# regcite

Retrieval over EU regulation on AI in medicine, with answers that cite the
exact article they came from and are checked against the retrieved text.

Target corpus: the EU AI Act (2024/1689), MDR (2017/745), IVDR (2017/746)
and the GDPR (2016/679). regcite is a research and engineering project. It is
not legal or clinical advice.

## Status

Early work. What exists today: `regcite ingest` downloads the four
regulations (consolidated versions, pinned and recorded in
`data/manifest.json`), converts them to Markdown, and search over them
returns article-level citations with BM25, local embeddings, or a hybrid of
both. `regcite eval` compares the three on a small draft question set. There
is no LLM step and no interface yet, and no API key is needed. Dense search
downloads a 440 MB embedding model the first time it runs.

Preliminary retrieval results (18 questions, so differences between dense and
hybrid are within noise) are in
[docs/decisions/0002-retrieval.md](docs/decisions/0002-retrieval.md).

## Quick start

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"        # add ",dense" for embedding search

regcite ingest                 # downloads about 4 MB into data/raw/ (not tracked by git)
regcite search "human oversight high-risk"                  # BM25
regcite search "who may refuse an automated decision" --ranker hybrid
regcite eval                   # recall@5 and MRR for bm25, dense, hybrid
pytest
```

The first dense or hybrid run embeds the corpus (about 3 minutes on a CPU) and
caches the vectors in `data/index/`.

## API

```powershell
pip install -e ".[api,dense]"
regcite serve                  # http://127.0.0.1:8000, loads the corpus and models at startup

curl -X POST http://127.0.0.1:8000/search -H "Content-Type: application/json" `
  -d '{"query": "human oversight of high-risk AI", "ranker": "hybrid", "k": 5}'
```

`POST /search` returns the top chunks with rank, score, document, article,
citation path, text, and the source version and retrieval date from the
manifest. `GET /health` lists the available rankers (BM25 only if the `dense`
extra is missing). Queries are limited to 500 characters and 30 requests per
minute per client. The query goes in the request body, not the URL, and the
server keeps no access log, so query text is not recorded.

## Layout

```
src/regcite/chunking.py   Split documents into citable chunks
src/regcite/search.py     BM25 index, rank fusion, hybrid index
src/regcite/dense.py      Local embeddings and cached vector index
src/regcite/rankers.py    Build a ranker by name (bm25, dense, hybrid)
src/regcite/evaluate.py   Retrieval metrics, scored per article
src/regcite/api.py        FastAPI service: POST /search, GET /health, rate limit
src/regcite/cli.py        `regcite ingest | search | eval | serve` commands
src/regcite/ingest/       Download, convert to Markdown, load into chunks
data/manifest.json        Source, version, date and SHA-256 of each text
src/regcite/config.py     Settings, including the Claude model ID
src/regcite/gold.py       Load gold questions, match chunks to expected articles
eval/gold.jsonl           Gold questions (draft, see eval/README.md)
docs/decisions/           Architecture decision records
tests/                    Chunking, search, dense, evaluation and ingestion tests
.github/workflows/ci.yml  lint and test jobs on every push
data/raw/                 Source regulation texts (add your own)
CLAUDE.md                 Project guidance for Claude Code
```

## Roadmap

| Milestone | Goal |
|-----------|------|
| M0 | Foundations: ruff, CI, model config, ingestion module |
| M1 | Corpus: fetch and convert the four regulations, manifest with hashes, `regcite ingest`, first gold questions |
| M2 | Retrieval: local embeddings and hybrid ranking with reciprocal rank fusion (done); reranker ablation (open) |
| M2b | Retrieval-only web UI comparing the rankers side by side, to measure deployment limits early |
| M3 | Grounded answers from Claude; every cited ID and quote is verified, otherwise retry once, then abstain |
| M4 | Evaluation: 60-100 gold questions, recall@5 and MRR with confidence intervals, no-retrieval and long-context baselines, faithfulness review |
| M5 | Docker, hosted demo, CI evaluation subset, write-up |

## Evaluation (planned)

Results will be reported as a table with 95% bootstrap confidence intervals,
comparing BM25, hybrid and hybrid with reranking, and answering with retrieval
against Claude alone and against whole documents in the prompt. The gold set
will include paraphrased, cross-article and out-of-scope questions. Cost per
query and total evaluation cost will be listed. This section is filled in once
`regcite eval` exists.

## Limitations

- Not legal or clinical advice.
- Citations are only as good as the corpus snapshot. Each text is recorded
  with its source, version and retrieval date in `data/manifest.json`.
- Cross-references between articles may not be followed by retrieval.

## Privacy (planned for the hosted demo)

- Question text is not logged by default.
- IP addresses are used only for rate limiting and are kept in memory, not on disk.
- Questions are sent to the Anthropic API to generate answers. Do not enter
  personal or patient data.
- The hosting region will be stated here once the demo is deployed.
- Evaluation questions are synthetic and contain no real personal data.

## Sources

Texts come from the EU Publications Office as consolidated XHTML (the
`eur-lex.europa.eu` site blocks scripted requests). Versions are pinned in
`src/regcite/ingest/sources.py`:

| Regulation | Consolidated version |
|------------|----------------------|
| AI Act (2024/1689) | 2026-07-27 |
| MDR (2017/745) | 2026-07-19 |
| IVDR (2017/746) | 2025-01-10 |
| GDPR (2016/679) | 2016-05-04 |

The downloaded texts are not committed. Consolidated texts have no recitals,
and tables are flattened to one paragraph per cell. Regulations are amended,
and a citation is only useful if it points to a known version, so
`data/manifest.json` records the SHA-256 of each source file.
