# Gold set

`gold.jsonl` has one question per line: `id`, `category`, `question` and `expected`
(a list of `{doc_id, ref}`; empty for out-of-scope questions). A chunk matches when it is
in the same document and its citation contains the reference, for example `Article 14`
(see `src/regcite/gold.py`).

Categories: `direct` (close to the article's wording), `paraphrase` (avoids it),
`cross_regulation` (needs two documents) and `out_of_scope` (the system should abstain).

Status: the first 20 questions are a draft written with an AI assistant against the
ingested text. They are all synthetic, with no real patient or company data. The author
has to review every question and expected reference before any result is reported, and
the set will grow to 60-100 questions in M4. Expected references are checked against the
corpus by `tests/test_gold.py` when `data/raw/` exists.
