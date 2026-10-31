"""Run the two local development servers; terminate only children we started."""
import argparse
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--open',action='store_true')
args=parser.parse_args()
if not shutil.which('npm') or not (ROOT/'frontend/node_modules').is_dir():
    sys.exit('먼저 frontend 폴더에서 npm ci를 실행하세요.')
for port in (8765,5188):
    with socket.socket() as sock:
        if sock.connect_ex(('127.0.0.1',port))==0:
            sys.exit(f'{port} 포트가 사용 중입니다. 기존 대시보드를 확인하거나 해당 터미널에서 종료하세요.')
children=[]
def stop(signum=None,frame=None):
    for child in children:
        if child.poll() is None:
            os.killpg(child.pid,signal.SIGTERM)
    for child in children:
        try:child.wait(timeout=5)
        except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL)
signal.signal(signal.SIGINT,stop)
signal.signal(signal.SIGTERM,stop)
try:
    children.append(subprocess.Popen([sys.executable,'-m','uvicorn','monitor.app:app','--app-dir','backend','--host','127.0.0.1','--port','8765'],cwd=ROOT,start_new_session=True))
    children.append(subprocess.Popen(['npm','run','dev'],cwd=ROOT/'frontend',start_new_session=True))
    for _ in range(60):
        if any(p.poll() is not None for p in children):raise RuntimeError('서버 시작에 실패했습니다. 위 오류를 확인하세요.')
        try:
            urllib.request.urlopen('http://127.0.0.1:8765/api/v1/health',timeout=1).close()
            urllib.request.urlopen('http://127.0.0.1:5188/',timeout=1).close()
            break
        except OSError:time.sleep(.5)
    else:raise RuntimeError('서버 준비 시간을 초과했습니다.')
    print('\n제라도의 AI 활동 모니터링: http://127.0.0.1:5188/\n종료: Ctrl+C\n',flush=True)
    if args.open:webbrowser.open('http://127.0.0.1:5188/')
    while all(p.poll() is None for p in children):time.sleep(.5)
finally:
    stop()
