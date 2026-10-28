from regcite.chunking import chunk_document
from regcite.ingest.convert import xhtml_to_markdown

FIXTURE = """<html><head><title>ignored title</title></head><body>
<p class="title-doc-first">REGULATION (EU) 2024/1689 before the first heading</p>
<div id="cpt_III">
<p class="title-division-1">CHAPTER III</p>
<p class="title-division-2"><span class="boldface">HIGH-RISK AI SYSTEMS</span></p>
<div id="cpt_III.sct_1">
<p class="title-division-1"><span class="italics">SECTION 1</span></p>
<p class="title-division-2">Classification</p>
</div>
</div>
<div class="eli-subdivision" id="art_14">
<p class="title-article-norm">Article 14</p>
<div class="eli-title"><p class="stitle-article-norm">Human oversight</p></div>
<div class="norm">
<span class="no-parag">1.  </span>
<div class="norm inline-element">High-risk AI systems shall be overseen<a href="#E0001">
<span class="superscript">1</span></a> by natural persons.</div>
</div>
<p class="modref"><a href="x">&#9660;M1</a></p>
<div class="norm">
<span class="no-parag">2.  </span>
<div class="norm inline-element">Oversight shall:
<div class="grid-container grid-list">
<div class="list grid-list-column-1"><span>(a) </span></div>
<div class="grid-list-column-2"><p class="norm">prevent risks;</p></div>
</div>
<div class="grid-container grid-list">
<div class="list grid-list-column-1"><span>(b) </span></div>
<div class="grid-list-column-2"><p class="norm">minimise&#160;harm.</p></div>
</div>
</div>
</div>
</div>
<p class="footnote">(<a href="#src.E0001"><span class="superscript">1</span></a>) Footnote text.</p>
<p class="title-annex-1">ANNEXES</p>
<table><tr><td><p>ANNEX I - table of contents entry</p></td></tr></table>
<div id="anx_III">
<p class="title-annex-1">ANNEX III</p>
<p class="title-annex-2">High-risk AI systems referred to in Article 6(2)</p>
<p class="norm">Biometrics.</p>
</div>
</body></html>"""


def test_headings_use_markdown_levels():
    lines = xhtml_to_markdown(FIXTURE).splitlines()
    headings = [line for line in lines if line.startswith("#")]
    assert headings == [
        "# Chapter III HIGH-RISK AI SYSTEMS",
        "## Section 1 Classification",
        "### Article 14 Human oversight",
        "# Annex III High-risk AI systems referred to in Article 6(2)",
    ]


def test_annex_title_in_second_annex_paragraph():
    xhtml = (
        '<p class="title-annex-1">ANNEX X</p><p class="title-annex-1">Large-scale IT systems</p>'
        '<p class="norm">1. Schengen.</p>'
    )
    assert xhtml_to_markdown(xhtml).splitlines()[0] == "# Annex X Large-scale IT systems"


def test_markers_are_joined_to_their_text():
    markdown = xhtml_to_markdown(FIXTURE)
    assert "1. High-risk AI systems shall be overseen by natural persons." in markdown
    assert "(a) prevent risks;" in markdown
    assert "(b) minimise harm." in markdown


def test_noise_is_dropped():
    markdown = xhtml_to_markdown(FIXTURE)
    for dropped in (
        "before the first heading",
        "ignored title",
        "M1",
        "Footnote text",
        "table of contents",
    ):
        assert dropped not in markdown


def test_output_chunks_into_article_citations():
    chunks = chunk_document("ai_act", xhtml_to_markdown(FIXTURE))
    citations = {chunk.citation for chunk in chunks}
    assert (
        "Chapter III HIGH-RISK AI SYSTEMS > Section 1 Classification > Article 14 Human oversight"
        in citations
    )
    assert "Annex III High-risk AI systems referred to in Article 6(2)" in citations
