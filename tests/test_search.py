from regcite.chunking import Chunk
from regcite.search import BM25Index, tokenize


def make_chunks():
    return [
        Chunk("ai_act", "Article 6", "High-risk classification applies to medical device AI.", 1),
        Chunk(
            "ai_act", "Article 14", "Human oversight shall be ensured for high-risk systems.", 10
        ),
        Chunk("fda", "Clinical decision support", "Software that analyses images is a device.", 1),
    ]


def test_tokenize_lowercases_and_splits_on_punctuation():
    assert tokenize("510(k) High-Risk") == ["510", "k", "high", "risk"]


def test_best_match_is_ranked_first():
    index = BM25Index(make_chunks())
    results = index.search("human oversight", top_k=3)

    assert results[0][0].citation == "Article 14"


def test_heading_text_is_searchable():
    chunks = [
        Chunk(
            "ai_act", "Article 14 Human oversight", "Systems shall be designed to be overseen.", 1
        ),
        Chunk("ai_act", "Article 6 Classification", "Devices requiring conformity assessment.", 5),
    ]
    results = BM25Index(chunks).search("human oversight")

    assert results[0][0].citation == "Article 14 Human oversight"


def test_unknown_terms_return_nothing():
    index = BM25Index(make_chunks())
    assert index.search("blockchain pancakes") == []


def test_empty_corpus_does_not_divide_by_zero():
    index = BM25Index([])
    assert index.search("anything") == []
