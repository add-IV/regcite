"""Load the gold question set and decide whether a chunk matches an expected reference."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from regcite.chunking import Chunk

CATEGORIES = {"direct", "paraphrase", "cross_regulation", "out_of_scope"}


@dataclass(frozen=True)
class Expected:
    doc_id: str
    ref: str  # e.g. "Article 14" or "Annex VIII"


@dataclass(frozen=True)
class Question:
    id: str
    category: str
    question: str
    expected: tuple[Expected, ...]


def load_gold(path: Path) -> list[Question]:
    questions = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        expected = tuple(Expected(e["doc_id"], e["ref"]) for e in row["expected"])
        questions.append(Question(row["id"], row["category"], row["question"], expected))
    return questions


_ARTICLE_REF = re.compile(r"(?:Article \d+[a-z]?|Annex [IVXLC]+)(?=\s|$)")


def article_key(chunk: Chunk) -> tuple[str, str]:
    """The (document, article or annex) a chunk belongs to, used to count an article once."""
    for part in reversed(chunk.citation.split(" > ")):
        found = _ARTICLE_REF.match(part)
        if found:
            return chunk.doc_id, found.group()
    return chunk.doc_id, chunk.citation


def matches(chunk: Chunk, expected: Expected) -> bool:
    """True if the chunk sits under the expected article or annex of the expected document."""
    if chunk.doc_id != expected.doc_id:
        return False
    pattern = rf"(?:^| > ){re.escape(expected.ref)}(?:\s|$)"
    return re.search(pattern, chunk.citation) is not None
