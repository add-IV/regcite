"""Keyword search over chunks using BM25.

This is a plain-Python baseline with no dependencies. It is good at exact
legal terms ("high-risk", "Article 14", "510(k)"), which embedding search
often blurs. Embeddings can be added later and compared against it.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from regcite.chunking import Chunk

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class BM25Index:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.n = len(chunks)

        # The citation is indexed with the text so a query can match a heading
        # such as "Human oversight" even when the body uses other words.
        self._term_freqs = [Counter(tokenize(f"{c.citation} {c.text}")) for c in chunks]
        self._lengths = [sum(tf.values()) for tf in self._term_freqs]
        self._avg_length = sum(self._lengths) / self.n if self.n else 0.0
        self._doc_freqs: Counter[str] = Counter()
        for tf in self._term_freqs:
            self._doc_freqs.update(tf.keys())

    def search(self, query: str, top_k: int = 5) -> list[tuple[Chunk, float]]:
        scores = [0.0] * self.n
        for term in set(tokenize(query)):
            df = self._doc_freqs.get(term, 0)
            if df == 0:
                continue
            idf = math.log(1 + (self.n - df + 0.5) / (df + 0.5))
            for i, tf in enumerate(self._term_freqs):
                freq = tf.get(term, 0)
                if freq:
                    norm = 1 - self.b + self.b * self._lengths[i] / self._avg_length
                    scores[i] += idf * freq * (self.k1 + 1) / (freq + self.k1 * norm)

        ranked = sorted(range(self.n), key=lambda i: scores[i], reverse=True)
        return [(self.chunks[i], scores[i]) for i in ranked[:top_k] if scores[i] > 0]
