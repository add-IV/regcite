from pathlib import Path

import pytest

from regcite.chunking import Chunk
from regcite.gold import CATEGORIES, Expected, load_gold, matches

GOLD = Path(__file__).parent.parent / "eval" / "gold.jsonl"
CORPUS = Path(__file__).parent.parent / "data" / "raw"


def test_gold_file_is_well_formed():
    questions = load_gold(GOLD)

    assert len(questions) >= 20
    assert len({q.id for q in questions}) == len(questions)
    assert {q.category for q in questions} <= CATEGORIES
    for q in questions:
        assert q.question.endswith("?")
        assert (q.category == "out_of_scope") == (not q.expected)


def test_match_requires_same_document_and_exact_article_number():
    chunk = Chunk("ai_act", "Chapter III > Article 14 Human oversight", "text", 1)

    assert matches(chunk, Expected("ai_act", "Article 14"))
    assert not matches(chunk, Expected("ai_act", "Article 1"))
    assert not matches(chunk, Expected("gdpr", "Article 14"))


def test_match_accepts_article_at_end_of_citation_and_annexes():
    assert matches(
        Chunk("mdr", "Annex VIII CLASSIFICATION RULES", "t", 1), Expected("mdr", "Annex VIII")
    )
    assert matches(Chunk("gdpr", "Chapter II > Article 9", "t", 1), Expected("gdpr", "Article 9"))
    assert not matches(
        Chunk("mdr", "Annex VIII CLASSIFICATION RULES", "t", 1), Expected("mdr", "Annex VII")
    )


@pytest.mark.skipif(not CORPUS.joinpath("ai_act.md").exists(), reason="run `regcite ingest` first")
def test_every_expected_reference_exists_in_the_corpus():
    from regcite.ingest import load_corpus

    chunks = load_corpus(CORPUS)
    for q in load_gold(GOLD):
        for expected in q.expected:
            assert any(matches(c, expected) for c in chunks), (q.id, expected)
