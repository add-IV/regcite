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
    if name == "bm25":
        return BM25Index(chunks)
    if name not in RANKERS:
        raise ValueError(f"unknown ranker {name!r}; choose from {', '.join(RANKERS)}")

    # Imported here so BM25 search works without numpy or a model download.
    from regcite.dense import DenseIndex, SentenceTransformerEmbedder

    dense = DenseIndex.build(chunks, SentenceTransformerEmbedder(get_embedding_model()), cache_dir)
    if name == "dense":
        return dense
    return HybridIndex([BM25Index(chunks), dense])
