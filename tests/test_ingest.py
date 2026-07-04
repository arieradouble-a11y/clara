import importlib.util

import pytest

from clara.ingest import _strip_html, from_html, from_pdf, from_text, ingest_bytes


def test_from_text_normalizes_whitespace():
    r = from_text("Line one.\r\n\r\n\r\nLine two.  ")
    assert r.text == "Line one.\n\nLine two."
    assert r.kind == "text"


def test_strip_html_drops_boilerplate():
    # Our dependency-free stripper (the fallback when trafilatura is absent).
    html = (
        "<html><head><title>Notice</title></head><body>"
        "<nav>menu links</nav><h1>Heading</h1><p>Hello world.</p>"
        "<script>var x=1;</script><footer>copyright</footer></body></html>"
    )
    text, title = _strip_html(html)
    assert "Hello world." in text
    assert "Heading" in text
    assert "menu links" not in text     # nav skipped
    assert "var x" not in text          # script skipped
    assert "copyright" not in text      # footer skipped
    assert title == "Notice"


def test_from_html_keeps_content_and_title():
    # Extractor-agnostic (trafilatura if installed, else the stripper).
    r = from_html("<html><head><title>Doc</title></head><body><p>Hello world.</p></body></html>")
    assert "Hello world." in r.text
    assert r.kind == "html"


def test_strip_html_decodes_entities():
    text, _ = _strip_html("<p>Fee is 5 &amp; up &lt; limit</p>")
    assert "5 & up < limit" in text


def test_ingest_bytes_dispatch():
    assert "Plain text." in ingest_bytes("a.txt", b"Plain text.").text
    assert ingest_bytes("a.txt", b"x").kind == "text"
    assert "Hi there." in ingest_bytes("a.html", b"<p>Hi there.</p>").text


def test_pdf_without_pypdf_raises_clearly():
    if importlib.util.find_spec("pypdf") is not None:
        pytest.skip("pypdf installed; error path not exercised")
    with pytest.raises(RuntimeError, match="pypdf"):
        from_pdf(b"%PDF-1.4 not really")
