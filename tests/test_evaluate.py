import pytest

from regcite.chunking import Chunk
from regcite.evaluate import evaluate_retrieval, summarise
from regcite.gold import Expected, Question, article_key


class StubRanker:
    def __init__(self, chunks):
        self.chunks = chunks

    def search(self, query, top_k=5):
        return [(c, 1.0) for c in self.chunks[:top_k]]


def art(doc, number, text="t", line=1):
    return Chunk(doc, f"Chapter I > Article {number} Title", text, line)


def question(*expected, category="direct", qid="q"):
    return Question(qid, category, "q?", tuple(Expected(d, r) for d, r in expected))


def test_article_key_uses_the_article_or_annex_in_the_citation():
    assert article_key(art("mdr", 4)) == ("mdr", "Article 4")
    assert article_key(Chunk("mdr", "Annex VIII RULES", "t", 1)) == ("mdr", "Annex VIII")
    assert article_key(Chunk("mdr", "Preamble", "t", 1)) == ("mdr", "Preamble")


def test_chunks_of_one_article_count_once():
    ranker = StubRanker([art("mdr", 4, line=1), art("mdr", 4, line=2), art("mdr", 7)])

    (result,) = evaluate_retrieval(ranker, [question(("mdr", "Article 7"))], k=2)

    assert result.ranks == (2,)
    assert result.recall == 1.0
    assert result.reciprocal_rank == 0.5


def test_missing_article_scores_zero():
    (result,) = evaluate_retrieval(StubRanker([art("mdr", 4)]), [question(("mdr", "Article 9"))])

    assert result.ranks == (None,)
    assert result.recall == 0.0
    assert result.reciprocal_rank == 0.0


def test_recall_counts_only_the_top_k_and_each_expected_article():
    ranker = StubRanker([art("ai_act", 4), art("gdpr", 9), art("ai_act", 26)])
    wanted = question(("ai_act", "Article 4"), ("gdpr", "Article 35"), ("ai_act", "Article 26"))

    (result,) = evaluate_retrieval(ranker, [wanted], k=2)

    assert result.ranks == (1, None, 3)
    assert result.recall == pytest.approx(1 / 3)


def test_out_of_scope_questions_are_skipped_and_summary_groups_by_category():
    ranker = StubRanker([art("mdr", 4)])
    questions = [
        question(("mdr", "Article 4"), qid="a"),
        question(("mdr", "Article 5"), category="paraphrase", qid="b"),
        question(category="out_of_scope", qid="c"),
    ]

    summary = summarise(evaluate_retrieval(ranker, questions))

    assert summary["all"] == {"n": 2, "recall": 0.5, "mrr": 0.5}
    assert summary["direct"]["recall"] == 1.0
    assert summary["paraphrase"]["recall"] == 0.0
    assert "out_of_scope" not in summary
