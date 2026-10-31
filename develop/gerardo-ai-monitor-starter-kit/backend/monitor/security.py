"""Single-owner authentication; secrets stay outside the image and repository."""
from __future__ import annotations
import hashlib
import html
import json
import secrets
import time
from pathlib import Path
from urllib.parse import parse_qs
from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

COOKIE = '__Host-monitor'
TTL = 7 * 24 * 3600


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(password: str, salt: str) -> str:
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()


class PrivateAccess:
    def __init__(self, store, config_path: str):
        cfg = json.loads(Path(config_path).read_text())
        self.username = cfg.get('username', 'admin')
        if not isinstance(self.username, str) or not self.username or len(self.username) > 100:
            raise RuntimeError('Invalid private username')
        self.salt, self.password = cfg['salt'], cfg['password_hash']
        self.ingest_hash, self.device = cfg['ingest_hash'], cfg['device_id']
        for value, length in ((self.salt,32),(self.password,128),(self.ingest_hash,64),(self.device,32)):
            if len(value) != length or any(c not in '0123456789abcdef' for c in value):
                raise RuntimeError('Invalid private authentication configuration')
        self.store = store
        with store.db() as c:
            c.execute('CREATE TABLE IF NOT EXISTS auth_sessions(id TEXT PRIMARY KEY, expires REAL NOT NULL)')
            c.execute('CREATE TABLE IF NOT EXISTS login_attempts(id TEXT PRIMARY KEY, started REAL, attempts INTEGER)')
            c.execute('CREATE TABLE IF NOT EXISTS auth_config(id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL)')
            fingerprint = digest(self.username + ':' + self.salt + ':' + self.password)
            previous = c.execute("SELECT fingerprint FROM auth_config WHERE id='owner'").fetchone()
            if not previous or previous[0] != fingerprint:
                c.execute('DELETE FROM auth_sessions')
                c.execute('DELETE FROM login_attempts')
                c.execute("INSERT OR REPLACE INTO auth_config VALUES ('owner',?)", (fingerprint,))

    def authenticated(self, request):
        value = request.cookies.get(COOKIE, '')
        if not value or len(value) > 128:
            return False
        with self.store.db() as c:
            row = c.execute('SELECT expires FROM auth_sessions WHERE id=?', (digest(value),)).fetchone()
        return bool(row and row[0] > time.time())

    def ingestion(self, request):
        auth = request.headers.get('authorization','')
        return auth.startswith('Bearer ') and secrets.compare_digest(digest(auth[7:]), self.ingest_hash)

    def register(self, app, public_url):
        def page(error='', status=200):
            return HTMLResponse('''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>제라도의 AI 작업실 · 로그인</title>
<style>*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}body{padding:24px max(16px,env(safe-area-inset-right)) 24px max(16px,env(safe-area-inset-left));margin:0;background:#101615;color:#eff5f1;font:16px system-ui;display:grid;min-height:100svh;place-items:center}main{width:min(440px,100%);padding:clamp(24px,6vw,36px);border:1px solid #34433c;border-radius:20px;background:#19221e}small{color:#79d9bc}h1{font-size:26px}p{color:#bbc9c0;line-height:1.7}label{display:block;margin-top:24px}input,button{box-sizing:border-box;width:100%;padding:14px;margin-top:10px;border-radius:9px;border:1px solid #526258;font:inherit}input{background:#101615;color:white}button{background:#79d9bc;color:#10251c;cursor:pointer;font-weight:700}.error{color:#ffb2a7}input,button{min-height:48px;font-size:16px}@media(max-height:650px){body{align-items:start}}@media(max-width:380px){h1{font-size:23px}p{font-size:14px}}</style>
<main><small>GERARDO / PRIVATE WORKSPACE</small><h1>제라도의 AI 작업실</h1><p>노트북에서 전송한 실제 활동 기록입니다.<br>아이디와 비밀번호로 로그인해 주세요.</p>'''
                + (f'<p class="error" role="alert">{html.escape(error)}</p>' if error else '')
                + '''<form method="post" action="/auth/login"><label for="username">아이디</label><input id="username" name="username" type="text" autocomplete="username" required maxlength="100" autofocus><label for="password">비밀번호</label><input id="password" name="password" type="password" autocomplete="current-password" required maxlength="256"><button>작업실 열기</button></form><p><small>대화 원문과 코드는 저장하지 않습니다.</small></p></main></html>''', status_code=status)

        @app.get('/login', include_in_schema=False)
        def login_page(request: Request):
            return RedirectResponse('/',303) if self.authenticated(request) else page()

        @app.post('/auth/login', include_in_schema=False)
        async def login(request: Request):
            if request.headers.get('origin') != public_url:
                return page('허용되지 않은 요청입니다.',403)
            now = time.time()
            # Persistent global limit prevents restart/IP rotation bypass on this personal service.
            with self.store.db() as c:
                c.execute("DELETE FROM login_attempts WHERE started < ?", (now-900,))
                row = c.execute("SELECT attempts FROM login_attempts WHERE id='owner'").fetchone()
                if row and row[0] >= 10:
                    response = page('로그인 시도가 많습니다. 15분 뒤 다시 시도하세요.',429)
                    response.headers['Retry-After'] = '900'
                    return response
                c.execute("INSERT INTO login_attempts VALUES ('owner',?,1) ON CONFLICT(id) DO UPDATE SET attempts=attempts+1", (now,))
            body = parse_qs((await request.body()).decode('utf-8',errors='replace'))
            password = body.get('password',[''])[0]
            username = body.get('username',[''])[0]
            valid_password = len(password) <= 256 and secrets.compare_digest(password_hash(password,self.salt),self.password)
            valid_username = len(username) <= 100 and secrets.compare_digest(username.encode(),self.username.encode())
            if not (valid_password and valid_username):
                return page('아이디 또는 비밀번호를 확인해 주세요.',401)
            value = secrets.token_urlsafe(32)
            with self.store.db() as c:
                c.execute('DELETE FROM auth_sessions WHERE expires < ?', (now,))
                c.execute('INSERT INTO auth_sessions VALUES (?,?)', (digest(value), now+TTL))
                c.execute('DELETE FROM login_attempts')
            response = RedirectResponse('/',303)
            response.set_cookie(COOKIE,value,max_age=TTL,secure=True,httponly=True,samesite='strict',path='/')
            return response

        @app.post('/auth/logout', include_in_schema=False)
        def logout(request: Request):
            if request.headers.get('origin') != public_url:
                return JSONResponse({'error':{'message':'허용되지 않은 요청입니다.'}},403)
            with self.store.db() as c:
                c.execute('DELETE FROM auth_sessions WHERE id=?',(digest(request.cookies.get(COOKIE,'')),))
            response = RedirectResponse('/login',303)
            response.delete_cookie(COOKIE,path='/',secure=True,httponly=True,samesite='strict')
            return response
