---
description: 소스 어댑터 구현
argument-hint: "<작업 스펙 경로 또는 요청>"
---

대상: $ARGUMENTS

프로젝트 루트에서 AGENTS.md, goal.md, decisions.md, progress.md를 먼저 읽는다.
이 파일은 작업 프롬프트이며 현재 앱 구현 여부를 먼저 확인한다.

지원표에서 확인된 소스 하나만 대상으로 한다. 읽기 전용 파싱, 안정 ID, 정규화, 원자적 checkpoint와 오류 격리를 구현한다. 합성 fixture로 중복·회전·불완전 행·counter reset을 검증한다.

결과는 변경 파일·검증 명령과 결과·미검증·남은 일로 보고한다.
