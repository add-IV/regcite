# Retrieval demo: CPU-only torch, BM25 + bge-base dense + hybrid, served by uvicorn.
# Corpus, vector cache and the embedding model live in the /app/data volume.

FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --extra api --extra dense --no-install-project
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --extra api --extra dense --no-editable

FROM python:3.12-slim
RUN useradd --create-home --uid 1000 regcite \
    && mkdir -p /app/data && chown regcite:regcite /app/data
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY web ./web
COPY eval/gold.jsonl ./eval/gold.jsonl
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/app/data/hf \
    HF_HUB_DISABLE_TELEMETRY=1 \
    XDG_CACHE_HOME=/tmp/cache
USER regcite
VOLUME /app/data
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10m \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"
# Caddy on the host proxies to 127.0.0.1:8000, so only it may set X-Forwarded-For.
CMD ["regcite", "serve", "--host", "127.0.0.1", "--port", "8000", "--forwarded-allow-ips", "127.0.0.1"]
