FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/index.html frontend/tsconfig.json frontend/vite.config.ts ./
COPY frontend/src/ ./src/
RUN npm run build

FROM python:3.12-slim-bookworm AS backend
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.9.10 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/monitor/ backend/monitor/
COPY --from=frontend /build/dist/ frontend/dist/
RUN useradd --uid 10001 --create-home monitor && mkdir -p /app/.local && chown monitor:monitor /app/.local
USER monitor
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 MONITOR_DEPLOYMENT=demo
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/v1/health',timeout=3)"
CMD ["uvicorn", "monitor.app:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8765"]
