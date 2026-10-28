"""Retrieval metrics on the gold set, scored per article.

Several chunks of one article count once, so splitting long articles into
chunks does not change recall@k or MRR.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from regcite.gold import Question, article_key
from regcite.search import Ranker


@dataclass(frozen=True)
class QuestionResult:
    id: str
    category: str
    recall: float  # share of expected articles found in the top k
    reciprocal_rank: float  # 1 / rank of the first expected article, 0 if none found
    ranks: tuple[int | None, ...]  # article rank of each expected reference


def evaluate_retrieval(
    ranker: Ranker, questions: list[Question], k: int = 5, pool: int = 50
) -> list[QuestionResult]:
    """Score every answerable question; out-of-scope questions have no expected article."""
    results = []
    for q in questions:
        if not q.expected:
            continue
        articles: list[tuple[str, str]] = []
        for chunk, _ in ranker.search(q.question, top_k=pool):
            key = article_key(chunk)
            if key not in articles:
                articles.append(key)
        ranks = tuple(
            articles.index((e.doc_id, e.ref)) + 1 if (e.doc_id, e.ref) in articles else None
            for e in q.expected
        )
        found = [r for r in ranks if r is not None]
        results.append(
            QuestionResult(
                id=q.id,
                category=q.category,
                recall=sum(1 for r in found if r <= k) / len(ranks),
                reciprocal_rank=1 / min(found) if found else 0.0,
                ranks=ranks,
            )
        )
    return results


def summarise(results: list[QuestionResult]) -> dict[str, dict[str, float]]:
    """Mean recall@k and MRR overall and per category."""
    groups: dict[str, list[QuestionResult]] = defaultdict(list)
    for r in results:
        groups["all"].append(r)
        groups[r.category].append(r)
    return {
        name: {
            "n": len(rs),
            "recall": sum(r.recall for r in rs) / len(rs),
            "mrr": sum(r.reciprocal_rank for r in rs) / len(rs),
        }
        for name, rs in groups.items()
    }
