# 정규화 이벤트 계약 초안 v0.1

## 식별과 출처
각 이벤트는 event_id, source_id, provider(claude/codex/antigravity), model(nullable), session_id,
project_id(nullable), event_type, occurred_at(UTC ISO 8601), observed_at, source_ref, parser_version, synthetic을 가진다.
source_ref는 로컬 소스 식별자와 레코드 위치이며 UI에는 민감한 원문·절대 경로를 무조건 노출하지 않는다.
모든 측정값은 value, quality(measured/estimated/manual/unavailable), evidence_ref를 갖는다. unavailable의 value는 null.

## 이벤트 종류
session_started, activity, usage, artifact_changed, verification, task_note, task_confirmed.
원본이 없는 사건은 생성하지 않는다. Git artifact_changed는 관련 세션 연결을 별도 confidence로 보존한다.

## 사용량
usage는 input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, total_tokens(모두 nullable 정수),
usage_mode(delta/cumulative), counter_scope, counter_epoch, cache_semantics(included/excluded/unknown)를 포함한다.
원본 총합이 명시되면 출처와 함께 보존한다. 총합이 없고 의미가 확정된 경우에만 정규화 총합을 계산한다.
캐시가 input에 포함되면 다시 더하지 않는다. 제외된 경우에는 동일 단위·범위임을 확인한 뒤 더한다.
필수 항목이 null이거나 의미가 unknown이면 계산 총합은 null로 남긴다. 일부 항목은 따로 보여준다.

## 멱등성과 누적 카운터
- 안정적인 원본 record ID가 있으면 (source_id, record ID, event_type)에 유일성을 둔다.
- 없으면 파일 identity + 레코드 위치 + 내용 해시로 수집 ID를 구성한다. 파일 교체·회전은 따로 식별한다.
- 복사된 동일 로그의 두 번 등록은 source 등록 단계에서 감지한다. 불확실하면 집계에서 격리하고 알린다.
- 누적 counter는 동일 scope/epoch에서 이전 값과 차이만 반영한다. 최초 값은 관측 이전분을 포함할 수 있음을 표시한다.
- 감소는 음수 사용량으로 넣지 않고 reset 여부를 확인한다. 불명확하면 격리한다.
- 늦게 온 기록은 시각순으로 해당 scope를 다시 계산한다. 원본 누적치와 파생 증분치를 함께 합산하지 않는다.
- DB 이벤트 반영과 수집 체크포인트 갱신은 하나의 트랜잭션으로 처리한다.

## 날짜와 집계
표시 시간대 기본은 Asia/Seoul. 오늘은 해당 시간대의 [00:00, 다음 날 00:00), 주는 월요일 시작.
기간 조건은 UTC로 변환해 조회한다. 누적 사용량의 발생 시각을 알 수 없으면 관측 시각에 귀속하고 추정 표시한다.
총합에는 known_total, included_count, missing_count, estimated_count를 함께 반환한다.
미수집 도구가 있으면 “수집된 토큰”으로 표기한다. 전부 null이면 0 대신 미수집이다.
여러 AI의 겹치는 세션 시간을 합쳐 사용자의 작업 시간으로 표시하지 않는다.

## 완료와 비용
작업 상태는 recorded / verified / user_confirmed. verified는 성공 검증 evidence가 필요하다.
사용자 확인은 별도 기록으로 남기며 테스트 통과를 소급 생성하지 않는다.
비용은 actual_api_cost, estimated_api_equivalent, subscription_cost로 분리하고 currency·단가 기준일·출처를 저장한다.
단가나 모델이 불명확하면 추정액도 null이다. 통화가 다르면 환율 근거 없이 합산하지 않는다.
