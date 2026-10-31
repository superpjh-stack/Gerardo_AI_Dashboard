# Hostinger VPS 배포

대상: VPS 1934103. 최초 배포는 공개 읽기 전용 체험판이다.
노트북의 실제 이벤트·DB·로그는 업로드하지 않는다. MONITOR_DEPLOYMENT=demo에서는
`demo=false` 요청도 합성 자료로 강제하며 모든 POST를 거부한다.
실제 데이터 연동에는 인증·HTTPS·노트북 수집기 전송 구성을 별도로 추가해야 한다.

## Docker 구성
- Node 빌드 단계에서 React 정적 파일 생성, Python 런타임에 UI와 API를 함께 포함.
- 비루트 UID 10001, 읽기 전용 파일시스템, 전용 SQLite 볼륨, healthcheck.
- build context는 공개 GitHub 저장소의 앱 하위 폴더. 로컬 DB·로그·환경변수는 .dockerignore로 제외.
- MONITOR_PUBLIC_URL은 실제 외부 origin과 정확히 맞춰 설정. 허용 Host·Origin에 추가한다.
- 외부 18788 → 컨테이너 8765. 다른 기존 서비스 포트·설정을 변경하지 않는다.

## Docker Manager
애플리케이션 이름 `gerardo-ai-dashboard`. deploy/compose.hostinger.yaml을 YAML 편집기에 붙여넣고 배포한다.
재현 가능한 릴리스는 build.context의 #main을 배포한 커밋 전체 SHA로 바꾼다.
현재 예시는 직접 IP의 HTTP 체험판이다. 비밀·인증·개인 활동 데이터를 이 경로로 보내지 않는다.

## 검증
- `uv run pytest -q`: 로컬 모드 회귀와 서버 체험판 데이터 격리.
- `npm --prefix frontend run build`, `docker build -t gerardo-ai-dashboard:deploy .`.
- 컨테이너 /api/v1/health, /, /activity, 정적 assets, /overview 응답 확인.
- 실제 DB를 주입해도 체험판에서 읽히지 않는 것을 테스트로 확인.
- VPS 배포 후 외부 URL의 UI/API와 POST 거부를 다시 확인한다.

## 배포 결과 — 2026-10-31
- URL: http://187.52.127.215:18788/
- 프로젝트: `gerardo-ai-dashboard`, 컨테이너: `gerardo-ai-dashboard-dashboard-1` (healthy).
- 배포 커밋: `ab7f9ed4b3368097d6113f178bbfecfb1bcdbca4`.
- 서버 구성: `/opt/gerardo-ai-dashboard/compose.yaml`, 빌드 로그: `/opt/gerardo-ai-dashboard/deploy.log`.
- hPanel 최초 배포에서 `Docker project not found` 오류 발생. 인증된 Hostinger 웹 콘솔에서 동일한 Compose를 커밋 SHA로 고정하여 빌드·기동했다.
- 외부 health, 루트 화면, /activity, overview와 events API에서 HTTP 200 확인. 실제 브라우저에서 VPS 체험판 표시와 차트 확인.
- POST /api/v1/scan은 HTTP 403 `demo_readonly`. 개인 로그·DB는 전송하지 않았다.
- 운영 명령: `docker compose -p gerardo-ai-dashboard -f /opt/gerardo-ai-dashboard/compose.yaml ps`.
