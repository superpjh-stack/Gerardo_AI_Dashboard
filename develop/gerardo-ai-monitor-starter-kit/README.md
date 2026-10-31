# 제라도의 AI 활동 모니터링

세 AI의 토큰 사용량과 작업 기록을 한곳에 모으는 로컬 대시보드. React + TypeScript / FastAPI / SQLite.
2026-10-31: 문서 스타터킷에서 실행 가능한 초기 버전으로 확장했습니다.

## 실행

이 폴더의 **[start.command](start.command)를 더블클릭**하면 두 서버와 브라우저를 엽니다.
이미 실행 중이면 기존 화면을 사용하세요: **http://127.0.0.1:5188/**
API: http://127.0.0.1:8765/docs . 다른 앱의 localhost:5173과 구분하기 위해 화면 포트를 5188로 선택했습니다.

터미널에서 실행하려면 이 폴더에서:

```bash
uv sync
npm --prefix frontend ci
uv run python scripts/dev.py
```

종료는 실행 터미널에서 Ctrl+C. 위 실행기는 자신이 시작한 프로세스만 종료합니다.
처음 화면에서 ‘지금 동기화’를 누르면 지정된 로컬 기록을 수집합니다.
‘데이터 소스’에서 1분 간격 동기화를 켤 수 있습니다. 브라우저가 열린 동안에만 동작합니다.

## 현재 기능
- Claude / Codex JSONL 메타데이터 읽기 전용 수집, 파일별 변경 감지, 중복 방지
- 오늘·이번 주·이번 달·전체 / 프로젝트 / 도구 필터
- AI 카드, 프로젝트별 타임라인, 일별 토큰 차트와 표
- 세션 상세, 로컬 근거 참조, 메모, 사용자 검토 완료 표시
- 로컬 규칙형 브리핑, 별도로 켜는 합성 예시 모드
- 미수집·부분 수집·연결 오류 표시, 키보드 접근과 반응형 CSS

## 연동과 한계
- Claude: `~/.claude/projects`에서 최근 수정 로그 최대 100개. 전체 로그를 모두 수집한 것이 아닙니다.
- Codex: `~/.codex/sessions`에서 최근 수정 로그 최대 100개.
- Antigravity: 확인한 경로에서 지원 소스를 발견하지 못해 미연결 상태입니다.
- `MONITOR_MAX_FILES=300 uv run python scripts/dev.py`처럼 수집 상한을 변경할 수 있습니다.
- ‘전체’는 **이 앱이 수집한 전체 기록**입니다. 삭제된 원본은 재구성하지 않습니다.
- 한 일은 프로젝트·세션·도구 호출 기반입니다. 대화 전문·코드·도구 인자를 저장하거나 외부로 전송하지 않습니다.
- 검증 자동 수집, Git 연결, 의미 기반 작업 요약, 비용·구독·잔여 한도는 아직 구현하지 않았습니다.
- 세션 상세는 현재 화면의 패널로 열립니다. 독립 상세 URL은 후속 범위입니다.
- 날짜는 Asia/Seoul 기준이며 누적 사용량은 관측 시각에 귀속합니다.

## 검증

```bash
uv run pytest -q
npm --prefix frontend run build
```

자동 테스트 15개: 누적·캐시·중복·지연 기록·null·자정·복사/회전·파일 잘림·DB 롤백·메모·확인·Origin/Host 제한·예시 분리.
실행 결과와 UI 확인 범위는 [진행 기록](progress.md)을 봅니다.

## 구조
- `backend/monitor/adapters.py`: 관찰한 JSONL 형식 파서
- `backend/monitor/store.py`: SQLite, 파일 스냅샷·중복 제거·메모
- `backend/monitor/service.py`: 기간·프로젝트 집계와 예시 데이터
- `backend/monitor/app.py`: 로컬 API, Origin·Host·변경 요청 토큰 검사
- `frontend/src/`: 대시보드·타임라인·프로젝트·사용량·소스 화면
- `.local/`: 로컬 DB. Git 제외, 원본 로그와 분리

[가이드](docs/guide.md) · [기획](docs/product-plan.md) · [구현 계획](docs/plans/2026-10-31-mvp.md) · [공통 규칙](AGENTS.md) · [연동 조사](docs/source-capabilities.md) · [백로그](docs/backlog.md)

Codex는 AGENTS.md, Claude는 CLAUDE.md와 .claude/commands/, Antigravity는 [시작 프롬프트](prompts/antigravity-start.md)를 사용합니다.

## VPS에서 실제 기록 보기
HTTPS 개인 작업실: https://gerardo.187-52-127-215.sslip.io:18790/
비밀번호는 이 노트북의 `.local/private/접속정보.txt`에 저장되어 있다(Git 제외).
`실제기록전송.command`를 실행하면 지정된 로컬 소스를 다시 읽고 메타데이터만 전송한다.
대화·코드·도구 인자·원본 경로·로컬 메모는 전송하지 않는다. 전송은 수동이며 자동 시작 작업은 없다.
서버의 “수신 기록 새로고침”은 이미 받은 기록을 조회한다.
자세한 배포·수집 범위·운영 방법은 [배포 문서](docs/deployment.md)를 참고한다.
