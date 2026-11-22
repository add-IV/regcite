from regcite.ingest import load_corpus


def test_load_corpus_reads_supported_files_only(tmp_path):
    (tmp_path / "act.md").write_text("# Article 1\nSubject matter.\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("# Article 2\nScope.\n", encoding="utf-8")
    (tmp_path / "ignored.pdf").write_bytes(b"%PDF")

    chunks = load_corpus(tmp_path)

    assert {c.doc_id for c in chunks} == {"act", "notes"}


def test_load_corpus_empty_folder(tmp_path):
    assert load_corpus(tmp_path) == []
