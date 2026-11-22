import logging

import pytest
from fastapi.testclient import TestClient

from regcite.api import MAX_QUERY_CHARS, Example, RateLimiter, create_app
from regcite.chunking import Chunk
from regcite.search import BM25Index

CHUNKS = [
    Chunk("ai_act", "Chapter III > Article 14 Human oversight", "Human oversight of systems.", 7),
    Chunk("gdpr", "Chapter II > Article 9 Special categories", "Health data is special.", 3),
]
SOURCES = {
    "ai_act": {"title": "AI Act", "version": "consolidated 2026-07-27", "retrieved": "2026-10-28"}
}


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def make_client(limiter=None, rankers=None, **kwargs):
    rankers = rankers if rankers is not None else {"bm25": BM25Index(CHUNKS)}
    app = create_app(rankers, len(CHUNKS), SOURCES, limiter, **kwargs)
    return TestClient(app)


def test_health_lists_available_rankers():
    body = make_client().get("/health").json()

    assert body == {"status": "ok", "rankers": ["bm25"], "chunks": 2}


def test_search_returns_cited_hits_with_source_info():
    response = make_client().post("/search", json={"query": "human oversight", "ranker": "bm25"})

    assert response.status_code == 200
    body = response.json()
    assert body["ranker"] == "bm25"
    top = body["hits"][0]
    assert top["rank"] == 1
    assert top["doc_id"] == "ai_act"
    assert top["article"] == "Article 14"
    assert top["citation"] == "Chapter III > Article 14 Human oversight"
    assert top["line"] == 7
    assert top["source"] == {
        "title": "AI Act",
        "version": "consolidated 2026-07-27",
        "retrieved": "2026-10-28",
    }


def test_unknown_source_has_empty_source_fields():
    hits = make_client().post("/search", json={"query": "health data", "ranker": "bm25"}).json()

    assert hits["hits"][0]["doc_id"] == "gdpr"
    assert hits["hits"][0]["source"] == {"title": None, "version": None, "retrieved": None}


def test_unavailable_ranker_is_rejected():
    response = make_client().post("/search", json={"query": "oversight", "ranker": "dense"})

    assert response.status_code == 422


@pytest.mark.parametrize(
    "body",
    [
        {"query": ""},
        {"query": "x" * (MAX_QUERY_CHARS + 1)},
        {"query": "oversight", "k": 0},
        {"query": "oversight", "k": 21},
        {"query": "oversight", "ranker": "magic"},
    ],
)
def test_invalid_requests_are_rejected(body):
    assert make_client().post("/search", json=body).status_code == 422


def test_rate_limit_returns_429_with_retry_after_then_recovers():
    clock = Clock()
    client = make_client(RateLimiter(limit=2, window=60, clock=clock))
    request = {"query": "oversight", "ranker": "bm25"}

    assert client.post("/search", json=request).status_code == 200
    assert client.post("/search", json=request).status_code == 200
    blocked = client.post("/search", json=request)
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1

    clock.now = 61
    assert client.post("/search", json=request).status_code == 200


def test_rate_limiter_counts_clients_separately():
    limiter = RateLimiter(limit=1, window=60, clock=Clock())

    assert limiter.retry_after("a") is None
    assert limiter.retry_after("b") is None
    assert limiter.retry_after("a") is not None


def test_rate_limiter_forgets_idle_clients():
    clock = Clock()
    limiter = RateLimiter(limit=5, window=60, clock=clock)
    limiter.retry_after("a")
    clock.now = 30
    limiter.retry_after("b")

    clock.now = 70
    limiter.forget_idle()

    assert limiter.retry_after("a") is None
    assert list(limiter._calls) == ["b", "a"]
    assert len(limiter._calls["a"]) == 1


def test_app_starts_and_stops_with_pruning_task():
    with make_client() as client:
        assert client.get("/health").status_code == 200


def test_query_text_is_not_logged(caplog):
    secret = "patient-jane-doe-diabetes"
    with caplog.at_level(logging.DEBUG):
        make_client().post("/search", json={"query": secret, "ranker": "bm25"})

    assert secret not in caplog.text


def test_examples_lists_gold_questions():
    examples = [Example(id="g01", category="direct", question="What is human oversight?")]

    body = make_client(examples=examples).get("/examples").json()

    assert body == [{"id": "g01", "category": "direct", "question": "What is human oversight?"}]


def test_examples_is_empty_without_gold_file():
    assert make_client().get("/examples").json() == []


def test_static_page_is_served_next_to_the_api(tmp_path):
    (tmp_path / "index.html").write_text("<h1>regcite</h1>", encoding="utf-8")
    client = make_client(static_dir=tmp_path)

    assert client.get("/").text == "<h1>regcite</h1>"
    assert client.get("/health").json()["status"] == "ok"
    assert client.post("/search", json={"query": "oversight", "ranker": "bm25"}).status_code == 200


def test_no_static_page_without_web_folder():
    assert make_client().get("/").status_code == 404
