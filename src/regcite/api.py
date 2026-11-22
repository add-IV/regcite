"""HTTP API: ``POST /search`` returns the top chunks of a chosen ranker with their citations.

The app also serves the static page in ``web/`` and the gold questions as examples.

Query text is never logged. It travels in the request body, not the URL, so access logs and
proxies do not record it. Client IPs are used only for rate limiting and live in memory.
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from regcite.chunking import Chunk
from regcite.gold import article_key, load_gold
from regcite.ingest import load_corpus
from regcite.rankers import RANKERS, build_rankers
from regcite.search import Ranker

MAX_QUERY_CHARS = 500
MAX_TRACKED_CLIENTS = 10_000


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=MAX_QUERY_CHARS)
    ranker: Literal["bm25", "dense", "hybrid"] = "hybrid"
    k: int = Field(default=5, ge=1, le=20)


class Source(BaseModel):
    title: str | None = None
    version: str | None = None
    retrieved: str | None = None


class Hit(BaseModel):
    rank: int
    score: float
    doc_id: str
    article: str
    citation: str
    line: int
    text: str
    source: Source


class SearchResponse(BaseModel):
    ranker: str
    hits: list[Hit]


class Example(BaseModel):
    id: str
    category: str
    question: str


class RateLimiter:
    """At most ``limit`` calls per client within ``window`` seconds, kept in memory only.

    The app calls ``forget_idle`` once per window, so an IP is held for at most two windows.
    """

    def __init__(self, limit: int = 30, window: float = 60.0, clock=time.monotonic):
        self.limit = limit
        self.window = window
        self.clock = clock
        self._calls: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def retry_after(self, client: str) -> float | None:
        """Seconds to wait if the client is over the limit, else None (and the call is counted)."""
        now = self.clock()
        with self._lock:
            if len(self._calls) >= MAX_TRACKED_CLIENTS and client not in self._calls:
                self._forget_idle(now)
            calls = self._calls.setdefault(client, deque())
            while calls and now - calls[0] >= self.window:
                calls.popleft()
            if len(calls) >= self.limit:
                return self.window - (now - calls[0])
            calls.append(now)
            return None

    def forget_idle(self) -> None:
        """Drop clients with no call in the last window."""
        with self._lock:
            self._forget_idle(self.clock())

    def _forget_idle(self, now: float) -> None:
        idle = [
            c for c, calls in self._calls.items() if not calls or now - calls[-1] >= self.window
        ]
        for client in idle:
            del self._calls[client]


def create_app(
    rankers: dict[str, Ranker],
    chunk_count: int,
    sources: dict[str, dict] | None = None,
    limiter: RateLimiter | None = None,
    examples: list[Example] | None = None,
    static_dir: Path | None = None,
) -> FastAPI:
    limiter = limiter or RateLimiter()
    examples = examples or []

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async def prune() -> None:
            while True:
                await asyncio.sleep(limiter.window)
                limiter.forget_idle()

        task = asyncio.create_task(prune())
        yield
        task.cancel()

    app = FastAPI(title="regcite", docs_url=None, redoc_url=None, lifespan=lifespan)
    sources = sources or {}
    search_lock = threading.Lock()  # embedding models are not safe to call concurrently

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "rankers": sorted(rankers), "chunks": chunk_count}

    @app.get("/examples", response_model=list[Example])
    def list_examples() -> list[Example]:
        return examples

    @app.post("/search", response_model=SearchResponse)
    def search(body: SearchRequest, request: Request) -> SearchResponse:
        client = request.client.host if request.client else "unknown"
        wait = limiter.retry_after(client)
        if wait is not None:
            raise HTTPException(
                status_code=429,
                detail="Too many requests",
                headers={"Retry-After": str(int(wait) + 1)},
            )
        ranker = rankers.get(body.ranker)
        if ranker is None:
            raise HTTPException(status_code=422, detail=f"ranker {body.ranker!r} is not available")
        with search_lock:
            results = ranker.search(body.query, top_k=body.k)
        return SearchResponse(
            ranker=body.ranker,
            hits=[
                _hit(rank, chunk, score, sources) for rank, (chunk, score) in enumerate(results, 1)
            ],
        )

    if static_dir is not None:  # mounted last so the API routes take precedence
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="web")
    return app


def _hit(rank: int, chunk: Chunk, score: float, sources: dict[str, dict]) -> Hit:
    info = sources.get(chunk.doc_id, {})
    return Hit(
        rank=rank,
        score=score,
        doc_id=chunk.doc_id,
        article=article_key(chunk)[1],
        citation=chunk.citation,
        line=chunk.line,
        text=chunk.text,
        source=Source(
            title=info.get("title"), version=info.get("version"), retrieved=info.get("retrieved")
        ),
    )


def app_from_env() -> FastAPI:
    """Load the corpus and rankers once.

    Paths come from REGCITE_CORPUS, _MANIFEST, _INDEX, _GOLD and _WEB; a missing gold file or
    web folder is skipped.
    """
    corpus = Path(os.environ.get("REGCITE_CORPUS", "data/raw"))
    manifest = Path(os.environ.get("REGCITE_MANIFEST", "data/manifest.json"))
    index = Path(os.environ.get("REGCITE_INDEX", "data/index"))
    gold = Path(os.environ.get("REGCITE_GOLD", "eval/gold.jsonl"))
    web = Path(os.environ.get("REGCITE_WEB", "web"))

    chunks = load_corpus(corpus)
    if not chunks:
        raise RuntimeError(f"No corpus found under {corpus}; run `regcite ingest` first")

    try:
        rankers = build_rankers(list(RANKERS), chunks, index)
    except ImportError:  # dense extra not installed: serve BM25 only
        rankers = build_rankers(["bm25"], chunks, index)
    for ranker in rankers.values():  # load the embedding model now, not on the first request
        ranker.search("warm up", top_k=1)

    sources = {}
    if manifest.is_file():
        documents = json.loads(manifest.read_text(encoding="utf-8")).get("documents", [])
        sources = {d["doc_id"]: d for d in documents}
    examples = []
    if gold.is_file():
        examples = [
            Example(id=q.id, category=q.category, question=q.question) for q in load_gold(gold)
        ]
    return create_app(
        rankers,
        len(chunks),
        sources,
        examples=examples,
        static_dir=web if web.is_dir() else None,
    )
