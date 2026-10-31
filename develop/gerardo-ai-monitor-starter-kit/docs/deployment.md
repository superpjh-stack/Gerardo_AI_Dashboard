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

## 비공개 실제 기록 서비스 — 2026-10-31
- 주소: https://gerardo.187-52-127-215.sslip.io:18790/
- 프로젝트 `gerardo-ai-private`, 서버 경로 `/opt/gerardo-ai-private`.
- 코드 커밋 `78d1c48` (로그인 폼의 same-origin 출처 정책 수정 포함).
- Compose: `deploy/compose.private.yaml`, 프록시: `deploy/Caddyfile.private`.
- 공개 체험판의 서비스와 볼륨을 유지하고 새 private DB에만 실제 기록을 저장한다.
- 기존 443 포트 서비스는 유지. 새 Caddy는 80에서 인증서를 검증하고 18790으로 HTTPS 제공.
- 인증서 검증, 비로그인 API 401, 로그인/로그아웃·세션 만료, 브라우저 폼 오류 처리를 확인했다.
- 실제 메타데이터 최초 전송 완료. 개수·스냅샷 SHA256 및 전체 기간 토큰 집계를 대조했다.
- 개인 집계와 전송 영수증은 Git에 넣지 않는다. 로컬 `.local/private/last-transfer.json`에서 확인한다.
- 24개 pytest, TypeScript/Vite 빌드 통과. 서버 앱 컨테이너 healthy 확인.

### 사용 방법
1. 이 노트북의 `.local/private/접속정보.txt`에서 비밀번호를 확인하여 HTTPS 주소에 로그인한다.
2. 새 기록 전송은 프로젝트의 `실제기록전송.command`를 실행한다. 자동 실행·주기 전송은 설치하지 않았다.
3. 서버 화면의 새로고침은 수신 완료된 기록만 다시 조회한다. 노트북 로그를 원격 스캔하지 않는다.
4. 현재 Claude는 최근 수정 100개 파일과 이전 수집분, Codex는 지원 경로의 최근 최대 100개 파일을 수집한다.
   Antigravity는 지원 가능한 기록 경로를 찾지 못한 상태로 표시한다.

### 비밀 설정과 운영
- `.local/private/`는 소유자 전용(0700), 접속·전송 파일은 0600이며 Git에서 제외된다.
- 서버 `secrets/auth.json`에는 로그인 비밀번호 해시와 전송 키 해시만 있다. 앱 UID 10001만 읽을 수 있다.
- 로그인 세션 만료는 7일이며 서버 DB에 해시만 저장한다. 로그아웃은 서버 세션을 폐기한다.
- `scripts/prepare_private.py`는 신규 설정용이다. 기존 설정이 있으면 덮어쓰지 않고 중단한다.
- 갱신은 `.env`의 MONITOR_REVISION을 검증한 SHA로 설정 후
  `docker compose -p gerardo-ai-private up -d --build`를 실행한다.
- 중지는 `docker compose -p gerardo-ai-private stop`. 볼륨을 삭제하지 않으면 기록과 인증서가 보존된다.
- IP 기반 DNS 서비스에 의존한다. 개인 도메인을 사용하려면 Caddy와 MONITOR_PUBLIC_URL, 로컬 client.json의 주소를 함께 변경한다.

## 모바일 반응형 배포 — 2026-10-31
- private 서비스 코드 `6aecf84` 배포 완료. 기존 HTTPS 주소에서 새로고침하면 적용된다.
- 하단 메뉴·큰 터치 영역·세로 필터·스크롤 차트·전체 화면 상세·로그인 유동 폭 적용.
- 서버 정적 CSS 및 로그인 HTML 갱신, 기존 계정 로그인, 실제 기록 집계 보존, 컨테이너 healthy 확인.
- 검증용 로컬 서버는 종료했다. 실제 모바일 기기의 OS 키보드 동작은 별도 검증 범위다.
