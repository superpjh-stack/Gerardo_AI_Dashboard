# 제라도의 AI 활동 모니터링 바이브코딩 가이드

작성일: 2026-10-31. 대상: Claude · Codex · Antigravity를 사용하는 개인용 로컬 대시보드.
이 문서는 초기 기획과 현재 구현 기준을 함께 담는다. 최신 구현 상태는 다음 절과 README를 따른다.

## 현재 개발 상태 · 2026-10-31

이 가이드의 초기 기획에 따라 실행 앱을 구현했다. 화면은 http://127.0.0.1:5188/, API는 8765다.
킷의 start.command 또는 `uv run python scripts/dev.py`로 실행한다.
Claude/Codex 로컬 수집, 화면 5종, 메모·확인, 예시 모드가 동작한다. Antigravity는 연결 미확인이다.
실제 실행 방법과 제약의 최신 기준은 README.md, progress.md, docs/source-capabilities.md다.



## 1. 만들 제품
“오늘 세 AI가 무엇을 했고, 어디에 토큰이 들었으며, 내가 다음에 무엇을 확인할지”를 한 화면에서 파악한다.
사용량과 작업 결과를 프로젝트·세션·근거로 연결한다. AI별 생산성 순위를 임의로 계산하지 않는다.

첫 버전: 연결 상태, 기간/프로젝트 필터, 도구 카드, 작업 타임라인, 토큰 분석, 근거형 일보, 메모·확인.
후속: AI 바통 터치, 토큰 영수증 고도화, 주간 회고, 작업 별자리.

## 2. 폴더와 시작 방법
`develop/gerardo-ai-monitor-starter-kit/`을 프로젝트 루트로 연다. 기존 MES 자료와 별개다.
킷의 README.md → AGENTS.md → goal.md → contracts/ → decisions.md → docs/backlog.md → progress.md 순서로 읽는다.
`frontend/src/`, `backend/monitor/`에 실행 코드가 있고 `backend/tests/`에 검증이 있다.
가이드 전문은 develop의 외부 파일과 킷의 docs/guide.md에 동일하게 유지한다.

## 3. 기술 방향
React + TypeScript UI, Python + FastAPI API, SQLite 저장소, 도구별 읽기 전용 수집기 구조를 제안한다.
의존성 버전은 구현 시 공식 문서와 실제 환경을 확인해 lock 파일로 고정한다.
로컬 UI 5188 / API 8765를 사용한다. 충돌 시 설정과 허용 Origin을 함께 변경한다.
초기 설정은 `uv sync`, `npm --prefix frontend ci`. 실행은 `uv run python scripts/dev.py`.
검증은 `uv run pytest -q`, `npm --prefix frontend run build`.

## 4. 세 AI 활용
공통 규칙의 정본은 AGENTS.md다. 작업 역할은 도구 이름에 고정하지 않는다.
Claude는 CLAUDE.md와 .claude/commands/ 작업 프롬프트를 읽는다.
Codex는 AGENTS.md와 prompts/codex-start.md를 사용한다.
Antigravity는 prompts/antigravity-start.md를 대화에 붙여 넣어 같은 규칙을 읽게 한다.
특정 설정 파일이 자동 로드된다고 전제하거나 권한 설정을 일괄 복사하지 않는다.
기본은 순차 작업이며 인수인계는 docs/handoff.md로 한다. 공용 파일을 동시에 수정하지 않는다.

## 5. 실제 데이터 확보
M0에서 설치 형태·버전·허용 소스·필드 의미를 먼저 조사한다.
공식 내보내기/문서화된 연동/허용 로컬 기록을 확인하고 docs/source-capabilities.md에 근거를 남긴다.
인증정보를 수집하지 않고 지정한 경로만 읽는다. 미지원 항목은 null과 사유로 표시한다.
한 수집기 장애가 다른 도구 조회를 막지 않도록 마지막 성공과 최근 시도를 분리한다.
원본 파일·프로젝트는 읽기 전용이며 앱 데이터는 전용 .local 저장소에만 쓴다.

## 6. 반드시 지킬 숫자 규칙
- 도구와 모델을 분리한다. model이 없으면 미확인으로 둔다.
- null과 0을 구분하고 실측/추정/수동/미수집 및 출처를 보존한다.
- 누적과 증분, 캐시 포함 여부를 확인한 뒤 집계한다.
- 재수집은 멱등이어야 하며 로그 회전·reset·늦게 온 기록을 검증한다.
- 한국시간 기준 날짜 경계를 UTC 조건으로 변환한다.
- 일부 도구만 수집되면 “수집된 토큰”과 누락 범위를 표시한다.
- API 실제 비용·API 환산액·정액 구독료를 분리한다. 한도와 단가는 확인 없이 만들지 않는다.
- Git 변경만으로 작성 AI를 확정하지 않고 완료 발언·검증·사용자 확인을 분리한다.

## 7. 화면 방향
짙은 네이비 배경과 살구/민트/보라 구분색을 사용한다. 오늘의 성과와 확인할 일을 먼저 보여준다.
상단 필터 → 브리핑 → 핵심 지표 → AI 카드 → 타임라인/확인할 일 → 사용량 순서다.
처음 실행했을 때는 연결 안내를 표시한다. 데모는 명시적인 별도 모드다.
390/1280/1440px, 키보드 접근, 차트 대응 표, 로딩·빈 상태·부분 수집·오류를 검증한다.
구체 기준은 contracts/screens.md와 docs/ui-guide.md를 따른다.

## 8. 개발 순서와 프롬프트
1. `/source-audit`: 실제 지원표와 비식별 fixture 조건 확인.
2. `/backlog`, `/ingest`: 첫 작업의 범위·계약·완료 조건 확정.
3. `/backend-init`, `/frontend-init`: 구현 요청 시 앱 골격 생성.
4. `/collector`: 확인된 소스 하나의 멱등 수집.
5. `/feature`, `/screen`: 조회 API와 대시보드 기능 연결.
6. `/usage-check`: 집계 불변조건 확인.
7. `/handoff`, `/docgen`: 근거 있는 진행 보고와 문서 갱신.
위 슬래시 이름은 Claude용 프롬프트 파일이다. 다른 도구는 같은 파일 내용을 읽고 작업할 수 있다.

공통 시작 요청 예시:
> AGENTS.md와 goal.md, contracts/를 읽고 docs/backlog.md의 M0부터 진행해. 실제 소스와 지원 필드를 확인해 docs/source-capabilities.md에 근거를 남겨줘. 모르는 값은 미확인으로 두고 원본 로그나 인증정보는 문서에 복사하지 마.

## 9. 검증과 완료
docs/acceptance.md는 계획이다. 실행 전에는 통과로 기록하지 않는다.
필수 검증은 재수집, counter·캐시 의미, null, 시간대, 부분 실패, checkpoint 복구, 예시 분리, 근거 연결이다.
구현 후에는 실제 UI 동작과 API·집계 테스트를 확인한다. 결과를 progress.md에 기록한다.
문서만 수정하는 작업은 상대 링크·도메인 잔재·중복 가이드 일치를 확인하면 된다.

## 10. 작업 종료 보고
변경 파일, 실제 실행한 검증과 결과, 미검증, 다음 작업을 짧게 보고한다.
실제 앱이 없으면 개발 문서 준비 완료라고 말한다. 연동 미확인을 연동 완료로 표현하지 않는다.
