"""Embedding search: a local sentence-transformers model and a cached vector index."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Protocol

import numpy as np

from regcite.chunking import Chunk

# bge models embed queries with an instruction; documents are embedded as they are.
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


class Embedder(Protocol):
    name: str

    def embed_documents(self, texts: list[str]) -> np.ndarray: ...

    def embed_queries(self, texts: list[str]) -> np.ndarray: ...


class SentenceTransformerEmbedder:
    """Unit-length vectors from a local model; the model loads on first use."""

    def __init__(self, name: str, query_instruction: str = QUERY_INSTRUCTION):
        self.name = name
        self.query_instruction = query_instruction
        self._model = None

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return self._encode(texts)

    def embed_queries(self, texts: list[str]) -> np.ndarray:
        return self._encode([self.query_instruction + t for t in texts])

    def _encode(self, texts: list[str]) -> np.ndarray:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.name)
        vectors = self._model.encode(
            texts, normalize_embeddings=True, batch_size=32, show_progress_bar=len(texts) > 100
        )
        return np.asarray(vectors, dtype=np.float32)


class DenseIndex:
    def __init__(self, chunks: list[Chunk], vectors: np.ndarray, embedder: Embedder):
        if len(chunks) != len(vectors):
            raise ValueError("one vector per chunk is required")
        self.chunks = chunks
        self.vectors = vectors
        self.embedder = embedder

    @classmethod
    def build(
        cls, chunks: list[Chunk], embedder: Embedder, cache_dir: Path | None = None
    ) -> DenseIndex:
        """Embed the chunks, or load the vectors saved for exactly these chunks and model."""
        path = _cache_path(cache_dir, embedder.name, chunks) if cache_dir else None
        if path is not None and path.is_file():
            return cls(chunks, np.load(path), embedder)
        vectors = embedder.embed_documents([_embedding_text(c) for c in chunks])
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            np.save(path, vectors)
        return cls(chunks, vectors, embedder)

    def search(self, query: str, top_k: int = 5) -> list[tuple[Chunk, float]]:
        if not len(self.chunks):
            return []
        query_vector = self.embedder.embed_queries([query])[0]
        scores = self.vectors @ query_vector
        order = np.argsort(-scores, kind="stable")[:top_k]
        return [(self.chunks[i], float(scores[i])) for i in order]


def _embedding_text(chunk: Chunk) -> str:
    # The citation holds the article title, which the body text often lacks.
    return f"{chunk.citation}\n{chunk.text}"


def _cache_path(cache_dir: Path, model: str, chunks: list[Chunk]) -> Path:
    digest = hashlib.sha256()
    for chunk in chunks:
        digest.update(_embedding_text(chunk).encode("utf-8"))
        digest.update(b"\0")
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", model)
    return cache_dir / f"{slug}-{digest.hexdigest()[:16]}.npy"
