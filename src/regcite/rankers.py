"""Build a ranker by name so the CLI and evaluation can compare them."""

from __future__ import annotations

from pathlib import Path

from regcite.chunking import Chunk
from regcite.config import get_embedding_model
from regcite.search import BM25Index, HybridIndex, Ranker

RANKERS = ("bm25", "dense", "hybrid")


def build_ranker(
    name: str, chunks: list[Chunk], cache_dir: Path | None = Path("data/index")
) -> Ranker:
    return build_rankers([name], chunks, cache_dir)[name]


def build_rankers(
    names: list[str], chunks: list[Chunk], cache_dir: Path | None = Path("data/index")
) -> dict[str, Ranker]:
    """Build several rankers that share one BM25 index and one embedding model."""
    unknown = [n for n in names if n not in RANKERS]
    if unknown:
        raise ValueError(f"unknown ranker {unknown[0]!r}; choose from {', '.join(RANKERS)}")

    bm25 = BM25Index(chunks)
    rankers: dict[str, Ranker] = {}
    if "bm25" in names:
        rankers["bm25"] = bm25
    if "dense" in names or "hybrid" in names:
        # Imported here so BM25 search works without numpy or a model download.
        from regcite.dense import DenseIndex, SentenceTransformerEmbedder

        embedder = SentenceTransformerEmbedder(get_embedding_model())
        dense = DenseIndex.build(chunks, embedder, cache_dir)
        if "dense" in names:
            rankers["dense"] = dense
        if "hybrid" in names:
            rankers["hybrid"] = HybridIndex([bm25, dense])
    return {name: rankers[name] for name in names}
