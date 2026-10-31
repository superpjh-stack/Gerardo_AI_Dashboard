---
description: 다른 AI에게 작업 인계
argument-hint: "<작업 스펙 경로 또는 요청>"
---

대상: $ARGUMENTS

프로젝트 루트에서 AGENTS.md, goal.md, decisions.md, progress.md를 먼저 읽는다.
이 파일은 작업 프롬프트이며 현재 앱 구현 여부를 먼저 확인한다.

현재 diff와 실제 검증 결과를 확인한 후 docs/handoff.md 형식으로 인계 블록을 작성한다. 담당 파일, 완료 조건, 미검증, 다음 작업을 명시한다. 다른 AI를 자동 실행하지 않는다.

결과는 변경 파일·검증 명령과 결과·미검증·남은 일로 보고한다.
