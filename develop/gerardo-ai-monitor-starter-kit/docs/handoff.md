# AI 간 인수인계

자동으로 다른 AI를 실행하는 기능이 아니다. 사용자가 도구를 전환할 때 아래 블록을 복사한다.

```text
작업 ID:
목표 / 완료 조건:
담당 도구 / 브랜치:
읽을 계약과 스펙:
변경 파일 / 동시에 수정하면 안 되는 파일:
완료한 내용:
실행한 검증과 결과:
미검증 / 차단 / 사용자 결정 필요:
다음 한 단계:
```

같은 파일의 병행 수정은 피하고, 이어받은 도구는 현재 diff와 실제 파일부터 확인한다.
이전 도구의 완료 보고만으로 테스트 통과를 재보고하지 않는다.

## SYNC-001 · Codex · 2026-10-31
- 승인된 실제 메타데이터 전송: private 인증, 전송 스키마/임시 배치/원자 반영, 수동 전송 명령, VPS 상태 UI.
- 변경: backend/monitor/{app,security,transfer}.py, frontend/src/{App,api,types}, scripts/{transfer,prepare_private}.py, deploy/compose.private.yaml 및 Caddyfile.private.
- 검증: 24개 pytest 통과, TypeScript/Vite 빌드 통과. 서버 배포·최초 전송 결과는 docs/deployment.md에 후속 기록.
- writing-plans 스킬 미설치: docs/superpowers/plans에 수동 실행 계획을 기록하고 승인된 설계를 순차 구현.
- SYNC-001 완료: HTTPS 인증서 정상, 인증 없는 데이터 접근 차단, 최초 실제 전송의 SHA256/개수·집계 일치.
- 후속 수정 78d1c48: 브라우저 form POST에서 Origin이 null이 되는 no-referrer 정책을 same-origin으로 교체. CUA로 비밀번호 검증 화면 확인.
- 로컬 비밀 파일/전송 결과는 Git 제외. 공개 저장소에는 실제 프로젝트 목록·개인 집계를 기록하지 않음.

## AUTH-002 · Codex · 2026-10-31
- 사용자 요청에 따라 아이디/비밀번호 로그인을 추가하고 비공개 자격 증명을 변경했다.
- 인증 설정 지문이 바뀌면 이전 세션을 폐기한다. 전송 전용 키와 실제 활동 DB는 유지한다.
- 잘못된 아이디, 이전 비밀번호, 이전 세션 거부 및 새 로그인 테스트 포함 25개 테스트 통과.
- 비밀번호 원문은 로컬 비공개 접속 파일만 갱신하며 Git에 포함하지 않는다.

## UI-002 · Codex · 2026-10-31
- 요청: 휴대폰에서 읽기 편한 반응형 개선.
- 변경: frontend/src/App.tsx, styles.css, index.html, backend/monitor/security.py의 로그인 레이아웃.
- 모바일 하단 메뉴·큰 글자/터치 영역·세로 필터·활동 카드·상세 스크롤 및 로그인 폭 개선.
- 검증: TypeScript/Vite 빌드, 25개 백엔드 회귀 테스트, Chrome 로컬 프레임에서 모바일/태블릿/데스크톱 폭과 가로 넘침 확인.
- 검증용 서버·데이터는 .local에만 생성. 운영 인증·개인 기록·전송 설정은 유지.

## COST-001 · Codex · 2026-10-31
- 요청: 세 도구의 토큰과 통계적인 비용 표시.
- 변경: backend/monitor/pricing.py와 service.py/app.py, frontend types/App/styles, test_pricing.py.
- 공식 OpenAI·Anthropic·Google 단가 스냅샷, 정확한 모델 ID 매칭, 캐시 포함/제외 처리, 캐시 쓰기 범위 추정.
- 대시보드 합계, 도구·프로젝트·세션별 비용, 사용량 화면의 일별 통계·단가·공식 출처.
- 실제 청구/구독료 미연동. Antigravity 미수집은 null. 알려지지 않은 모델은 산정 제외.
- 검증: pytest 30개 통과, frontend production build 성공. Chrome 제어 연속 시간 초과로 이번 실화면 QA 미완료.
- 가격 기준일 고정이며 자동 갱신하지 않는다. 장문/고속 할증·세금·할인·도구/저장 비용 제외를 UI에 명시.
