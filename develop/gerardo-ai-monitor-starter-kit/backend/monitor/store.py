from __future__ import annotations
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from .adapters import parse_file, uid, VERSION

NAMES = {'claude': 'Claude', 'codex': 'Codex', 'antigravity': 'Antigravity'}


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: Path, roots: dict[str, Path], max_files=100):
        self.path, self.roots, self.max_files = path, roots, max_files
        path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        with self.db() as c:
            c.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY, state TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS files(provider TEXT, path TEXT, signature TEXT,
                PRIMARY KEY(provider,path));
            CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, provider TEXT,
                file TEXT, occurred_at TEXT, data TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS event_time ON events(occurred_at);
            CREATE TABLE IF NOT EXISTS event_instances(id TEXT, provider TEXT, file TEXT, occurred_at TEXT, data TEXT,
                PRIMARY KEY(id,file));
            INSERT OR IGNORE INTO event_instances SELECT id,provider,file,occurred_at,data FROM events;
            CREATE TABLE IF NOT EXISTS notes(id TEXT PRIMARY KEY, task TEXT, text TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS confirmations(task TEXT PRIMARY KEY, created_at TEXT);
            ''')
            for provider in NAMES:
                c.execute('INSERT OR IGNORE INTO sources VALUES (?,?)', (provider, json.dumps({
                    'id': provider, 'name': NAMES[provider], 'status': 'not_connected',
                    'last_success_at': None, 'last_attempt_at': None, 'error': None,
                    'files': 0, 'warnings': 0, 'scan_limit': max_files})))

    @contextmanager
    def db(self):
        c = sqlite3.connect(self.path, timeout=30)
        c.row_factory = sqlite3.Row
        try:
            with c:
                yield c
        finally:
            c.close()

    def sources(self):
        with self.db() as c:
            rows = [json.loads(r['state']) for r in c.execute('SELECT * FROM sources ORDER BY id')]
        for row in rows:
            root = self.roots.get(row['id'])
            row['available'] = bool(root and root.is_dir() and row['id'] != 'antigravity')
            row['capabilities'] = ['sessions', 'model', 'tokens', 'tools'] if row['available'] else []
            row['location'] = ('~/' + str(root.relative_to(Path.home()))) if root and root.is_relative_to(Path.home()) else '설정된 로컬 소스'
            if not row['available']:
                row['status'] = 'unavailable'
                row['error'] = '지원 가능한 로컬 기록 경로를 찾지 못했습니다.'
        return rows

    def sync(self, provider):
        if not self.lock.acquire(blocking=False):
            raise BlockingIOError('이미 동기화 중입니다.')
        try:
            return self._sync(provider)
        finally:
            self.lock.release()

    def _sync(self, provider):
        state = next(s for s in self.sources() if s['id'] == provider)
        state['last_attempt_at'] = now()
        root = self.roots.get(provider)
        if not state['available']:
            self.save_state(state)
            return state
        try:
            root = root.resolve()
            candidates = [p for p in root.rglob('*.jsonl')
                          if not p.is_symlink() and p.resolve().is_relative_to(root)]
            candidates.sort(key=lambda p: p.stat().st_mtime_ns, reverse=True)
            selected = candidates[:self.max_files]
            warnings = 0
            changed = 0
            # Each file is reconciled atomically. Existing good files survive unrelated failures.
            for path in selected:
                try:
                    stat = path.stat()
                    signature = f'{VERSION}:{stat.st_ino}:{stat.st_size}:{stat.st_mtime_ns}'
                    with self.db() as c:
                        old = c.execute('SELECT signature FROM files WHERE provider=? AND path=?',
                                        (provider, str(path))).fetchone()
                    if old and old['signature'] == signature:
                        continue
                    events, count = parse_file(path, provider, root)
                    warnings += count
                    with self.db() as c:
                        c.execute('DELETE FROM event_instances WHERE provider=? AND file=?', (provider, str(path)))
                        for event in events:
                            c.execute('INSERT OR REPLACE INTO event_instances VALUES (?,?,?,?,?)',
                                (event['event_id'], provider, str(path), event['occurred_at'], json.dumps(event, ensure_ascii=False)))
                        c.execute('INSERT OR REPLACE INTO files VALUES (?,?,?)', (provider, str(path), signature))
                        # Rebuild canonical IDs from all known file snapshots: copied or rotated
                        # logs keep their history even when the original file is truncated.
                        c.execute('DELETE FROM events WHERE provider=?', (provider,))
                        c.execute('''INSERT OR IGNORE INTO events SELECT id,provider,file,occurred_at,data
                            FROM event_instances WHERE provider=? ORDER BY occurred_at,file''', (provider,))
                    changed += 1
                except (OSError, ValueError, TypeError, KeyError, sqlite3.Error):
                    warnings += 1
            # Scan warning counts are cumulative, so an unchanged rescan cannot hide a prior gap.
            state.update(status='partial' if warnings or state.get('warnings') or len(candidates) > len(selected) else 'connected',
                error=None, last_success_at=now(), files=len(selected), total_files=len(candidates),
                warnings=state.get('warnings', 0) + warnings, changed_files=changed)
        except OSError:
            state.update(status='error', error='소스 파일에 접근할 수 없습니다. 경로와 권한을 확인하세요.')
        self.save_state(state)
        return state

    def save_state(self, state):
        with self.db() as c:
            c.execute('UPDATE sources SET state=? WHERE id=?', (json.dumps(state, ensure_ascii=False), state['id']))

    def events(self):
        with self.db() as c:
            return [json.loads(r[0]) for r in c.execute('SELECT data FROM events ORDER BY occurred_at,id')]

    def detail(self, task_id):
        events = [e for e in self.events() if uid(e['provider'], e['session_id']) == task_id]
        if not events:
            return None
        with self.db() as c:
            notes = [dict(r) for r in c.execute('SELECT * FROM notes WHERE task=? ORDER BY created_at', (task_id,))]
            confirmed = c.execute('SELECT created_at FROM confirmations WHERE task=?', (task_id,)).fetchone()
        refs = {e['source_ref']: e for e in events}
        return {'events': events[-100:], 'notes': notes, 'confirmed_at': confirmed[0] if confirmed else None,
            'evidence': [{'ref': ref, 'type': e['event_type'], 'time': e['occurred_at'], 'available': self.evidence_exists(e)} for ref, e in list(refs.items())[-40:]]}

    def evidence_exists(self, event):
        root = self.roots.get(event['provider'])
        if not root:
            return False
        relative = event['source_ref'].rsplit(':', 1)[0]
        candidate = (root / relative).resolve()
        return candidate.is_relative_to(root.resolve()) and candidate.is_file()

    def confirmations(self):
        with self.db() as c:
            return {r['task']: r['created_at'] for r in c.execute('SELECT * FROM confirmations')}

    def note(self, task, text):
        created = now()
        with self.db() as c:
            c.execute('INSERT INTO notes VALUES (?,?,?,?)', (uid(task, created), task, text, created))

    def confirm(self, task):
        with self.db() as c:
            c.execute('INSERT OR IGNORE INTO confirmations VALUES (?,?)', (task, now()))
