---
description: 세 도구의 실제 수집 가능 범위 조사
argument-hint: "<작업 스펙 경로 또는 요청>"
---

대상: $ARGUMENTS

프로젝트 루트에서 AGENTS.md, goal.md, decisions.md, progress.md를 먼저 읽는다.
이 파일은 작업 프롬프트이며 현재 앱 구현 여부를 먼저 확인한다.

docs/spec/001-source-discovery.md와 docs/source-capabilities.md를 따른다. 지정한 소스만 확인하고 토큰·캐시·누적 의미와 근거를 기록한다. 지원되지 않는 필드를 발명하지 않는다.

결과는 변경 파일·검증 명령과 결과·미검증·남은 일로 보고한다.
