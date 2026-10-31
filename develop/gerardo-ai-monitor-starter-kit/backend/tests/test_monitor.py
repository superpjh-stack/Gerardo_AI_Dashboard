import json
from datetime import datetime
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from monitor.adapters import parse_file, uid
from monitor.app import create_app
from monitor.service import totals, overview, period_bounds
from monitor.store import Store


def write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(r)+'\n' for r in rows))


def codex_rows(values=(100,150,150)):
    rows=[{'type':'session_meta','timestamp':'2026-10-31T00:00:00Z','payload':{'id':'s1','cwd':'/project/alpha'}},
          {'type':'turn_context','timestamp':'2026-10-31T00:00:01Z','payload':{'model':'test-model','cwd':'/project/alpha/backend'}}]
    for i,total in enumerate(values):
        rows.append({'type':'event_msg','timestamp':f'2026-10-31T00:0{i+1}:00Z','payload':{'type':'token_count','info':{'total_token_usage':{
            'input_tokens':total-20,'output_tokens':20,'cached_input_tokens':40,'cache_write_input_tokens':0,'total_tokens':total}}}})
    return rows


def claude_row(output=20):
    return {'type':'assistant','timestamp':'2026-10-31T00:00:00Z','sessionId':'cs1','cwd':'/project/alpha',
        'requestId':'r1','message':{'id':'msg1','model':'fixture-model','usage':{'input_tokens':10,'output_tokens':output,
            'cache_read_input_tokens':40,'cache_creation_input_tokens':30},'content':[{'type':'text','text':'PRIVATE CONTENT'},
            {'type':'tool_use','id':'tool1','name':'Edit','input':{'file':'PRIVATE PATH','content':'PRIVATE CODE'}}]}}


def test_codex_cumulative_and_cache(tmp_path):
    p=tmp_path/'s.jsonl';write(p,codex_rows())
    events,warnings=parse_file(p,'codex',tmp_path)
    usages=[e for e in events if e['event_type']=='usage']
    assert [e['usage']['total_tokens'] for e in usages]==[100,50]
    assert totals(events)['total_tokens']==150
    assert totals(events)['cache_read_tokens']==40
    assert warnings==0
    assert all(e['project']=='alpha' for e in events)


def test_late_arrival_sorted_before_deltas(tmp_path):
    p=tmp_path/'s.jsonl';rows=codex_rows((100,150));write(p,[*rows[:2],rows[3],rows[2]])
    events,warnings=parse_file(p,'codex',tmp_path)
    assert totals(events)['total_tokens']==150
    assert warnings==0


def test_unknown_counter_reset_quarantined(tmp_path):
    p=tmp_path/'s.jsonl';write(p,codex_rows((100,50,150)))
    events,warnings=parse_file(p,'codex',tmp_path)
    assert totals(events)['total_tokens']==150
    assert warnings==1


def test_claude_streaming_duplicate_and_cache(tmp_path):
    p=tmp_path/'s.jsonl';write(p,[claude_row(),claude_row(30),claude_row(25)])
    events,warnings=parse_file(p,'claude',tmp_path)
    assert totals(events)['total_tokens']==110
    assert len([e for e in events if e['event_type']=='usage'])==1
    assert len([e for e in events if e['event_type']=='activity'])==1
    assert 'PRIVATE' not in json.dumps(events)


def test_null_not_zero(tmp_path):
    row=claude_row();del row['message']['usage']['input_tokens']
    p=tmp_path/'s.jsonl';write(p,[row]);events,_=parse_file(p,'claude',tmp_path)
    assert totals(events)['total_tokens'] is None
    assert totals(events)['missing_count']==1
    assert totals([])['total_tokens'] is None


def test_partial_tail_retried(tmp_path):
    p=tmp_path/'s.jsonl';write(p,codex_rows((100,)))
    with p.open('a') as f:f.write('{"type":')
    events,warnings=parse_file(p,'codex',tmp_path)
    assert totals(events)['total_tokens']==100 and warnings==1


def test_korean_midnight():
    start,end=period_bounds('today',datetime.fromisoformat('2026-10-31T12:00:00+09:00'))
    assert start=='2026-10-30T15:00:00+00:00'
    assert end=='2026-10-31T15:00:00+00:00'


@pytest.fixture
def store(tmp_path):
    roots={p:tmp_path/p for p in ['claude','codex','antigravity']}
    for root in roots.values():root.mkdir()
    write(roots['codex']/'session.jsonl',codex_rows())
    return Store(tmp_path/'db.sqlite3',roots)


def test_idempotence_copy_and_rotation(store):
    store.sync('codex');original=store.events()
    store.sync('codex');assert store.events()==original
    p=store.roots['codex']/'session.jsonl'
    (p.parent/'copy.jsonl').write_bytes(p.read_bytes())
    store.sync('codex');assert len(store.events())==len(original)
    write(p,codex_rows((100,150,200)))
    store.sync('codex');assert totals(store.events())['total_tokens']==200


def test_symlink_outside_ignored(store,tmp_path):
    outside=tmp_path/'secret.jsonl';write(outside,codex_rows((999,)))
    (store.roots['codex']/'link.jsonl').symlink_to(outside)
    store.sync('codex');assert totals(store.events())['total_tokens']==150


