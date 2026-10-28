"""Convert consolidated EU legal-act XHTML into Markdown that ``chunking`` can cite.

Chapters and annexes become level-1 headings, sections level 2, and articles
level 3, so a chunk's citation reads ``Chapter III > Section 3 > Article 14 ...``.
Text before the first heading, footnotes, amendment markers and the annex
table of contents are dropped. Tables are flattened to one paragraph per cell.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

SKIP_CLASSES = {
    "modref",
    "arrow",
    "footnote",
    "disclaimer",
    "superscript",
    "hd-toc-1",
    "hd-toc-2",
    "hd-toc-3",
}
SKIP_TAGS = {"head", "script", "style"}
VOID_TAGS = {"br", "hr", "img", "meta", "link", "col", "input"}
BLOCK_TAGS = {"p", "div", "tr", "td", "th", "li", "ul", "ol", "table", "h1", "h2", "h3", "h4"}
ROLE_BY_CLASS = {
    "title-article-norm": "article",
    "title-annex-1": "annex",
    "title-division-1": "division",
    "title-division-2": "sub",
    "title-annex-2": "sub",
    "stitle-article-norm": "sub",
}
# Paragraph numbers and list labels sit in their own element; they are joined
# to the text that follows.
MARKER = re.compile(r"^(?:\(?\d+\)?\.?|\(?[a-z]{1,4}\)|[–—-]|•)$")


def xhtml_to_markdown(xhtml: str) -> str:
    converter = _Converter()
    converter.feed(xhtml)
    converter.close()
    converter.finish()
    return "\n\n".join(converter.out) + "\n"


class _Converter(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.buf: list[str] = []
        self.prefix = ""
        self.stack: list[tuple[str, bool, str | None]] = []
        self.skip = 0
        self.pending: list | None = None  # [level, kind, text] of an unwritten heading
        self.started = False
        self.suppress = False

    def finish(self) -> None:
        self._flush()
        self._commit()

    def handle_starttag(self, tag, attrs):
        if tag in VOID_TAGS:
            if tag == "br":
                self.buf.append(" ")
            return
        classes = set((dict(attrs).get("class") or "").split())
        skip = tag in SKIP_TAGS or bool(classes & SKIP_CLASSES)
        role = None if skip else self._role(classes)
        if not skip and (role or tag in BLOCK_TAGS):
            self._flush()
        self.stack.append((tag, skip, role))
        if skip:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                break
        else:
            return
        popped = self.stack[i:]
        del self.stack[i:]
        self.skip -= sum(1 for _, skip, _ in popped if skip)
        _, skip, role = popped[0]
        if skip:
            return
        if role:
            self._end_role(role)
        elif tag in BLOCK_TAGS:
            self._flush()

    def handle_data(self, data):
        if not self.skip:
            self.buf.append(data)

    def _role(self, classes: set[str]) -> str | None:
        for name in classes:
            if name in ROLE_BY_CLASS:
                return ROLE_BY_CLASS[name]
        # MDR and IVDR put the annex title in a group-sequence paragraph.
        if "title-gr-seq-level-1" in classes and self.pending and self.pending[1] == "annex":
            return "sub"
        return None

    def _end_role(self, role: str) -> None:
        text = _normalise("".join(self.buf))
        self.buf = []
        if not text:
            return
        # Some annexes give their title in a second annex-title paragraph.
        if role == "annex" and self.pending and not text.upper().startswith("ANNEX"):
            role = "sub"
        if role == "sub":
            if self.pending:
                self.pending[2] += f" {text}"
            else:
                self._emit(text)
            return
        self._commit()
        if role == "article":
            level = 3
        elif role == "annex" or not text.upper().startswith("SECTION"):
            level = 1
        else:
            level = 2
        words = text.split(" ", 1)
        words[0] = words[0].capitalize()
        self.pending = [level, role, " ".join(words)]

    def _flush(self) -> None:
        text = _normalise("".join(self.buf))
        self.buf = []
        if not text:
            return
        if MARKER.match(text):
            self.prefix = f"{self.prefix} {text}".strip()
            return
        if self.prefix:
            text = f"{self.prefix} {text}"
            self.prefix = ""
        self._emit(text)

    def _emit(self, text: str) -> None:
        self._commit()
        if self.started and not self.suppress:
            self.out.append(text)

    def _commit(self) -> None:
        if not self.pending:
            return
        level, _, text = self.pending
        self.pending = None
        if text.upper() == "ANNEXES":  # table of contents of the annexes
            self.suppress = True
            return
        self.suppress = False
        self.started = True
        self.out.append(f"{'#' * level} {text}")


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()
