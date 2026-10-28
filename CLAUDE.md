# regcite

Retrieval over EU regulation on AI in medicine (AI Act, MDR, IVDR, GDPR) with answers that cite verifiable articles. This is an AI engineering portfolio project. The full roadmap is in the plan: `C:\Users\add-iv\.claude\plans\update-the-plan-virtual-deer.md` (milestones M0–M5, with M2b retrieval UI before M3 answer generation).

## Commands

```powershell
pip install -e ".[dev]"      # install with dev extras
python -m pytest             # run tests
python -m ruff check .       # lint
python -m ruff format .      # format (CI runs a `lint` job: format --check then check, and a parallel `test` job: pytest)
regcite ingest               # download and convert the corpus into data/raw (git-ignored)
regcite search "<query>" [--ranker bm25|dense|hybrid]
regcite eval                 # recall@5 and MRR per ranker on eval/gold.jsonl
regcite serve                # HTTP API on 127.0.0.1:8000 (pip install -e ".[api,dense]")
pip install -e ".[dev,dense]"  # embedding search; first dense run downloads a 440 MB model and embeds the corpus (~3 min, cached in data/index/)
```

Windows, PowerShell. Python >= 3.11. Source layout is `src/regcite/`, tests in `tests/`.

## Architecture

- `chunking.py`: `chunk_document(doc_id, text, max_chars=1200)` splits Markdown by heading into `Chunk`s; the heading path becomes the citation.
- `search.py`: `BM25Index` and `tokenize` (the lexical baseline; keep its behaviour unchanged), plus `reciprocal_rank_fusion` and `HybridIndex`. Every ranker exposes `search(query, top_k) -> [(Chunk, score)]`.
- `dense.py`: `SentenceTransformerEmbedder` (bge-base-en-v1.5, local) and `DenseIndex`, whose vectors are cached in `data/index/` keyed by model and chunk texts. Imports numpy, so import it lazily where BM25-only use must work.
- `rankers.py`: `build_ranker(name, chunks, cache_dir)`.
- `gold.py`, `evaluate.py`: gold questions and per-article recall@k / MRR; `matches` and `article_key` decide which article a chunk belongs to.
- `api.py`: `create_app(rankers, chunk_count, sources, limiter)` (FastAPI; `POST /search`, `GET /health`) and `app_from_env()` which loads corpus and rankers once and warms them up. The query goes in the POST body, never the URL, and `regcite serve` runs uvicorn with the access log off: do not add logging of query text or IPs. `RateLimiter` keeps client IPs in memory only.
- `cli.py`: `regcite ingest | search | eval | serve`.
- `ingest/`: `sources.py` pins the four regulations (consolidated CELEX), `fetch.py` downloads XHTML from the Publications Office resolver (eur-lex.europa.eu blocks scripts), `convert.py` turns it into Markdown (chapter/annex `#`, section `##`, article `###`), `pipeline.py` writes `data/raw/*.md` and `data/manifest.json`, `corpus.py` has `load_corpus`.
- `config.py`: `get_model()` returns the Claude model ID (env `REGCITE_MODEL`); `get_embedding_model()` the embedding model (env `REGCITE_EMBEDDING_MODEL`).

## Conventions

- Match the surrounding style: `from __future__ import annotations`, type hints, short docstrings, no extra comments.
- Every new behaviour gets a test in `tests/`. Citation verification and ingestion parsing need the most careful tests.
- Runtime dependencies are minimal by design. Add one only when the milestone needs it, pin its version, and prefer CPU-only builds.
- The model ID comes from config, never hard-coded in call sites. Record the model in every eval result.

## Rules for this project

- Citations must be verifiable: never present an answer whose cited chunk IDs or quotes were not checked against retrieved text.
- Never commit API keys, `.env` files, or regulation text whose reuse terms have not been checked. `data/raw/` stays out of git unless confirmed.
- Every corpus file needs an entry (source URL, version, retrieval date, SHA-256) in `data/manifest.json`.
- The project is not legal or clinical advice; keep that disclaimer in the README and the UI.
- Report eval numbers with confidence intervals and do not claim differences that fall within noise.
- LLM calls are cached on disk; reruns of evaluation must not cost money.
- Privacy: do not log user query text by default, keep IP addresses in memory only, and use synthetic data only in gold questions and tests (no real patient or company data).
