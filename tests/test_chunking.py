from regcite.chunking import chunk_document

SAMPLE = """# Regulation on AI in medical devices

Intro paragraph.

Article 14 Transparency

Providers shall ensure transparency.

Article 5 requires that systems be safe. This line is body text.

Annex I

Device list.
"""


def test_citations_follow_heading_hierarchy():
    chunks = chunk_document("doc", SAMPLE)
    citations = [c.citation for c in chunks]

    assert citations[0] == "Regulation on AI in medical devices"
    assert "Regulation on AI in medical devices > Article 14 Transparency" not in citations
    assert "Article 14 Transparency" in citations
    assert "Annex I" in citations
    assert "Article 14 Transparency > Annex I" not in citations
    assert any(c.citation == "Article 14 Transparency" and "Providers" in c.text for c in chunks)


def test_cross_reference_line_is_not_a_heading():
    text = "# Annex XVII\n\nArticle 1(1)\n\nArticle 2(3)\n\nDirective 93/42/EEC."
    chunks = chunk_document("doc", text)
    assert {c.citation for c in chunks} == {"Annex XVII"}
    assert "Article 1(1)" in chunks[0].text


def test_sentence_starting_with_article_is_not_a_heading():
    chunks = chunk_document("doc", SAMPLE)
    body_chunk = next(c for c in chunks if "Article 5 requires" in c.text)
    assert body_chunk.citation == "Article 14 Transparency"


def test_long_sections_are_split_on_paragraphs():
    paragraph = "word " * 100
    text = "Article 1 Scope\n\n" + "\n\n".join([paragraph] * 5)
    chunks = chunk_document("doc", text, max_chars=600)

    assert len(chunks) > 1
    assert all(c.citation == "Article 1 Scope" for c in chunks)
    assert all(len(c.text) <= 600 + len(paragraph) for c in chunks)


def test_line_numbers_point_at_opening_heading():
    chunks = chunk_document("doc", SAMPLE)
    intro = next(c for c in chunks if c.text.startswith("Intro"))
    article = next(c for c in chunks if c.citation == "Article 14 Transparency")
    assert intro.line == 1
    assert article.line == 5
