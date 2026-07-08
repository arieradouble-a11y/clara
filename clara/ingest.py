"""Ingestion — the front door. Turn a real document (plain text, HTML, a URL, a
PDF, or a DOCX) into clean text with paragraph structure preserved, ready for the
simplify / easyread pipeline.

Parsers are optional dependencies (`[ingest]` extra) and degrade honestly:
- HTML has a pure-stdlib fallback, so it always works; trafilatura is used for
  cleaner main-content extraction when installed.
- URL fetching uses stdlib urllib (no new dependency).
- PDF (pypdf) and DOCX (python-docx) raise a clear message if the library is
  absent, rather than a broken result.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


@dataclass
class IngestResult:
    text: str
    title: str | None = None
    kind: str = "text"
    ocr_applied: bool = False   # True when text came from OCR (a scanned PDF)


def _clean(text: str) -> str:
    """Normalize line endings, trim each line, collapse blank runs to a single
    blank so paragraphs survive but visual noise doesn't."""
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    out: list[str] = []
    blank = 0
    for line in text.split("\n"):
        line = line.strip()
        if line:
            out.append(line)
            blank = 0
        else:
            blank += 1
            if blank == 1:
                out.append("")
    return "\n".join(out).strip()


def from_text(text: str) -> IngestResult:
    return IngestResult(text=_clean(text), kind="text")


# --- HTML ---------------------------------------------------------------------

class _Stripper(HTMLParser):
    _SKIP = {"script", "style", "nav", "header", "footer", "aside", "noscript", "form", "svg"}
    _BLOCK = {"p", "br", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "article"}

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.title: str | None = None
        self._skip = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip += 1
        elif tag == "title":
            self._in_title = True
        elif tag in self._BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skip:
            self._skip -= 1
        elif tag == "title":
            self._in_title = False
        elif tag in self._BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._in_title:
            t = data.strip()
            if t and not self.title:
                self.title = t
            return
        if self._skip == 0:
            self.parts.append(data)


def _html_title(html: str) -> str | None:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else None


def _strip_html(html: str) -> tuple[str, str | None]:
    """Dependency-free extraction: drop boilerplate tags, keep block structure."""
    p = _Stripper()
    p.feed(html)
    return _clean("".join(p.parts)), p.title


def from_html(html: str, title: str | None = None) -> IngestResult:
    # Prefer trafilatura for clean main-content extraction; fall back to stdlib.
    try:
        import trafilatura
        extracted = trafilatura.extract(html, include_comments=False, include_tables=True)
        if extracted:
            return IngestResult(text=_clean(extracted), title=title or _html_title(html), kind="html")
    except Exception:
        pass
    text, found_title = _strip_html(html)
    return IngestResult(text=text, title=title or found_title, kind="html")


def from_url(url: str) -> IngestResult:
    req = Request(url, headers={"User-Agent": "clara-ingest/0.1"})  # ASCII-only header
    with urlopen(req, timeout=20) as r:
        raw = r.read()
        charset = r.headers.get_content_charset() or "utf-8"
    res = from_html(raw.decode(charset, errors="replace"))
    res.kind = "url"
    return res


# --- PDF ----------------------------------------------------------------------

# Below this many extractable characters per page, a PDF is almost certainly a
# scan (an image with no text layer) rather than a born-digital document. Kept
# deliberately low so a normal sparse page (a cover, a form) doesn't trip OCR.
_OCR_MIN_CHARS_PER_PAGE = 12


def _needs_ocr(pages: list[str]) -> bool:
    """Heuristic: does this PDF look like a scan with no usable text layer?"""
    if not pages:
        return False
    total = sum(len(p.strip()) for p in pages)
    return total < _OCR_MIN_CHARS_PER_PAGE * len(pages)


