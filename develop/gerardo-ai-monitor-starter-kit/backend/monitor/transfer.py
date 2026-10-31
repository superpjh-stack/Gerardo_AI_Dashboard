"""Allowlisted metadata snapshots. Incomplete uploads never replace live data."""
from __future__ import annotations
import hashlib
import json
import re
import time
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .adapters import uid, timestamp
from .store import NAMES, now

HexID = Annotated[str, Field(pattern=r'^[a-f0-9]{32}$')]
Provider = Literal['claude','codex','antigravity']
Count = Annotated[int, Field(strict=True,ge=0,le=10**15)]


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Usage(Strict):
    input_tokens: Count | None
    output_tokens: Count | None
    cache_read_tokens: Count | None
    cache_write_tokens: Count | None
    total_tokens: Count | None


class Event(Strict):
    event_id: HexID
    provider: Provider
    source_id: Provider
    session_id: HexID
    project_id: HexID
    project: str = Field(min_length=1,max_length=120)
    model: str | None = Field(default=None,max_length=120,pattern=r'^[\w.:-]+$')
    event_type: Literal['session_started','activity','usage']
    occurred_at: str
    observed_at: str
    source_ref: str = Field(pattern=r'^metadata:[a-f0-9]{32}$')
    parser_version: str = Field(max_length=40,pattern=r'^[\w.-]+$')
    synthetic: Literal[False] = False
    quality: Literal['measured'] = 'measured'
    title: Literal['작업 세션 시작','도구 호출','모델 사용량 기록']
    tool: str | None = Field(default=None,max_length=120,pattern=r'^[\w.:-]+$')
    usage: Usage | None = None
    raw_usage: Usage | None = None
    usage_mode: Literal['delta','cumulative'] | None = None
    cache_semantics: Literal['included','excluded','unknown'] | None = None
    attribution: Literal['first_observation','observed_interval','message_timestamp'] | None = None

    @field_validator('occurred_at','observed_at')
    @classmethod
    def valid_time(cls,v):
        parsed=timestamp(v)
        if not parsed: raise ValueError('Timezone required')
        return parsed

    @field_validator('project')
    @classmethod
    def no_path(cls,v):
        if any(ord(c)<32 or c in '/\\' for c in v): raise ValueError('Not a project display name')
        return v


class Source(Strict):
    id: Provider
    status: Literal['connected','partial','unavailable','error','not_connected']
    available: bool
    last_success_at: str | None
    last_attempt_at: str | None
    files: Count
    total_files: Count | None = None
    warnings: Count
    scan_limit: Count

    @field_validator('last_success_at','last_attempt_at')
    @classmethod
    def valid_time(cls,v):
        if v is None:return None
        parsed=timestamp(v)
        if not parsed:raise ValueError('Timezone required')
        return parsed


class Batch(Strict):
    device_id: HexID
    upload_id: HexID
    events: list[Event] = Field(min_length=1,max_length=250)


class Finish(Strict):
    device_id: HexID
    upload_id: HexID
    count: int = Field(ge=1,le=200000)
    digest: str = Field(pattern=r'^[a-f0-9]{64}$')
    sources: list[Source] = Field(min_length=3,max_length=3)


def canonical(events):
    return json.dumps(sorted(events,key=lambda e:e['event_id']),ensure_ascii=False,sort_keys=True,separators=(',',':'))


def snapshot_digest(events):
    return hashlib.sha256(canonical(events).encode()).hexdigest()


def export_event(e):
    data={k:e[k] for k in Event.model_fields if k in e}
    data.update(session_id=uid(e['session_id']), project_id=uid(e['project_id']),
                source_ref='metadata:'+uid(e['source_ref']),
                title={'activity':'도구 호출','usage':'모델 사용량 기록','session_started':'작업 세션 시작'}[e['event_type']])
    result = Event.model_validate(data).model_dump(exclude_none=True)
    for key in ('usage','raw_usage'):
        if key in data and data[key] is not None: result[key] = Usage.model_validate(data[key]).model_dump()
    return result


def export_source(s):
    return Source.model_validate({k:s.get(k) for k in Source.model_fields}).model_dump()


