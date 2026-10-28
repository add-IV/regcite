"""Split regulatory documents into chunks that keep their location.

Each chunk carries a citation path built from the headings above it, for
example ``Chapter III > Article 14 > Paragraph 2``, so a search hit can be
quoted back to the exact place in the source document.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MARKDOWN_HEADING = re.compile(r"^(#{1,6})\s+(?P<title>.+?)\s*$")
# Legal headings such as "Article 14 Transparency" or "Art. 6". Lines that
# end in a period are treated as body text, so "Article 5 requires ..."
# inside a paragraph is not mistaken for a heading. A number followed directly
# by "(" is a cross-reference such as "Article 1(1)", not a heading.
ARTICLE_HEADING = re.compile(
    r"^(?P<title>(?:Article|Art\.|Section|Chapter|Annex)\s+[0-9IVXLC]+[A-Za-z]?\b(?!\().*?)\s*$"
)
MAX_HEADING_LENGTH = 120


@dataclass(frozen=True)
class Chunk:
    doc_id: str
    citation: str
    text: str
    line: int  # line of the heading that opens the section (1-based)


def chunk_document(doc_id: str, text: str, max_chars: int = 1200) -> list[Chunk]:
    """Split one document into chunks of roughly ``max_chars``.

    Sections start at headings. Within a section, paragraphs (separated by
    blank lines) are packed together until adding another would exceed
    ``max_chars``. A single paragraph longer than the limit is kept whole.
    """
    chunks: list[Chunk] = []
    stack: list[tuple[int, str]] = []  # (level, title) of open headings
    body: list[str] = []
    section_line = 1

    for line_no, line in enumerate(text.splitlines(), start=1):
        heading = _parse_heading(line)
        if heading is None:
            body.append(line)
            continue

        _emit(doc_id, stack, body, section_line, max_chars, chunks)
        body = []

        level, title = heading
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))
        section_line = line_no

    _emit(doc_id, stack, body, section_line, max_chars, chunks)
    return chunks


def _parse_heading(line: str) -> tuple[int, str] | None:
    match = MARKDOWN_HEADING.match(line)
    if match:
        return len(match.group(1)), match.group("title")

    if len(line) <= MAX_HEADING_LENGTH and not line.rstrip().endswith("."):
        match = ARTICLE_HEADING.match(line)
        if match:
            return 1, match.group("title")

    return None


def _emit(
    doc_id: str,
    stack: list[tuple[int, str]],
    body: list[str],
    start: int,
    max_chars: int,
    out: list[Chunk],
) -> None:
    citation = " > ".join(title for _, title in stack) or doc_id
    paragraphs = [p.strip() for p in "\n".join(body).split("\n\n") if p.strip()]

    buffer = ""
    for paragraph in paragraphs:
        if buffer and len(buffer) + len(paragraph) > max_chars:
            out.append(Chunk(doc_id, citation, buffer, start))
            buffer = ""
        buffer = f"{buffer}\n\n{paragraph}" if buffer else paragraph

    if buffer:
        out.append(Chunk(doc_id, citation, buffer, start))
