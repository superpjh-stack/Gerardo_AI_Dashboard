from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from .adapters import FIELDS, uid
from .store import NAMES

KST = ZoneInfo('Asia/Seoul')


def period_bounds(period, clock=None):
    current = (clock or datetime.now(KST)).astimezone(KST)
    start = current.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == 'week':
        start -= timedelta(days=start.weekday())
    elif period == 'month':
        start = start.replace(day=1)
    elif period == 'all':
        start = datetime(2000, 1, 1, tzinfo=KST)
    elif period != 'today':
        raise ValueError('지원하지 않는 기간입니다.')
    end = current.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return start.astimezone(timezone.utc).isoformat(), end.astimezone(timezone.utc).isoformat()


def totals(events):
    usage = [e for e in events if e['event_type'] == 'usage']
    result = {k: sum(e['usage'][k] for e in usage if e['usage'].get(k) is not None)
              if any(e['usage'].get(k) is not None for e in usage) else None for k in FIELDS}
    result.update(included_count=sum(e['usage'].get('total_tokens') is not None for e in usage),
                  missing_count=sum(e['usage'].get('total_tokens') is None for e in usage),
                  estimated_count=sum(e.get('quality') == 'estimated' for e in usage))
    return result


def overview(events, sources, confirmations, period='today', project='all', provider='all', start=None, end=None):
    if start is None:
        start, end = period_bounds(period)
    selected = [e for e in events if start <= e['occurred_at'] < end
                and (project == 'all' or e['project_id'] == project)
                and (provider == 'all' or e['provider'] == provider)]
    sessions = defaultdict(list)
    for event in selected:
        sessions[uid(event['provider'], event['session_id'])].append(event)
    tasks = []
    for task_id, group in sessions.items():
        group.sort(key=lambda e: e['occurred_at'])
        last = group[-1]
        tools = Counter(e.get('tool') for e in group if e.get('tool'))
        tasks.append(dict(id=task_id, provider=last['provider'], project=last['project'],
            project_id=last['project_id'], title=last['project'] + ' 작업 세션',
            summary=' · '.join(f'{name} {count}회' for name, count in tools.most_common(3)) or '모델 사용 기록이 수집되었습니다.',
            model=next((e.get('model') for e in reversed(group) if e.get('model')), None),
            occurred_at=last['occurred_at'], started_at=group[0]['occurred_at'],
            event_count=len(group), tool_count=sum(tools.values()), usage=totals(group),
            status='user_confirmed' if task_id in confirmations else 'recorded',
            synthetic=last.get('synthetic', False)))
    tasks.sort(key=lambda t: t['occurred_at'], reverse=True)
    providers = []
    for key, name in NAMES.items():
        group = [e for e in selected if e['provider'] == key]
        source = next(s for s in sources if s['id'] == key)
        providers.append(dict(id=key, name=name, source=source, usage=totals(group),
            sessions=sum(t['provider'] == key for t in tasks),
            latest=max((e['occurred_at'] for e in group), default=None),
            models=list(dict.fromkeys(e['model'] for e in reversed(group) if e.get('model')))))
    daily = defaultdict(list)
    for e in selected:
        if e['event_type'] == 'usage':
            day = datetime.fromisoformat(e['occurred_at']).astimezone(KST).strftime('%Y-%m-%d')
            daily[day].append(e)
    day_start = datetime.fromisoformat(start).astimezone(KST)
    day_end = datetime.fromisoformat(end).astimezone(KST)
    if period == 'all' and daily:
        day_start = datetime.fromisoformat(min(daily)).replace(tzinfo=KST)
    if (day_end-day_start).days > 62:
        day_start = day_end - timedelta(days=62)
    series = []
    while day_start < day_end:
        day = day_start.strftime('%Y-%m-%d')
        series.append({'date': day, **{p: totals([e for e in daily[day] if e['provider'] == p])['total_tokens'] for p in NAMES}})
        day_start += timedelta(days=1)
    projects = []
    for project_id in {e['project_id'] for e in selected}:
        group = [e for e in selected if e['project_id'] == project_id]
        projects.append({'id': project_id, 'name': group[0]['project'], 'usage': totals(group),
            'sessions': sum(t['project_id'] == project_id for t in tasks),
            'providers': sorted(set(e['provider'] for e in group))})
    projects.sort(key=lambda p: p['usage']['total_tokens'] or 0, reverse=True)
    total = totals(selected)
    covered = sum(p['usage']['total_tokens'] is not None for p in providers)
    confirmed = sum(t['status'] == 'user_confirmed' for t in tasks)
    return dict(usage=total, sessions=len(tasks), confirmed=confirmed, pending=len(tasks)-confirmed,
        providers=providers, tasks=tasks, projects=projects, series=series,
        coverage={'providers_with_usage': covered, 'providers_total': 3,
                  'missing_providers': [p['name'] for p in providers if p['usage']['total_tokens'] is None]},
        briefing=f'{len(projects)}개 프로젝트에서 {len(tasks)}개 작업 세션을 확인했습니다. '
                 f'사용자 확인 완료 {confirmed}개, 검토할 세션 {len(tasks)-confirmed}개입니다.' if tasks else '아직 이 기간에 수집된 활동이 없습니다. 소스를 연결하거나 조회 기간을 바꿔보세요.',
        timezone='Asia/Seoul', period={'from': start, 'to': end},
        recent_events=list(reversed(selected[-200:])))


def demo_events():
    """Synthetic data is generated in memory and never inserted into the real DB."""
    events = []
    now = datetime.now(KST)
    for day in range(7):
        for i, provider in enumerate(NAMES):
            for j in range(2):
                time = (now - timedelta(days=day)).replace(hour=9+i*3+j, minute=12+j*17, second=0, microsecond=0)
                project = ['AI 활동 모니터링', '개인 포트폴리오', '업무 자동화'][j if day % 2 else i]
                usage = dict(input_tokens=18000+(6-day)*2300+i*1200, output_tokens=2200+j*800,
                             cache_read_tokens=6000+i*1000, cache_write_tokens=0)
                usage['total_tokens'] = usage['input_tokens']+usage['output_tokens']
                session = f'demo-{provider}-{day}-{j}'
                events.append(dict(event_id=uid(session), provider=provider, source_id=provider, session_id=session,
                    project=project, project_id=uid('demo',project), model=['Claude · 예시','Codex · 예시','Gemini · 예시'][i],
                    event_type='usage', occurred_at=time.astimezone(timezone.utc).isoformat(), title='예시 모델 사용량',
                    usage=usage, quality='measured', synthetic=True, source_ref='synthetic-fixture',
                    cache_semantics='included', usage_mode='delta'))
    return sorted(events, key=lambda e:e['occurred_at'])
