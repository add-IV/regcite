import numpy as np
import pytest

from regcite.chunking import Chunk
from regcite.dense import DenseIndex
from regcite.search import BM25Index, HybridIndex, reciprocal_rank_fusion

SLOT_OF = {"oversight": 0, "human": 0, "fines": 1, "penalty": 1, "data": 2, "health": 2}


class FakeEmbedder:
    """Bag-of-concepts vectors where synonyms share a slot; counts document calls."""

    name = "fake/model"

    def __init__(self):
        self.document_calls = 0

    def _encode(self, texts):
        vectors = np.zeros((len(texts), 3), dtype=np.float32)
        for row, text in enumerate(texts):
            for word in text.lower().split():
                if word in SLOT_OF:
                    vectors[row, SLOT_OF[word]] += 1
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / np.where(norms == 0, 1, norms)

    def embed_documents(self, texts):
        self.document_calls += 1
        return self._encode(texts)

    def embed_queries(self, texts):
        return self._encode(texts)


CHUNKS = [
    Chunk("ai_act", "Article 14 Human oversight", "human oversight of the system", 1),
    Chunk("ai_act", "Article 99 Penalties", "fines and penalty amounts", 10),
    Chunk("gdpr", "Article 9", "health data is special", 20),
]


def test_dense_search_ranks_by_similarity():
    index = DenseIndex.build(CHUNKS, FakeEmbedder())

    top, score = index.search("human oversight", top_k=1)[0]

    assert top.citation.startswith("Article 14")
    assert score > 0.5


def test_vectors_are_cached_for_the_same_chunks_and_model(tmp_path):
    first = FakeEmbedder()
    DenseIndex.build(CHUNKS, first, tmp_path)
    second = FakeEmbedder()
    index = DenseIndex.build(CHUNKS, second, tmp_path)

    assert first.document_calls == 1
    assert second.document_calls == 0
    assert index.search("fines", top_k=1)[0][0].citation.startswith("Article 99")


def test_cache_is_not_reused_when_chunks_change(tmp_path):
    DenseIndex.build(CHUNKS, FakeEmbedder(), tmp_path)
    changed = [*CHUNKS[:2], Chunk("gdpr", "Article 9", "other text", 20)]
    embedder = FakeEmbedder()

    DenseIndex.build(changed, embedder, tmp_path)

    assert embedder.document_calls == 1


def test_vectors_must_match_chunks():
    with pytest.raises(ValueError):
        DenseIndex(CHUNKS, np.zeros((1, 3), dtype=np.float32), FakeEmbedder())


def test_rrf_rewards_agreement_between_lists():
    a, b, c = CHUNKS
    fused = reciprocal_rank_fusion([[a, b, c], [c, a, b]], k=60, top_k=3)

    assert [chunk for chunk, _ in fused][0] == a
    assert fused[0][1] == pytest.approx(1 / 61 + 1 / 62)


def test_rrf_includes_chunks_found_by_only_one_list():
    a, b, c = CHUNKS
    fused = reciprocal_rank_fusion([[a], [b]], k=60, top_k=5)

    assert {chunk for chunk, _ in fused} == {a, b}


def test_hybrid_finds_what_only_the_dense_side_can():
    chunks = [
        Chunk("ai_act", "Article 99", "penalty amounts", 1),
        Chunk("ai_act", "Article 14", "human oversight", 5),
    ]
    bm25 = BM25Index(chunks)
    hybrid = HybridIndex([bm25, DenseIndex.build(chunks, FakeEmbedder())])

    assert bm25.search("fines") == []  # no shared word
    assert hybrid.search("fines", top_k=1)[0][0].citation == "Article 99"
