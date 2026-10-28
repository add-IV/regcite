"""Download a legal act as XHTML from the Publications Office resolver.

eur-lex.europa.eu answers scripted requests with an empty page, so the
resolver is used instead.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request

from regcite.ingest.sources import Source

USER_AGENT = "regcite-research/0.1"


def fetch_source(source: Source, timeout: float = 120, retries: int = 3) -> bytes:
    request = urllib.request.Request(
        source.url,
        headers={
            "Accept": "application/xhtml+xml",
            "Accept-Language": "eng",
            "User-Agent": USER_AGENT,
        },
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
            if body:
                return body
        except urllib.error.URLError:
            if attempt == retries - 1:
                raise
        time.sleep(2**attempt)
    raise RuntimeError(f"Empty response for {source.url}")
