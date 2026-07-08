import importlib.util
import io

import pytest

from clara import ingest as ingest_mod
from clara.ingest import _needs_ocr, _strip_html, from_html, from_pdf, from_text, ingest_bytes


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


# --- OCR (Phase 2) ------------------------------------------------------------

def test_needs_ocr_heuristic():
    assert _needs_ocr(["", "", ""]) is True                     # scan: no text
    assert _needs_ocr(["A" * 500]) is False                     # born-digital page
    assert _needs_ocr([]) is False                              # empty PDF, nothing to OCR


def _scan_pdf(text: str = "You must pay 500 dollars by June 1.") -> bytes:
    """A single-page image-only PDF — a stand-in for a scanned document."""
    pytest.importorskip("PIL")
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (600, 300), "white")
    ImageDraw.Draw(img).text((20, 140), text, fill="black")  # pixels, not a text layer
    buf = io.BytesIO()
    img.save(buf, "PDF")
    return buf.getvalue()


def test_from_pdf_off_leaves_scan_untouched():
    pytest.importorskip("pypdf")
    r = from_pdf(_scan_pdf(), ocr="off")
    assert r.ocr_applied is False
    assert r.text.strip() == ""            # no text layer, and we didn't OCR


def test_from_pdf_auto_invokes_ocr_when_scanned(monkeypatch):
    pytest.importorskip("pypdf")
    monkeypatch.setattr(ingest_mod, "_ocr_pdf", lambda data: "Recovered by OCR.")
    r = from_pdf(_scan_pdf(), ocr="auto")
    assert r.ocr_applied is True
    assert "Recovered by OCR." in r.text


def test_from_pdf_auto_degrades_when_ocr_engine_absent(monkeypatch):
    pytest.importorskip("pypdf")
    if importlib.util.find_spec("ocrmypdf") is not None:
        pytest.skip("ocrmypdf installed; the degrade path isn't exercised")
    # auto mode + no [ocr] extra: fall back to the (empty) text, don't crash.
    r = from_pdf(_scan_pdf(), ocr="auto")
    assert r.ocr_applied is False
    assert r.text.strip() == ""


def test_from_pdf_force_raises_without_engine():
    pytest.importorskip("pypdf")
    if importlib.util.find_spec("ocrmypdf") is not None:
        pytest.skip("ocrmypdf installed; the missing-dependency path isn't exercised")
    with pytest.raises(RuntimeError, match="ocr"):
        from_pdf(_scan_pdf(), ocr="force")


def test_from_pdf_skips_ocr_for_born_digital(monkeypatch):
    pytest.importorskip("pypdf")
    # If _needs_ocr is False, _ocr_pdf must never be called (no wasted OCR cost).
    def _boom(_data):
        raise AssertionError("OCR should not run on a text PDF")

    monkeypatch.setattr(ingest_mod, "_ocr_pdf", _boom)
    monkeypatch.setattr(ingest_mod, "_needs_ocr", lambda pages: False)
    r = from_pdf(_scan_pdf(), ocr="auto")
    assert r.ocr_applied is False
