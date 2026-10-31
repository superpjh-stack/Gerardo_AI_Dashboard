from __future__ import annotations
import os
import secrets
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from typing import Literal
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from .adapters import timestamp, uid
from .service import demo_events, overview
from .store import Store, NAMES
from .security import PrivateAccess
from .transfer import Receiver, Batch, Finish

ROOT = Path(__file__).resolve().parents[2]


class Note(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class SourceInput(BaseModel):
    provider: Literal['claude', 'codex', 'antigravity']


def create_app(store=None):
    deployment = os.environ.get('MONITOR_DEPLOYMENT', 'local')
    if deployment not in ('local', 'demo', 'private'):
        raise RuntimeError('Unsupported deployment mode')
    hosted_demo = deployment == 'demo'
    private = deployment == 'private'
    store = store or Store(ROOT / '.local/monitor.sqlite3', {
        'claude': Path.home()/'.claude/projects',
        'codex': Path.home()/'.codex/sessions',
        'antigravity': Path.home()/'.gemini/antigravity',
    }, max_files=int(os.environ.get('MONITOR_MAX_FILES', '100')))
    app = FastAPI(title='제라도의 AI 활동 모니터링', version='0.1.0')
    app.state.store = store
    access = PrivateAccess(store, os.environ['MONITOR_AUTH_FILE']) if private else None
    receiver = Receiver(store, access.device) if access else None
    token = secrets.token_urlsafe(32)
    origins = ['http://127.0.0.1:5188', 'http://localhost:5188', 'http://127.0.0.1:8765', 'http://localhost:8765']
    public_url = os.environ.get('MONITOR_PUBLIC_URL', '').rstrip('/')
    if private and not public_url.startswith('https://'):
        raise RuntimeError('Private deployment requires HTTPS')
    if private:
        origins = []
    hosts = ['127.0.0.1', 'localhost', 'testserver']
    if public_url:
        parsed = urlsplit(public_url)
        if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.path or parsed.username:
            raise RuntimeError('MONITOR_PUBLIC_URL must be an origin')
        origins.append(public_url)
        hosts.append(parsed.hostname)
    if access:
        access.register(app, public_url)

    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['GET', 'POST'], allow_headers=['Content-Type', 'X-Local-Token'])
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)

    @app.middleware('http')
    async def local_guard(request: Request, call_next):
        path = request.url.path
        mutation = request.method not in ('GET','HEAD','OPTIONS')
        ingest = private and path in ('/api/v1/transfer/batch','/api/v1/transfer/finish')
        def denied(code, message, status=403):
            return JSONResponse({'error': {'code': code, 'message': message, 'retryable': False}}, status_code=status,
                headers={'Cache-Control':'no-store'})
        if hosted_demo and mutation:
            return denied('demo_readonly','VPS 체험판은 읽기 전용입니다.')
        origin = request.headers.get('origin')
        navigation = (hosted_demo or private) and request.method == 'GET' and request.headers.get('sec-fetch-dest') == 'document'
        if (origin and origin not in origins) or (request.headers.get('sec-fetch-site') == 'cross-site' and not navigation):
            return denied('origin_denied','허용되지 않은 요청 출처입니다.')
        if private:
            if ingest:
                if not access.ingestion(request):
                    return denied('transfer_auth','전송 인증이 필요합니다.',401)
            elif path not in ('/api/v1/health','/login','/auth/login') and not access.authenticated(request):
                if not path.startswith('/api/') and request.method == 'GET':
                    return RedirectResponse('/login',303,headers={'Cache-Control':'no-store'})
                return denied('login_required','작업실 로그인이 필요합니다.',401)
        if mutation:
            auth_form = private and path in ('/auth/login','/auth/logout')
            if not ingest and not auth_form and not secrets.compare_digest(request.headers.get('x-local-token',''),token):
                return denied('token_required','화면을 새로고침한 뒤 다시 시도하세요.')
            # Bound both declared and chunked bodies before JSON/form parsing.
            limit = 2 * 1024 * 1024 if ingest else 16384
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body)>limit:
                    return denied('too_large','요청 크기가 제한을 초과했습니다.',413)
            request._body = bytes(body)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Frame-Options'] = 'DENY'
        if private:
            response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'"
        return response

    if receiver:
        @app.post('/api/v1/transfer/batch')
        def receive_batch(body: Batch):
            try:
                return receiver.batch(body)
            except PermissionError:
                raise HTTPException(403,'등록된 기기가 아닙니다.')
            except ValueError:
                raise HTTPException(409,'전송 배치 상태를 확인하세요.')

        @app.post('/api/v1/transfer/finish')
        def receive_finish(body: Finish):
            try:
                return receiver.finish(body)
            except PermissionError:
                raise HTTPException(403,'등록된 기기가 아닙니다.')
            except ValueError:
                raise HTTPException(409,'전체 전송 개수와 해시가 일치하지 않습니다.')

    @app.exception_handler(HTTPException)
    async def api_error(request, exc):
        return JSONResponse({'error': {'code': str(exc.status_code), 'message': exc.detail, 'retryable': exc.status_code >= 500}}, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse({'error': {'code': 'invalid_input', 'message': '입력 형식이나 조회 조건을 확인하세요.', 'retryable': False}}, status_code=422)

    @app.get('/api/v1/health')
    def health():
        return {'status': 'ok', 'version': '0.2.0', 'local_only': deployment == 'local', 'deployment': deployment}

    @app.get('/api/v1/session')
    def session():
        return {'token': token}

    @app.get('/api/v1/sources')
    def sources():
        if hosted_demo:
            return [dict(s, available=False, status='demo', location='연결되지 않음', capabilities=[],
                         files=0, total_files=0, last_success_at=None, last_attempt_at=None, warnings=0,
                         error='VPS 체험판에는 노트북 기록이 연결되어 있지 않습니다.') for s in store.sources()]
        return receiver.sources() if receiver else store.sources()

    @app.post('/api/v1/sources')
    def connect(body: SourceInput):
        return sync(body.provider)

    @app.post('/api/v1/sources/{provider}/sync')
    def sync(provider: str):
        if private:
            raise HTTPException(409, '노트북에서 전송 명령을 실행한 뒤 화면을 새로고침하세요.')
        if provider not in NAMES:
            raise HTTPException(404, '소스를 찾을 수 없습니다.')
        try:
            return store.sync(provider)
        except BlockingIOError:
            raise HTTPException(409, '이미 동기화 중입니다. 잠시 후 다시 시도하세요.')

    def get_overview(period, project, provider, demo, from_, to):
        if provider != 'all' and provider not in NAMES:
            raise HTTPException(422, '도구 필터를 확인하세요.')
        if bool(from_) != bool(to):
            raise HTTPException(422, '시작일과 종료일을 함께 지정하세요.')
        start, end = timestamp(from_), timestamp(to)
        if from_ and (not start or not end or start >= end):
            raise HTTPException(422, '유효한 시간대와 조회 기간을 지정하세요.')
        demo = hosted_demo or demo
        events = demo_events() if demo else store.events()
        sources = receiver.sources() if receiver else store.sources()
        if demo:
            sources = [dict(s, status='demo', available=True, error=None) for s in sources]
        try:
            return overview(events, sources, {} if demo else store.confirmations(), period, project, provider, start, end)
        except ValueError:
            raise HTTPException(422, '조회 기간을 확인하세요.')

    @app.get('/api/v1/overview')
    def dashboard(period: Literal['today','week','month','all']='today', project: str='all', provider: str='all', demo: bool=False,
                  from_: str | None=Query(None, alias='from'), to: str | None=None):
        return get_overview(period, project, provider, demo, from_, to)

    @app.get('/api/v1/usage')
    def usage(period: Literal['today','week','month','all']='today', project: str='all', provider: str='all', demo: bool=False):
        data = get_overview(period, project, provider, demo, None, None)
        return {k: data[k] for k in ('usage','series','providers','coverage','period')}

    @app.get('/api/v1/projects')
    def projects(demo: bool=False):
        demo = hosted_demo or demo
        events = demo_events() if demo else store.events()
        return sorted({e['project_id']: {'id': e['project_id'], 'name': e['project']} for e in events}.values(), key=lambda p:p['name'])

    @app.get('/api/v1/events')
    def events(period: Literal['today','week','month','all']='today', project: str='all', provider: str='all', demo: bool=False,
               cursor: int=Query(0,ge=0), limit: int=Query(50,ge=1,le=200)):
        demo = hosted_demo or demo
        data = get_overview(period, project, provider, demo, None, None)
        start, end = data['period']['from'], data['period']['to']
        all_events = demo_events() if demo else store.events()
        selected = sorted([e for e in all_events if start <= e['occurred_at'] < end and
                    (project=='all' or e['project_id']==project) and (provider=='all' or e['provider']==provider)],
                    key=lambda e:(e['occurred_at'],e['event_id']), reverse=True)
        return {'items': selected[cursor:cursor+limit], 'next_cursor': cursor+limit if cursor+limit<len(selected) else None}

    @app.get('/api/v1/tasks/{task_id}')
    def detail(task_id: str, demo: bool=False):
        demo = hosted_demo or demo
        if demo:
            group = [e for e in demo_events() if uid(e['provider'],e['session_id']) == task_id]
            if not group:
                raise HTTPException(404, '예시 세션을 찾을 수 없습니다.')
            return {'events': group, 'notes': [], 'confirmed_at': None,
                    'evidence': [{'ref': '합성 예시 데이터', 'type': 'usage', 'time': e['occurred_at']} for e in group]}
        data = store.detail(task_id)
        if not data:
            raise HTTPException(404, '세션을 찾을 수 없습니다.')
        return data

    @app.post('/api/v1/tasks/{task_id}/notes')
    def note(task_id: str, body: Note):
        if not store.detail(task_id):
            raise HTTPException(404, '세션을 찾을 수 없습니다.')
        if not body.text.strip():
            raise HTTPException(422, '메모를 입력하세요.')
        store.note(task_id, body.text.strip())
        return {'saved': True}

    @app.post('/api/v1/tasks/{task_id}/confirmations')
    def confirm(task_id: str):
        if not store.detail(task_id):
            raise HTTPException(404, '세션을 찾을 수 없습니다.')
        store.confirm(task_id)
        return {'status': 'user_confirmed'}

    dist = ROOT / 'frontend/dist'
    if dist.is_dir():
        app.mount('/assets', StaticFiles(directory=dist / 'assets'), name='assets')

        @app.get('/{path:path}', include_in_schema=False)
        def frontend(path: str):
            if path not in ('', 'activity', 'projects', 'usage', 'sources'):
                raise HTTPException(404, '페이지를 찾을 수 없습니다.')
            return FileResponse(dist / 'index.html')

    return app


app = create_app()
