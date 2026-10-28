# regcite

Retrieval over EU regulation on AI in medicine (AI Act, MDR, IVDR, GDPR, MDCG 2019-11) with answers that cite verifiable articles. This is an AI engineering portfolio project. The full roadmap is in the plan: `C:\Users\add-iv\.claude\plans\update-the-plan-virtual-deer.md` (milestones M0–M5).

## Commands

```powershell
pip install -e ".[dev]"      # install with dev extras
python -m pytest             # run tests
python -m ruff check .       # lint
python -m ruff format .      # format (CI runs a `lint` job: format --check then check, and a parallel `test` job: pytest)
regcite search "<query>" --corpus data/raw
```

Windows, PowerShell. Python >= 3.11. Source layout is `src/regcite/`, tests in `tests/`.

## Architecture

- `chunking.py`: `chunk_document(doc_id, text, max_chars=1200)` splits Markdown by heading into `Chunk`s; the heading path becomes the citation.
- `search.py`: `BM25Index` and `tokenize`. This is the lexical baseline; keep its behaviour unchanged when adding hybrid ranking.
- `cli.py`: `regcite search`.
- `ingest/`: `load_corpus` reads a folder of .md/.txt files into chunks. Fetching and conversion go here in M1.
- `config.py`: `get_model()` returns the Claude model ID (env `REGCITE_MODEL`, default in `DEFAULT_MODEL`).

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
