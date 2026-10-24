FROM python:3.12-slim@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.13.5@sha256:32a7bb39b496babbd997b0a39a4d66c126bdaf5661b302bf6f06abda8deca6ff /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock ./

RUN uv sync --locked --no-dev

COPY app ./app
COPY migrations ./migrations
COPY scripts ./scripts
COPY demo ./demo
COPY alembic.ini ./

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/uploads \
    && chown appuser:appuser /app/uploads

USER appuser

EXPOSE 8000

CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--limit-concurrency", "8", "--backlog", "128", "--timeout-keep-alive", "5", "--timeout-graceful-shutdown", "30"]
