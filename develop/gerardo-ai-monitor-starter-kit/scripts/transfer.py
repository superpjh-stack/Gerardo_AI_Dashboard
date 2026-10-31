#!/usr/bin/env python3
"""Explicit one-shot transfer; never installs a timer or uploads original files."""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
import uuid
import urllib.request
import urllib.error
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from monitor.store import Store
from monitor.transfer import export_event, export_source, snapshot_digest
from monitor.service import totals


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',type=Path,default=ROOT/'.local/private/client.json')
    parser.add_argument('--no-scan',action='store_true',help='Send the current normalized database without rescanning')
    args=parser.parse_args()
    if args.config.stat().st_mode & 0o077:raise RuntimeError('Client configuration must be private (chmod 600)')
    config=json.loads(args.config.read_text())
    base=config['url'].rstrip('/')
    if not base.startswith('https://'):raise RuntimeError('HTTPS required')
    store=Store(ROOT/'.local/monitor.sqlite3',{
        'claude':Path.home()/'.claude/projects',
        'codex':Path.home()/'.codex/sessions',
        'antigravity':Path.home()/'.gemini/antigravity'},max_files=100)
    if not args.no_scan:
        for provider in ('claude','codex','antigravity'):
            state=store.sync(provider)
            print(f'{provider}: {state["status"]}, files={state["files"]}')
    events=[export_event(e) for e in store.events()]
    if not events:raise RuntimeError('No events: refusing to replace the remote snapshot')
    sources=[export_source(s) for s in store.sources()]
    upload=uuid.uuid4().hex
    common={'device_id':config['device_id'],'upload_id':upload}
    # Refuse redirects: never forward the ingestion bearer to another destination.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):return None
    opener=urllib.request.build_opener(NoRedirect)
    def post(path,payload):
        body=json.dumps(payload,ensure_ascii=False).encode()
        for attempt in range(3):
            request=urllib.request.Request(base+path,data=body,headers={
                'Authorization':'Bearer '+config['ingest_token'],'Content-Type':'application/json'})
            try:
                with opener.open(request,timeout=45) as response:return json.load(response)
            except urllib.error.HTTPError as error:
                if error.code<500:raise RuntimeError(f'Transfer rejected (HTTP {error.code}); no secrets logged') from None
                if attempt==2:raise RuntimeError(f'Server error HTTP {error.code}') from None
            except urllib.error.URLError:
                if attempt==2:raise RuntimeError('Secure connection failed; live snapshot was not finalized') from None
            time.sleep(attempt+1)
    for start in range(0,len(events),250):
        result=post('/api/v1/transfer/batch',dict(common,events=events[start:start+250]))
        if start%2500==0:print(f'Staged {result["staged"]}/{len(events)}')
    expected=snapshot_digest(events)
    result=post('/api/v1/transfer/finish',dict(common,count=len(events),digest=expected,sources=sources))
    if result['count']!=len(events) or result['digest']!=expected:raise RuntimeError('Receipt mismatch')
    report={'url':base,'count':len(events),'digest':expected,'providers':dict(Counter(e['provider'] for e in events)),
            'usage':totals(events),'upload_id':upload,'completed_at':time.time()}
    output=ROOT/'.local/private/last-transfer.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    output.chmod(0o600)
    print(json.dumps({'verified_events':len(events),'providers':report['providers'],'usage':report['usage']},ensure_ascii=False))


if __name__=='__main__':main()