class Receiver:
    def __init__(self,store,device):
        self.store,self.device=store,device
        with store.db() as c:
            c.executescript('''CREATE TABLE IF NOT EXISTS incoming_runs(id TEXT PRIMARY KEY, created REAL, digest TEXT, count INTEGER);
            CREATE TABLE IF NOT EXISTS incoming_events(run TEXT, id TEXT, data TEXT, PRIMARY KEY(run,id));
            CREATE TABLE IF NOT EXISTS remote_state(id TEXT PRIMARY KEY, state TEXT);''')

    def batch(self,body):
        if body.device_id != self.device: raise PermissionError('Device mismatch')
        with self.store.db() as c:
            c.execute('DELETE FROM incoming_events WHERE run IN (SELECT id FROM incoming_runs WHERE created < ?)',(time.time()-86400,))
            c.execute('DELETE FROM incoming_runs WHERE created < ?',(time.time()-86400,))
            row=c.execute('SELECT digest FROM incoming_runs WHERE id=?',(body.upload_id,)).fetchone()
            if row and row[0]: raise ValueError('Upload already finalized')
            if not row and c.execute('SELECT COUNT(*) FROM incoming_runs').fetchone()[0]>=20:
                raise ValueError('Too many uploads; retry after stale uploads expire')
            c.execute('INSERT OR IGNORE INTO incoming_runs VALUES (?,?,NULL,NULL)',(body.upload_id,time.time()))
            for event in body.events:
                if event.source_id!=event.provider: raise ValueError('Provider mismatch')
                if event.event_type=='usage' and event.usage is None: raise ValueError('Usage missing')
                data=event.model_dump(exclude_none=True)
                # Excluding optional event fields must NOT remove nullable usage measurements.
                if event.usage:data['usage']=event.usage.model_dump()
                if event.raw_usage:data['raw_usage']=event.raw_usage.model_dump()
                c.execute('INSERT OR REPLACE INTO incoming_events VALUES (?,?,?)',(body.upload_id,event.event_id,json.dumps(data,ensure_ascii=False)))
            count=c.execute('SELECT COUNT(*) FROM incoming_events WHERE run=?',(body.upload_id,)).fetchone()[0]
            if count>200000:raise ValueError('Snapshot too large')
        return {'staged':count}

    def finish(self,body):
        if body.device_id!=self.device:raise PermissionError('Device mismatch')
        if {s.id for s in body.sources}!=set(NAMES):raise ValueError('All source states required')
        with self.store.db() as c:
            run=c.execute('SELECT digest,count FROM incoming_runs WHERE id=?',(body.upload_id,)).fetchone()
            if run and run[0]:
                if run[0]!=body.digest or run[1]!=body.count:raise ValueError('Receipt mismatch')
                return {'count':run[1],'digest':run[0],'replayed':True}
            events=[json.loads(r[0]) for r in c.execute('SELECT data FROM incoming_events WHERE run=?',(body.upload_id,))]
            if len(events)!=body.count or snapshot_digest(events)!=body.digest:raise ValueError('Incomplete snapshot')
            file='remote:'+self.device
            c.execute('DELETE FROM events WHERE file=?',(file,))
            c.execute('DELETE FROM event_instances WHERE file=?',(file,))
            for event in events:
                event['event_id']=uid(self.device,event['event_id'])
                event['session_id']=uid(self.device,event['session_id'])
                event['project_id']=uid(self.device,event['project_id'])
                row=(event['event_id'],event['provider'],file,event['occurred_at'],json.dumps(event,ensure_ascii=False))
                c.execute('INSERT OR REPLACE INTO events VALUES (?,?,?,?,?)',row)
                c.execute('INSERT OR REPLACE INTO event_instances VALUES (?,?,?,?,?)',row)
            for source in body.sources:
                state=source.model_dump()
                state.update(name=NAMES[source.id],location='노트북에서 전송된 메타데이터',
                    capabilities=['sessions','model','tokens','tools'] if source.available else [],
                    last_received_at=now(),error=None if source.available else '지원 가능한 노트북 기록 경로를 찾지 못했습니다.')
                c.execute('INSERT OR REPLACE INTO remote_state VALUES (?,?)',(source.id,json.dumps(state,ensure_ascii=False)))
            c.execute('UPDATE incoming_runs SET digest=?,count=? WHERE id=?',(body.digest,body.count,body.upload_id))
            c.execute('DELETE FROM incoming_events WHERE run=?',(body.upload_id,))
        return {'count':body.count,'digest':body.digest,'replayed':False}

    def sources(self):
        with self.store.db() as c:
            rows=[json.loads(r[0]) for r in c.execute('SELECT state FROM remote_state ORDER BY id')]
        return rows or [dict(s,available=False,status='not_connected',location='노트북 전송 대기',error='아직 수신한 기록이 없습니다.') for s in self.store.sources()]
