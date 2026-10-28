"""Fetch, convert and record the corpus: ``regcite ingest``."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable
from datetime import date
from pathlib import Path

from regcite.ingest.convert import xhtml_to_markdown
from regcite.ingest.fetch import fetch_source
from regcite.ingest.sources import SOURCES, Source


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ingest(
    out_dir: Path,
    manifest_path: Path,
    sources: Iterable[Source] = SOURCES,
    refresh: bool = False,
    fetch: Callable[[Source], bytes] = fetch_source,
    today: str | None = None,
) -> list[dict]:
    """Write ``<doc_id>.md`` files under ``out_dir`` and update the manifest.

    Downloaded XHTML is cached in ``out_dir/source`` and reused unless
    ``refresh`` is set, so reruns need no network and keep their retrieval date.
    """
    today = today or date.today().isoformat()
    previous = _read_manifest(manifest_path)
    source_dir = out_dir / "source"
    source_dir.mkdir(parents=True, exist_ok=True)

    entries = []
    for source in sources:
        raw_path = source_dir / f"{source.doc_id}.xhtml"
        if refresh or not raw_path.exists():
            raw = fetch(source)
            raw_path.write_bytes(raw)
            retrieved = today
        else:
            raw = raw_path.read_bytes()
            old = previous.get(source.doc_id, {})
            retrieved = old["retrieved"] if old.get("source_sha256") == sha256_hex(raw) else today

        markdown = xhtml_to_markdown(raw.decode("utf-8"))
        (out_dir / f"{source.doc_id}.md").write_text(markdown, encoding="utf-8", newline="\n")
        entries.append(
            {
                "doc_id": source.doc_id,
                "title": source.title,
                "celex": source.celex,
                "version": f"consolidated {source.consolidated}",
                "url": source.url,
                "retrieved": retrieved,
                "source_sha256": sha256_hex(raw),
                "markdown_sha256": sha256_hex(markdown.encode("utf-8")),
                "articles": sum(
                    1 for line in markdown.splitlines() if line.startswith("### Article")
                ),
            }
        )

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps({"documents": entries}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return entries


def _read_manifest(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    documents = json.loads(path.read_text(encoding="utf-8")).get("documents", [])
    return {entry["doc_id"]: entry for entry in documents}
