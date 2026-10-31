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

## private 모드
로그인 `/login` → POST `/auth/login` → Secure/HttpOnly/SameSite=strict 세션(7일).
POST `/auth/logout`은 서버 세션을 폐기한다. 로그인/로그아웃은 정확한 HTTPS Origin을 요구한다.
health/login 외 모든 조회는 로그인 필요. 기존 로컬 변경 토큰도 로그인 후 발급한다.
로그인 자격 증명과 전송 Bearer는 분리한다. Bearer로 대시보드를 조회할 수 없다.
POST `/transfer/batch`: 허용 필드 이벤트 250개 이하, 전체 요청 2MiB 이하. 임시 저장만 수행.
POST `/transfer/finish`: 기기/업로드 ID·전체 개수·정렬된 payload SHA256·소스 상태 3종을 검증한 뒤 원자 반영.
잘못된 스키마 422, 인증 실패 401, 기기 불일치 403, 스냅샷 불일치 409. 미완료 전송은 기존 기록을 변경하지 않는다.
서버는 노트북 소스를 직접 수집하지 않는다. 로컬 sync 요청은 409와 안내 문구를 반환한다.
