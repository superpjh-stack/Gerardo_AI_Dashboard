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
