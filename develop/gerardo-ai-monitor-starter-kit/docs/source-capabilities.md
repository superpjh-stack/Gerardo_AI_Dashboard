# 실제 소스 조사 · 2026-10-31

인증정보·대화 전문을 출력하지 않고 지정된 로컬 JSONL의 메타데이터 키와 usage만 확인했다.

| 도구 | 확인한 소스/형태 | 세션·모델 | 사용량 의미 | 현재 판정 |
|---|---|---|---|---|
| Claude | ~/.claude/projects/**/*.jsonl, 로컬 assistant 메시지 | sessionId, agentId, message.model | message.usage, 응답 ID 반복 제거. 입력·출력·캐시 읽기·쓰기 합산 | 부분 지원: 최근 수정 100개 / 조사 시 전체 336개 |
| Codex | ~/.codex/sessions/**/*.jsonl, cli_version 0.166.0, source vscode | session_meta, turn_context.model | event_msg/token_count의 total_token_usage 차이. cached_input은 input에 포함 | 지원: 조사 시 31개 파일 |
| Antigravity | ~/.gemini/antigravity 및 Library/Application Support/Antigravity/logs 확인 | 미확인 | 미확인 | 연결 미확인 |

Applications 및 사용자 Applications의 이름 목록에서도 Antigravity를 찾지 못했다. 다른 위치에 설치되지 않았다고 단정하지 않는다.
Claude.app 4.4212.0은 발견했으나 해당 앱 버전이 모든 JSONL을 작성한 버전이라는 의미는 아니다.
원본 샘플과 전체 경로·프롬프트는 공유 문서에 복사하지 않는다.

## 구현 범위
- Claude message.id와 requestId로 동일 응답 chunk 중복 제거. 가장 큰 출력 값 보존.
- 로컬 `<synthetic>` 응답은 실제 사용량에서 제외한다.
- Codex의 token_usage_record를 token_count와 함께 더하지 않는다.
- 누적 감소는 reset으로 추정해 합산하지 않고 경고로 격리한다.
- 최초 관측 누적값은 해당 관측 시각에 귀속한다. 이전 실제 발생 시간은 확정하지 않는다.
- 로그 형식은 관찰 기반 어댑터이며 공식 안정 API로 보장하지 않는다. 버전 변화 시 fixture를 갱신한다.
- 요금·잔여 한도·검증 성공·Git 작성자·프롬프트 의미 분석은 미수집이다.

## 근거
구현: backend/monitor/adapters.py. 비식별 합성 fixture: backend/tests/test_monitor.py.
캐시 필드 해석 보조: [Claude 공식 캐시 문서](https://platform.claude.com/docs/en/build-with-claude/prompt-caching).
