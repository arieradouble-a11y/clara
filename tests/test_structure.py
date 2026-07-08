from clara.export import _blocks_html, document_html
from clara.ingest import from_html
from clara.llm.base import MockProvider
from clara.pipeline import simplify_structured
from clara.simplify import simplify_blocks
from clara.structure import (
    HEADING,
    LIST_ITEM,
    PARAGRAPH,
    Block,
    block_dict,
    block_from_dict,
    blocks_to_text,
)

NOTICE = """
<html><head><title>About Your Payment</title></head><body>
<nav>skip me</nav>
<h1>Notice of Amount Due</h1>
<p>A balance remains unpaid for 2025.</p>
<h2>What you need to do</h2>
<ol><li>Pay 500 dollars by June 1.</li><li>Or call to arrange a plan.</li></ol>
<h3>If you disagree</h3>
<ul><li>Send us your receipts.</li></ul>
<footer>copyright</footer>
</body></html>
"""


# --- model --------------------------------------------------------------------

def test_blocks_to_text_flattens():
    blocks = [Block(HEADING, "Title", level=2), Block(PARAGRAPH, "Body."), Block(PARAGRAPH, "")]
    assert blocks_to_text(blocks) == "Title\n\nBody."   # empties dropped


def test_block_dict_roundtrip():
    b = Block(LIST_ITEM, "Step one.", level=0, ordered=True)
    assert block_from_dict(block_dict(b)) == b


# --- ingest -------------------------------------------------------------------

def test_html_ingest_captures_structure():
    blocks = from_html(NOTICE).blocks
    kinds = [(b.type, b.text) for b in blocks]
    # boilerplate skipped, <title> not a body block
    assert ("paragraph", "skip me") not in kinds
    assert not any(b.text == "About Your Payment" for b in blocks)
    # headings, ordered + unordered list items all survive with the right type
    assert Block(HEADING, "Notice of Amount Due", level=1) in blocks
    assert Block(HEADING, "What you need to do", level=2) in blocks
    assert Block(LIST_ITEM, "Pay 500 dollars by June 1.", ordered=True) in blocks
    assert Block(LIST_ITEM, "Send us your receipts.", ordered=False) in blocks


def test_plain_text_has_no_blocks():
    from clara.ingest import from_text
    assert from_text("Just prose.").blocks == []


def test_docx_ingest_classifies_headings_and_lists():
    import io

    import pytest
    docx = pytest.importorskip("docx")
    from clara.ingest import from_docx

    d = docx.Document()
    d.add_heading("Notice", level=1)
    d.add_paragraph("Body text.")
    d.add_paragraph("Pay by June 1.", style="List Number")
    d.add_paragraph("Bring receipts.", style="List Bullet")
    buf = io.BytesIO()
    d.save(buf)

    blocks = from_docx(buf.getvalue()).blocks
    assert Block(HEADING, "Notice", level=1) in blocks
    assert Block(PARAGRAPH, "Body text.") in blocks
    assert Block(LIST_ITEM, "Pay by June 1.", ordered=True) in blocks
    assert Block(LIST_ITEM, "Bring receipts.", ordered=False) in blocks


# --- export -------------------------------------------------------------------

def test_blocks_html_renders_headings_and_lists():
    blocks = [
        block_dict(Block(HEADING, "Do this", level=2)),
        block_dict(Block(LIST_ITEM, "First", ordered=True)),
        block_dict(Block(LIST_ITEM, "Second", ordered=True)),
        block_dict(Block(PARAGRAPH, "A note.")),
        block_dict(Block(LIST_ITEM, "Bullet", ordered=False)),
    ]
    html = _blocks_html(blocks)
    assert "<h2>Do this</h2>" in html
    assert html.count("<ol>") == 1 and html.count("</ol>") == 1   # consecutive items = one list
    assert "<li>First</li>" in html and "<li>Second</li>" in html
    assert "<p>A note.</p>" in html
    assert "<ul>" in html and "<li>Bullet</li>" in html


def test_blocks_html_deep_heading_becomes_h3_and_escapes():
    html = _blocks_html([block_dict(Block(HEADING, "5 < 6 & up", level=4))])
    assert "<h3>5 &lt; 6 &amp; up</h3>" in html


def test_document_html_structured_kind_single_h1():
    doc = document_html(kind="structured", title="Doc",
                        blocks=[block_dict(Block(HEADING, "Section", level=2))])
    assert doc.count("<h1>") == 1        # the title owns the only h1
    assert "<h2>Section</h2>" in doc


# --- simplify + pipeline ------------------------------------------------------

def test_simplify_blocks_preserves_structure():
    # Mock echoes prompt -> text unchanged, so we can assert structure is kept.
    blocks = from_html(NOTICE).blocks
    out = simplify_blocks(blocks, provider=MockProvider())
    assert [b.type for b in out] == [b.type for b in blocks]
    assert [b.ordered for b in out] == [b.ordered for b in blocks]
    # headings pass through verbatim
    assert out[0] == blocks[0]


def test_simplify_structured_verifies_on_flattened_text():
    blocks = from_html(NOTICE).blocks
    res = simplify_structured(blocks, provider=MockProvider())
    assert res.blocks and res.faithfulness.ok          # echo -> faithful
    assert "500" in blocks_to_text(res.blocks)
