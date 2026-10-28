"""Read a folder of .md/.txt regulation files and chunk them by article."""

from __future__ import annotations

from pathlib import Path

from regcite.chunking import Chunk, chunk_document

SUPPORTED_SUFFIXES = {".md", ".txt"}


def load_corpus(corpus: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(corpus.rglob("*")):
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        chunks.extend(chunk_document(path.stem, text))
    return chunks