def test_failure_preserves_good_data(store,monkeypatch):
    store.sync('codex');before=store.events()
    write(store.roots['codex']/'session.jsonl',codex_rows((100,150,200)))
    def fail(*args):raise OSError('temporary')
    monkeypatch.setattr('monitor.store.parse_file',fail)
    store.sync('codex');assert store.events()==before
    assert next(s for s in store.sources() if s['id']=='codex')['warnings']==1


def test_api_guard_notes_demo_and_filters(store):
    store.sync('codex');client=TestClient(create_app(store))
    assert client.get('/api/v1/health').status_code==200
    assert client.post('/api/v1/sources/codex/sync').status_code==403
    assert client.get('/api/v1/session',headers={'Origin':'https://evil.example'}).status_code==403
    assert client.get('/api/v1/health',headers={'Host':'evil.example'}).status_code==400
    token=client.get('/api/v1/session').json()['token'];headers={'X-Local-Token':token}
    assert client.get('/api/v1/overview?period=no').status_code==422
    assert client.get('/api/v1/overview?from=bad&to=bad').status_code==422
    assert client.get('/api/v1/events?limit=201').status_code==422
    data=client.get('/api/v1/overview?period=all').json()
    assert data['usage']['total_tokens']==150
    assert data['providers'][2]['usage']['total_tokens'] is None
    assert client.get('/api/v1/overview?period=all&provider=claude').json()['usage']['total_tokens'] is None
    task=data['tasks'][0]['id']
    assert client.post(f'/api/v1/tasks/{task}/notes',json={'text':'다음 작업 확인'},headers=headers).status_code==200
    assert client.post(f'/api/v1/tasks/{task}/confirmations',headers=headers).status_code==200
    detail=client.get(f'/api/v1/tasks/{task}').json()
    assert detail['notes'][0]['text']=='다음 작업 확인'
    assert detail['confirmed_at'] and all(e['available'] for e in detail['evidence'])
    assert all(e['event_type']!='verification' for e in detail['events'])
    before=len(store.events())
    assert client.get('/api/v1/overview?demo=true').json()['tasks'][0]['synthetic']
    assert len(store.events())==before
    assert client.get('/api/v1/overview?period=all').json()['usage']['total_tokens']==150
    (store.roots['codex']/'session.jsonl').unlink()
    assert all(not e['available'] for e in client.get(f'/api/v1/tasks/{task}').json()['evidence'])


def test_sync_conflict(store):
    store.lock.acquire()
    try:
        with pytest.raises(BlockingIOError):store.sync('codex')
    finally:store.lock.release()


def test_truncated_original_preserves_rotated_copy(store):
    p=store.roots['codex']/'session.jsonl'
    store.sync('codex')
    (p.parent/'rotated.jsonl').write_bytes(p.read_bytes())
    store.sync('codex')
    write(p,codex_rows((100,)))
    store.sync('codex')
    assert totals(store.events())['total_tokens']==150


def test_database_failure_rolls_back_checkpoint_and_events(store):
    store.sync('codex');before=store.events()
    with store.db() as c:
        signature=c.execute('SELECT signature FROM files').fetchone()[0]
        c.execute("CREATE TRIGGER fail_insert BEFORE INSERT ON event_instances BEGIN SELECT RAISE(ABORT, 'test failure'); END")
    write(store.roots['codex']/'session.jsonl',codex_rows((100,150,200)))
    store.sync('codex')
    assert store.events()==before
    with store.db() as c:
        assert c.execute('SELECT signature FROM files').fetchone()[0]==signature


def test_local_synthetic_response_not_counted(tmp_path):
    p=tmp_path/'s.jsonl';row=claude_row();row['message']['model']='<synthetic>'
    write(p,[row]);events,_=parse_file(p,'claude',tmp_path)
    assert events==[]


def test_hosted_demo_never_exposes_real_events(store,monkeypatch):
    store.sync('codex')
    monkeypatch.setenv('MONITOR_DEPLOYMENT','demo')
    monkeypatch.setenv('MONITOR_PUBLIC_URL','http://dashboard.example:8788')
    client=TestClient(create_app(store),base_url='http://dashboard.example:8788')
    assert client.get('/api/v1/health').json()['deployment']=='demo'
    for demo in ['true','false']:
        result=client.get('/api/v1/overview?period=all&demo='+demo).json()
        assert result['tasks'] and all(t['synthetic'] for t in result['tasks'])
        events=client.get('/api/v1/events?demo='+demo).json()['items']
        assert all(e['synthetic'] for e in events)
    assert all(not s['available'] for s in client.get('/api/v1/sources').json())
    assert client.get('/api/v1/tasks/'+uid('codex','s1')).status_code==404
    token=client.get('/api/v1/session').json()['token']
    assert client.post('/api/v1/sources/codex/sync',headers={'X-Local-Token':token}).status_code==403
    assert client.get('/api/v1/health',headers={'Host':'untrusted.example'}).status_code==400
    assert client.get('/api/v1/overview',headers={'Origin':'http://dashboard.example:8788'}).status_code==200
    assert client.get('/api/v1/overview',headers={'Origin':'http://evil.example'}).status_code==403