def _ocr_pdf(data: bytes) -> str:
    """Add a text layer to a scanned PDF with OCR, then extract it.

    Uses ocrmypdf (which drives tesseract + ghostscript). This is the heavy path,
    so it lives behind the `[ocr]` extra and only runs when a PDF looks scanned.
    """
    try:
        import ocrmypdf
    except Exception as e:
        raise RuntimeError(
            'OCR needs the [ocr] extra: pip install "clara[ocr]" and install the '
            "tesseract binary (e.g. apt install tesseract-ocr, or the Windows build)."
        ) from e
    from pypdf import PdfReader

    import os
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        inp = os.path.join(d, "in.pdf")
        out = os.path.join(d, "out.pdf")
        with open(inp, "wb") as f:
            f.write(data)
        # force_ocr: rasterize and OCR every page. Safe here because we only reach
        # this on a PDF we've judged to have effectively no text layer.
        ocrmypdf.ocr(inp, out, force_ocr=True, progress_bar=False, output_type="pdf")
        reader = PdfReader(out)
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)


def from_pdf(source, *, ocr: str = "auto") -> IngestResult:
    """Extract text from a PDF, optionally OCR-ing a scanned one.

    ocr: "auto" (default) OCRs only when the PDF looks like a scan and the [ocr]
    extra is installed, degrading to the sparse text otherwise; "force" always
    OCRs and raises if the extra is missing; "off" never OCRs.
    """
    try:
        from pypdf import PdfReader
    except Exception as e:
        raise RuntimeError('PDF ingestion needs pypdf: pip install "clara[ingest]".') from e
    data = bytes(source) if isinstance(source, (bytes, bytearray)) else source.read()
    reader = PdfReader(io.BytesIO(data))
    pages = [(page.extract_text() or "") for page in reader.pages]
    title = None
    try:
        if reader.metadata and reader.metadata.title:
            title = reader.metadata.title
    except Exception:
        title = None

    text = _clean("\n\n".join(pages))
    applied = False
    if ocr != "off" and (ocr == "force" or _needs_ocr(pages)):
        try:
            ocr_text = _clean(_ocr_pdf(data))
        except RuntimeError:
            if ocr == "force":
                raise
            ocr_text = ""  # auto mode: [ocr] extra absent — keep what little we have
        if len(ocr_text) > len(text):
            text, applied = ocr_text, True
    return IngestResult(text=text, title=title, kind="pdf", ocr_applied=applied)


# --- DOCX ---------------------------------------------------------------------

def from_docx(source) -> IngestResult:
    try:
        import docx
    except Exception as e:
        raise RuntimeError('DOCX ingestion needs python-docx: pip install "clara[ingest]".') from e
    stream = io.BytesIO(source) if isinstance(source, (bytes, bytearray)) else source
    document = docx.Document(stream)
    paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    title = None
    for p in document.paragraphs:
        name = (p.style.name or "").lower() if p.style else ""
        if p.text.strip() and (name.startswith("title") or name.startswith("heading")):
            title = p.text.strip()
            break
    return IngestResult(text=_clean("\n\n".join(paragraphs)), title=title, kind="docx")


# --- Dispatch -----------------------------------------------------------------

def ingest_bytes(filename: str, data: bytes, *, ocr: str = "auto") -> IngestResult:
    ext = Path(filename or "").suffix.lower()
    if ext == ".pdf":
        return from_pdf(bytes(data), ocr=ocr)
    if ext == ".docx":
        return from_docx(bytes(data))
    if ext in (".html", ".htm"):
        return from_html(bytes(data).decode("utf-8", "replace"))
    return from_text(bytes(data).decode("utf-8", "replace"))


def ingest_file(path, *, ocr: str = "auto") -> IngestResult:
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".pdf":
        return from_pdf(path.read_bytes(), ocr=ocr)
    if ext == ".docx":
        return from_docx(path.read_bytes())
    if ext in (".html", ".htm"):
        return from_html(path.read_text(encoding="utf-8", errors="replace"))
    return from_text(path.read_text(encoding="utf-8", errors="replace"))
