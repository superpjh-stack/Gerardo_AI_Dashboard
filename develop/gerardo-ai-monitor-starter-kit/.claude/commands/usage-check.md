---
description: 사용량 집계 검증
argument-hint: "<작업 스펙 경로 또는 요청>"
---

대상: $ARGUMENTS

프로젝트 루트에서 AGENTS.md, goal.md, decisions.md, progress.md를 먼저 읽는다.
이 파일은 작업 프롬프트이며 현재 앱 구현 여부를 먼저 확인한다.

contracts/events.md와 docs/acceptance.md를 기준으로 중복, 누적, 캐시, null, 한국시간 경계, synthetic 제외를 검증한다. 불일치 원인을 설명하고 실패를 숨기지 않는다.

결과는 변경 파일·검증 명령과 결과·미검증·남은 일로 보고한다.
