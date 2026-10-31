#!/usr/bin/env python3
"""Generate separate login/ingest credentials in ignored, owner-only local files."""
import json
import os
import secrets
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from monitor.security import password_hash,digest

os.umask(0o077)
directory=ROOT/'.local/private'
directory.mkdir(parents=True,exist_ok=True)
directory.chmod(0o700)
if any((directory/name).exists() for name in ('auth.json','client.json','login.json')):
    raise SystemExit('Existing credentials preserved; rotate explicitly instead.')
url='https://gerardo.187-52-127-215.sslip.io:18790'
password=secrets.token_urlsafe(24);ingest=secrets.token_urlsafe(32);salt=secrets.token_hex(16);device=secrets.token_hex(16)
for name,data in {
    'auth.json':dict(salt=salt,password_hash=password_hash(password,salt),ingest_hash=digest(ingest),device_id=device),
    'client.json':dict(url=url,device_id=device,ingest_token=ingest),
    'login.json':dict(url=url,password=password),
}.items():
    (directory/name).write_text(json.dumps(data,indent=2))
(directory/'접속정보.txt').write_text(f'제라도의 비공개 AI 작업실\n주소: {url}\n비밀번호: {password}\n\n이 파일과 client.json은 외부에 공유하지 마세요.\n다음 전송: 프로젝트의 실제기록전송.command 실행\n')
print('Private configuration created. Credentials were not printed.')
