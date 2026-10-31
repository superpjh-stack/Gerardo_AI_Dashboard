# Gerardo_AI_Dashboard

**제라도의 AI 활동 모니터링** — Claude, Codex, Antigravity의 사용량과 작업 기록을 모으는 개인용 로컬 대시보드입니다.

React · TypeScript · FastAPI · SQLite 기반입니다. 현재 Claude와 Codex의 로컬 JSONL 기록을 지원하며, Antigravity는 연결 경로 확인이 필요합니다.

## 시작하기

앱과 개발 문서는 [`develop/gerardo-ai-monitor-starter-kit`](develop/gerardo-ai-monitor-starter-kit/README.md)에 있습니다.

```bash
cd develop/gerardo-ai-monitor-starter-kit
uv sync
npm --prefix frontend ci
uv run python scripts/dev.py
```

화면: http://127.0.0.1:5188/ · API: http://127.0.0.1:8765/docs

macOS에서는 의존성 설치 후 앱 폴더의 `start.command`를 더블클릭할 수도 있습니다.
Node.js 22.12+ 또는 지원되는 이후 버전과 uv가 필요합니다. Python은 uv가 프로젝트 설정에 맞춰 준비합니다.

## 포함 기능

- 기간·프로젝트·AI별 토큰 집계와 차트
- 프로젝트별 활동 타임라인과 세션 근거
- 작업 메모와 사용자 검토 완료 표시
- 실제 기록과 분리된 합성 예시 모드
- 수집 범위·미수집·부분 수집 상태 표시

로컬 DB, 개인 로그, 인증정보, 의존성과 빌드 결과물은 저장소에 포함하지 않습니다.
최초 수집은 도구별 최근 수정 로그 최대 100개이며 변경할 수 있습니다. 사용량은 청구액이나 잔여 한도를 의미하지 않습니다.

## 개발 및 검증

```bash
cd develop/gerardo-ai-monitor-starter-kit
uv run pytest -q
npm --prefix frontend run build
```

[바이브코딩 가이드](develop/제라도_AI_활동_모니터링_바이브코딩_가이드.md) · [구현 계획](develop/gerardo-ai-monitor-starter-kit/docs/plans/2026-10-31-mvp.md) · [진행 기록과 한계](develop/gerardo-ai-monitor-starter-kit/progress.md)
