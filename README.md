# regcite

Retrieval over EU regulation on AI in medicine, with answers that cite the
exact article they came from and are checked against the retrieved text.

Target corpus: the EU AI Act (2024/1689), MDR (2017/745), IVDR (2017/746),
the GDPR (2016/679) and MDCG 2019-11 (software qualification). regcite is a research and engineering
project. It is not legal or clinical advice.

## Status

Early work. What exists today: Markdown or plain-text files are split by
article and heading, and searched with BM25 through a CLI. There is no real
corpus, no LLM step, no evaluation and no interface yet. No API keys or model
downloads are needed.

## Quick start

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"

# Put .md or .txt copies of the regulations under data/raw/
regcite search "human oversight high-risk" --corpus data/raw
pytest
```

## Layout

```
src/regcite/chunking.py   Split documents into citable chunks
src/regcite/search.py     BM25 keyword index
src/regcite/cli.py        `regcite search` command
src/regcite/ingest/       Load regulation files into chunks
src/regcite/config.py     Settings, including the Claude model ID
tests/                    Chunking, search and ingestion tests
.github/workflows/ci.yml  lint and test jobs on every push
data/raw/                 Source regulation texts (add your own)
CLAUDE.md                 Project guidance for Claude Code
```

## Roadmap

| Milestone | Goal |
|-----------|------|
| M0 | Foundations: ruff, CI, model config, ingestion module |
| M1 | Corpus: fetch and convert the five sources, manifest with hashes, `regcite ingest`, first gold questions |
| M2 | Retrieval: local embeddings, hybrid ranking with reciprocal rank fusion, optional reranker |
| M3 | Grounded answers from Claude; every cited ID and quote is verified, otherwise retry once, then abstain |
| M4 | Evaluation: 60-100 gold questions, recall@5 and MRR with confidence intervals, no-retrieval and long-context baselines, faithfulness review |
| M5 | FastAPI service, web UI, Docker, hosted demo with rate and spend limits, write-up |

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

Keep a note of the version and date of each text in `data/raw/`. Regulations
are amended, and a citation is only useful if it points to a known version.
