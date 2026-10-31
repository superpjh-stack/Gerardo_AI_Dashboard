"""Read only known JSONL metadata; never persist prompts, code, or tool arguments."""
from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

VERSION = 'jsonl-3'
FIELDS = ('input_tokens', 'output_tokens', 'cache_read_tokens', 'cache_write_tokens', 'total_tokens')


def uid(*parts: object) -> str:
    return hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:32]


def timestamp(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            return None
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        return None


def number(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def parse_file(path: Path, provider: str, root: Path) -> tuple[list[dict], int]:
    """Full-file reconciliation supports changed streaming records and truncation.

    Checkpoints skip unchanged files. A non-newline-terminated final record is
    intentionally retried on the next scan. Stable IDs deduplicate copied logs.
    """
    records = []
    warnings = 0
    with path.open('rb') as stream:
        for lineno, raw in enumerate(stream, 1):
            if not raw.endswith(b'\n'):
                warnings += 1
                continue
            try:
                row = json.loads(raw)
                if isinstance(row, dict):
                    records.append((lineno, row))
            except (ValueError, UnicodeDecodeError):
                warnings += 1
    records.sort(key=lambda item: (timestamp(item[1].get('timestamp')) or '', item[0]))
    events: dict[str, dict] = {}
    session = path.stem
    project = '미분류'
    project_id = 'unclassified'
    model = None
    previous: dict | None = None
    observed = datetime.now(timezone.utc).isoformat()
    relative = str(path.relative_to(root))

    def context(cwd):
        nonlocal project, project_id
        if isinstance(cwd, str) and cwd and project_id == 'unclassified':
            project = Path(cwd).name or '미분류'
            project_id = uid(cwd)

    def emit(key, kind, time, label, **extra):
        if not time:
            return
        eid = uid(provider, session, key)
        events[eid] = dict(event_id=eid, provider=provider, source_id=provider,
            session_id=session, project=project, project_id=project_id, model=model,
            event_type=kind, occurred_at=time, observed_at=observed,
            title=label, source_ref=f'{relative}:{lineno}', parser_version=VERSION,
            synthetic=False, quality='measured', **extra)

    for lineno, row in records:
        time = timestamp(row.get('timestamp'))
        if provider == 'codex':
            payload = row.get('payload')
            if not isinstance(payload, dict):
                continue
            if row.get('type') == 'session_meta':
                session = payload.get('id') or payload.get('session_id') or session
                context(payload.get('cwd'))
                emit('start', 'session_started', time, '작업 세션 시작')
            elif row.get('type') == 'turn_context':
                context(payload.get('cwd'))
                model = payload.get('model') or model
            elif row.get('type') == 'event_msg' and payload.get('type') == 'token_count':
                info = payload.get('info') or {}
                usage = info.get('total_token_usage')
                if not isinstance(usage, dict):
                    continue
                current = dict(input_tokens=number(usage.get('input_tokens')),
                    output_tokens=number(usage.get('output_tokens')),
                    cache_read_tokens=number(usage.get('cached_input_tokens')),
                    cache_write_tokens=number(usage.get('cache_write_input_tokens')),
                    total_tokens=number(usage.get('total_tokens')))
                if current == previous:
                    continue
                if previous and any(current[k] is not None and previous[k] is not None
                                    and current[k] < previous[k] for k in FIELDS):
                    warnings += 1  # Ambiguous reset: preserve baseline, quarantine this sample.
                    continue
                delta = {k: (None if current[k] is None or (previous and previous[k] is None)
                             else current[k] - (previous[k] if previous else 0)) for k in FIELDS}
                if delta['total_tokens'] is None and delta['input_tokens'] is not None and delta['output_tokens'] is not None:
                    delta['total_tokens'] = delta['input_tokens'] + delta['output_tokens']
                first = previous is None
                previous = current
                emit('usage:' + json.dumps(current, sort_keys=True), 'usage', time, '모델 사용량 기록',
                     usage=delta, raw_usage=current, usage_mode='cumulative',
                     cache_semantics='included', attribution='first_observation' if first else 'observed_interval')
            elif row.get('type') == 'response_item' and payload.get('type') in ('function_call', 'custom_tool_call'):
                name = payload.get('name', 'tool')
                if not isinstance(name, str) or not re.fullmatch(r'[\w.:-]{1,120}', name):
                    name = 'tool'
                emit(payload.get('call_id') or f'call:{lineno}', 'activity', time, '도구 호출 · ' + name, tool=name)
        elif provider == 'claude':
            if row.get('sessionId'):
                session = str(row['sessionId']) + (':' + str(row['agentId']) if row.get('agentId') else '')
            context(row.get('cwd'))
            msg = row.get('message')
            if row.get('type') != 'assistant' or not isinstance(msg, dict):
                continue
            model = msg.get('model') or model
            if isinstance(model, str) and model.startswith('<'):
                continue  # Local synthetic/error responses are not model usage.
            message_id = msg.get('id')
            if not message_id:  # Cannot safely deduplicate usage without an identity.
                warnings += 1
                continue
            u = msg.get('usage')
            if isinstance(u, dict):
                usage = dict(input_tokens=number(u.get('input_tokens')), output_tokens=number(u.get('output_tokens')),
                    cache_read_tokens=number(u.get('cache_read_input_tokens')),
                    cache_write_tokens=number(u.get('cache_creation_input_tokens')))
                usage['total_tokens'] = sum(usage.values()) if all(v is not None for v in usage.values()) else None
                key = 'usage:' + str(message_id) + ':' + str(row.get('requestId', ''))
                eid = uid(provider, session, key)
                old = events.get(eid)
                # Streaming chunks repeat the same message usage; retain largest final output.
                if not old or (usage['output_tokens'] or 0) >= (old['usage']['output_tokens'] or 0):
                    emit(key, 'usage', time, '모델 응답 기록', usage=usage, raw_usage=usage,
                         usage_mode='delta', cache_semantics='excluded', attribution='message_timestamp')
            for block in msg.get('content', []) if isinstance(msg.get('content'), list) else []:
                if isinstance(block, dict) and block.get('type') == 'tool_use':
                    name = block.get('name', 'tool')
                    if not isinstance(name, str) or not re.fullmatch(r'[\w.:-]{1,120}', name):
                        name = 'tool'
                    emit(block.get('id') or f'{message_id}:{name}', 'activity', time, '도구 호출 · ' + name, tool=name)
    return list(events.values()), warnings
