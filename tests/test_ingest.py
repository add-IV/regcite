from regcite.config import DEFAULT_MODEL, get_model
from regcite.ingest import load_corpus


def test_load_corpus_reads_supported_files_only(tmp_path):
    (tmp_path / "act.md").write_text("# Article 1\nSubject matter.\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("# Article 2\nScope.\n", encoding="utf-8")
    (tmp_path / "ignored.pdf").write_bytes(b"%PDF")

    chunks = load_corpus(tmp_path)

    assert {c.doc_id for c in chunks} == {"act", "notes"}


def test_load_corpus_empty_folder(tmp_path):
    assert load_corpus(tmp_path) == []


def test_model_defaults_and_env_override(monkeypatch):
    monkeypatch.delenv("REGCITE_MODEL", raising=False)
    assert get_model() == DEFAULT_MODEL
    monkeypatch.setenv("REGCITE_MODEL", "other-model")
    assert get_model() == "other-model"
