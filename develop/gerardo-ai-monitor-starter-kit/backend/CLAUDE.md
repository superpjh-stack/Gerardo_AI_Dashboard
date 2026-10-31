# 백엔드 참고 지침

먼저 루트 AGENTS.md와 contracts/events.md, storage.md, api.md를 읽는다.
실제 서버 코드는 monitor/, 검증은 tests/에 있다. FastAPI와 SQLite를 사용한다.
어댑터는 원본 읽기 → 정규화 → 검증 → 저장의 경계를 지킨다.
계정 인증정보를 파싱하지 않는다. 수집 체크포인트는 데이터와 원자적으로 갱신한다.
집계는 UI가 아니라 서비스 계층에서 수행하고 nullable·coverage를 API로 전달한다.
테스트 우선순위: 멱등성, 누적 counter, 캐시, 시간대, 파일 회전, 장애 복구.
