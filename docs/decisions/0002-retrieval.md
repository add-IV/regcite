# 0002: Retrieval with BM25, local embeddings and rank fusion

Status: accepted for M2; numbers are preliminary (see Caveats)

## Decision

- Keep `BM25Index` unchanged as the lexical baseline.
- Add dense retrieval with a local `BAAI/bge-base-en-v1.5` model (`dense.py`). English-only,
  because the corpus and the gold questions are English; a multilingual model is a possible
  later experiment. Queries get the bge retrieval instruction, chunks are embedded as
  `citation + text` so the article title is part of the vector.
- Vectors are cached in `data/index/` under a key made from the model name and the exact chunk
  texts, so changed chunks never reuse stale vectors.
- Add `HybridIndex`: reciprocal rank fusion (`k=60`) of the top 50 from each ranker.
- Every ranker has the same `search(query, top_k)` interface, selected by name
  (`regcite search --ranker`, `regcite eval --rankers`).
- Retrieval is scored per article: several chunks of one article count once (ADR 0001).

## First comparison

18 answerable gold questions, recall@5 and MRR, per article:

| Ranker | Recall@5 | MRR |
|--------|----------|-----|
| BM25 | 0.67 | 0.48 |
| Dense | 0.89 | 0.70 |
| Hybrid (RRF) | 0.83 | 0.58 |

By category, recall@5: paraphrase 0.64 (BM25), 0.91 (dense), 0.82 (hybrid); direct 0.80, 1.00,
1.00; cross-regulation (2 questions) 0.50 for all three.

## Caveats

- n=18, so one question moves recall by about 0.06. There are no confidence intervals yet.
  Only the gap between BM25 and dense looks larger than that; dense versus hybrid is within
  noise.
- The questions are an AI-drafted set that the author has not reviewed yet (`eval/README.md`).
- Hybrid scoring below dense is plausible with plain RRF, since BM25's weaker ranking dilutes
  the fused list. RRF settings were not tuned: tuning on 18 questions would overfit. Revisit
  on a held-out part of the 60-100 question set in M4.
- Embedding the corpus took about 3 minutes on a CPU; later runs load the cached vectors in
  seconds.

## Consequences

- Dense search needs numpy and sentence-transformers (the `dense` extra, with CPU-only torch).
  BM25 search and the tests need neither a model download nor torch.
- The embedding model adds about 440 MB to deployment; its memory and cold-start cost is to
  be measured when the retrieval UI runs (M2b).
- Not yet tried: a cross-encoder reranker (M2c) and a multilingual model.
