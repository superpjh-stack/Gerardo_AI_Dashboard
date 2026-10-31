# 로컬 API v0.1

접두 `/api/v1`, JSON, 날짜는 UTC. API 8765 / UI 5188. OpenAPI는 실행 서버의 /docs와 /openapi.json에서 제공한다.

| 메서드 | 경로 | 목적 |
|---|---|---|
| GET | /health | 앱 상태. 소스별 장애는 sources에서 별도 반환 |
| GET | /sources | 소스 상태·capabilities·last_success_at·last_attempt_at·오류 |
| POST | /sources | provider로 지정된 기본 로컬 소스 연결·동기화 |
| POST | /sources/{id}/sync | 등록 소스 수집 요청. 원본 변경 없음 |
| GET | /overview | 기간·프로젝트·도구 필터의 요약과 coverage |
| GET | /events | 필터·cursor·limit 기반 활동 조회 |
| GET | /projects | 프로젝트 및 미분류 항목 |
| GET | /usage | 동일 필터의 사용량과 누락 범위 |
| GET | /tasks/{id} | 요약·evidence refs·메모·확인 기록 |
| POST | /tasks/{id}/notes | 사용자 메모 |
| POST | /tasks/{id}/confirmations | 사용자 완료 확인, 검증 상태와 분리 |

조회 기간: from inclusive, to exclusive, timezone 기본 Asia/Seoul. 잘못된 기간은 422.
목록 limit 기본 50, 최대 200. 이벤트 정렬은 occurred_at과 event_id로 안정화한다.
오류: {error: {code, message, retryable}}. 404 미존재, 409 동기화 중, 422 입력 오류.
소스 한 개 오류로 전체 overview를 실패시키지 않고 coverage와 경고를 함께 반환한다.
POST sources의 본문은 {"provider":"claude"|"codex"|"antigravity"}. 임의 경로 입력을 받지 않는다. 기본 소스 경로의 JSONL만 읽고 symlink 경계를 검사한다.
기본 localhost 바인딩, 허용 Origin 제한, 변경 요청의 로컬 토큰 검증. 원문 파일을 임의 URL로 제공하지 않는다.
GET /session은 변경 요청에 필요한 로컬 토큰을 반환한다. POST는 X-Local-Token 헤더가 필요하다.
조회는 period=today|week|month|all, project, provider, demo를 지원한다. from/to 사용자 지정 기간은 overview에서 지원한다. 시간대는 현재 Asia/Seoul 고정이다. events의 cursor는 현재 정렬 결과의 오프셋 정수이며 동기화 시 페이지 경계가 달라질 수 있다.
현재 DTO 정의는 frontend/src/types.ts, 서버 핸들러는 backend/monitor/app.py에 있다. 커스텀 경로 등록은 후속 범위다.
