import json
import secrets
import time
import pytest
from fastapi.testclient import TestClient
from monitor.app import create_app
from monitor.security import password_hash, digest, COOKIE
from monitor.transfer import export_event, export_source, snapshot_digest
from monitor.store import Store
from monitor.service import totals
from test_monitor import codex_rows, write

URL='https://private.example:18790'

@pytest.fixture
def private(tmp_path,monkeypatch):
    password=secrets.token_urlsafe(32);token=secrets.token_urlsafe(32);salt=secrets.token_hex(16);device=secrets.token_hex(16)
    cfg=tmp_path/'auth.json'
    cfg.write_text(json.dumps(dict(salt=salt,password_hash=password_hash(password,salt),ingest_hash=digest(token),device_id=device)))
    monkeypatch.setenv('MONITOR_DEPLOYMENT','private');monkeypatch.setenv('MONITOR_PUBLIC_URL',URL);monkeypatch.setenv('MONITOR_AUTH_FILE',str(cfg))
    store=Store(tmp_path/'remote.db',{})
    client=TestClient(create_app(store),base_url=URL)
    return client,store,password,{'Authorization':'Bearer '+token},device

def login(private):
    client,store,password,headers,device=private
    return client.post('/auth/login',data={'password':password},headers={'Origin':URL},follow_redirects=False)

def snapshot(tmp_path,device):
    roots={'codex':tmp_path/'logs'}
    write(roots['codex']/'private-path.jsonl',codex_rows())
    source=Store(tmp_path/'local.db',roots);source.sync('codex')
    events=[export_event(e) for e in source.events()]
    common={'device_id':device,'upload_id':secrets.token_hex(16)}
    return dict(common,events=events),dict(common,count=len(events),digest=snapshot_digest(events),sources=[export_source(s) for s in source.sources()])

def test_all_private_routes_require_login(private):
    client,*_=private
    assert client.get('/api/v1/health').status_code==200
    for path in ('/api/v1/overview','/api/v1/projects','/api/v1/events','/api/v1/session','/api/v1/tasks/abc','/api/v1/sources','/api/v1/usage'):
        assert client.get(path).status_code==401
    for path in ('/','/activity','/assets/test.js','/docs','/openapi.json'):
        assert client.get(path,follow_redirects=False).status_code==303
    assert client.get('/login').status_code==200
    response=login(private)
    cookie=response.headers['set-cookie']
    assert 'Secure' in cookie and 'HttpOnly' in cookie and 'SameSite=strict' in cookie
    assert client.get('/api/v1/overview').status_code==200

def test_credentials_separated_and_csrf(private,tmp_path):
    client,store,password,headers,device=private
    batch,finish=snapshot(tmp_path,device)
    assert client.post('/api/v1/transfer/batch',json=batch).status_code==401
    assert client.get('/api/v1/events',headers=headers).status_code==401
    assert client.post('/auth/login',data={'password':password}).status_code==403
    assert client.post('/auth/login',data={'password':password},headers={'Origin':'https://evil.example'}).status_code==403
    login(private)
    assert client.post('/api/v1/transfer/batch',json=batch).status_code==401
    localtoken=client.get('/api/v1/session').json()['token']
    assert client.post('/api/v1/sources/codex/sync',headers={'X-Local-Token':localtoken}).status_code==409
    assert client.post('/auth/logout').status_code==403
    assert client.post('/auth/logout',headers={'Origin':URL},follow_redirects=False).status_code==303
    assert client.get('/api/v1/events').status_code==401

def test_session_expiry_and_restart(private):
    client,store,*_=private
    login(private)
    value=client.cookies.get(COOKIE)
    recreated=TestClient(create_app(store),base_url=URL);recreated.cookies.set(COOKIE,value)
    assert recreated.get('/api/v1/events').status_code==200
    with store.db() as c:c.execute('UPDATE auth_sessions SET expires=?',(time.time()-1,))
    assert client.get('/api/v1/events').status_code==401

def test_login_rate_limit_persists(private):
    client,store,*_=private
    for _ in range(10):assert client.post('/auth/login',data={'password':'wrong'},headers={'Origin':URL}).status_code==401
    recreated=TestClient(create_app(store),base_url=URL)
    assert recreated.post('/auth/login',data={'password':'wrong'},headers={'Origin':URL}).status_code==429

def test_snapshot_atomicity_retries_and_null(private,tmp_path):
    client,store,password,headers,device=private
    batch,finish=snapshot(tmp_path,device)
    assert 'private-path' not in json.dumps(batch) and '/project/' not in json.dumps(batch)
    assert client.post('/api/v1/transfer/batch',json=batch,headers=headers).status_code==200
    assert store.events()==[]
    assert client.post('/api/v1/transfer/batch',json=batch,headers=headers).json()['staged']==finish['count']
    assert client.post('/api/v1/transfer/finish',json=dict(finish,count=999),headers=headers).status_code==409
    assert store.events()==[]
    assert client.post('/api/v1/transfer/finish',json=finish,headers=headers).status_code==200
    assert len(store.events())==finish['count'] and totals(store.events())['total_tokens']==150
    assert client.post('/api/v1/transfer/finish',json=finish,headers=headers).json()['replayed']
    before=store.events()
    batch['upload_id']=finish['upload_id']=secrets.token_hex(16)
    batch['events']=batch['events'][:1]
    client.post('/api/v1/transfer/batch',json=batch,headers=headers)
    assert client.post('/api/v1/transfer/finish',json=finish,headers=headers).status_code==409
    assert store.events()==before
    login(private)
    sources=client.get('/api/v1/sources').json()
    assert next(s for s in sources if s['id']=='codex')['last_received_at']
    assert client.get('/api/v1/overview?period=all').json()['usage']['total_tokens']==150

def test_payload_validation_and_limits(private,tmp_path):
    client,store,password,headers,device=private
    batch,finish=snapshot(tmp_path,device)
    batch['events'][0]['prompt']='must never store'
    assert client.post('/api/v1/transfer/batch',json=batch,headers=headers).status_code==422
    del batch['events'][0]['prompt'];batch['events'][0]['source_ref']='/Users/private/raw.jsonl'
    assert client.post('/api/v1/transfer/batch',json=batch,headers=headers).status_code==422
    assert client.post('/api/v1/transfer/batch',content=b'x'*(2*1024*1024+1),headers=headers).status_code==413
    assert store.events()==[]

def test_null_values_preserved(private,tmp_path):
    client,store,password,headers,device=private
    batch,finish=snapshot(tmp_path,device)
    for event in batch['events']:
        if 'usage' in event:event['usage']['cache_write_tokens']=None
    finish['digest']=snapshot_digest(batch['events'])
    assert client.post('/api/v1/transfer/batch',json=batch,headers=headers).status_code==200
    assert client.post('/api/v1/transfer/finish',json=finish,headers=headers).status_code==200
    assert totals(store.events())['cache_write_tokens'] is None

def test_private_fails_closed(tmp_path,monkeypatch):
    monkeypatch.setenv('MONITOR_DEPLOYMENT','private');monkeypatch.delenv('MONITOR_AUTH_FILE',raising=False)
    with pytest.raises(KeyError):create_app(Store(tmp_path/'db',{}))
