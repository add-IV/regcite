import json

from regcite.cli import main
from regcite.ingest import ingest
from regcite.ingest.sources import Source

XHTML = b"""<html><body>
<div class="eli-subdivision" id="art_1">
<p class="title-article-norm">Article 1</p>
<div class="eli-title"><p class="stitle-article-norm">Subject matter</p></div>
<div class="norm"><p class="norm">This Regulation lays down rules.</p></div>
</div></body></html>"""

SOURCE = Source("demo", "Demo act", "02099R0001-20260101")


def test_source_version_comes_from_celex():
    assert SOURCE.consolidated == "2026-01-01"
    assert SOURCE.url.endswith("/02099R0001-20260101")


def test_ingest_writes_markdown_and_manifest(tmp_path):
    entries = ingest(
        tmp_path / "raw",
        tmp_path / "manifest.json",
        sources=[SOURCE],
        fetch=lambda source: XHTML,
        today="2026-10-28",
    )

    assert (tmp_path / "raw" / "demo.md").read_text(encoding="utf-8").startswith("### Article 1")
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["documents"] == entries
    assert entries[0]["retrieved"] == "2026-10-28"
    assert entries[0]["articles"] == 1
    assert len(entries[0]["source_sha256"]) == 64


def test_rerun_uses_cache_and_keeps_retrieval_date(tmp_path):
    kwargs = {"sources": [SOURCE], "fetch": lambda source: XHTML}
    ingest(tmp_path / "raw", tmp_path / "m.json", today="2026-10-28", **kwargs)

    def no_network(source):
        raise AssertionError("cache should be used")

    entries = ingest(
        tmp_path / "raw",
        tmp_path / "m.json",
        sources=[SOURCE],
        fetch=no_network,
        today="2027-01-01",
    )
    assert entries[0]["retrieved"] == "2026-10-28"


def test_refresh_downloads_again_with_new_date(tmp_path):
    kwargs = {"sources": [SOURCE], "fetch": lambda source: XHTML}
    ingest(tmp_path / "raw", tmp_path / "m.json", today="2026-10-28", **kwargs)
    entries = ingest(
        tmp_path / "raw", tmp_path / "m.json", today="2027-01-01", refresh=True, **kwargs
    )
    assert entries[0]["retrieved"] == "2027-01-01"


def test_cli_ingest_prints_summary(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        "regcite.cli.ingest",
        lambda out, manifest, refresh: [
            {"doc_id": "demo", "version": "consolidated 2026-01-01", "articles": 3}
        ],
    )
    code = main(["ingest", "--out", str(tmp_path), "--manifest", str(tmp_path / "m.json")])
    assert code == 0
    assert "demo: consolidated 2026-01-01, 3 articles" in capsys.readouterr().out
