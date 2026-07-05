"""Accessible document export — closing the loop from a hard document to one a
person can actually read.

Two outputs:
  - Semantic accessible HTML: pure Python, no dependencies, always available.
    Correct language attribute, a single <h1>, real paragraphs, and for Easy
    Read an ordered list of picture+text rows with alt text. Good contrast and
    generous spacing. Browsers produce a tagged PDF when you print this.
  - Tagged PDF (PDF/UA-1) via WeasyPrint (optional `[pdf]` extra). If WeasyPrint
    (or its system libraries) isn't available, it raises a clear message rather
    than a broken file — the HTML remains the reliable path.
"""
from __future__ import annotations

import html as _html

_CSS = (
    ":root{--fg:#1a1a1a;--bg:#fff;--muted:#555;--line:#ddd}"
    "@media(prefers-color-scheme:dark){:root{--fg:#ededed;--bg:#161616;--muted:#aaa;--line:#333}}"
    "*{box-sizing:border-box}"
    "body{margin:0;background:var(--bg);color:var(--fg);"
    "font:1.15rem/1.6 system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}"
    "main{max-width:40em;margin:0 auto;padding:2rem 1.25rem 4rem}"
    "h1{font-size:1.6rem;line-height:1.25;margin:0 0 1.25rem}"
    "p{margin:0 0 1rem}"
    "ol.easyread{list-style:none;margin:0;padding:0}"
    "ol.easyread li{display:flex;gap:1rem;align-items:center;padding:.75rem;"
    "border:1px solid var(--line);border-radius:12px;margin:0 0 .75rem}"
    "ol.easyread img{width:84px;height:84px;object-fit:contain;flex:none;background:#fff;"
    "border:1px solid var(--line);border-radius:10px}"
    "ol.easyread .txt{font-size:1.35rem}"
    "footer{margin-top:2rem;color:var(--muted);font-size:.85rem;"
    "border-top:1px solid var(--line);padding-top:1rem}"
)


def _paragraphs_html(text: str) -> str:
    parts = [p.strip() for p in (text or "").replace("\r\n", "\n").split("\n") if p.strip()]
    return "\n".join(f"<p>{_html.escape(p)}</p>" for p in parts) or "<p></p>"


def _easyread_html(lines: list, embed_images: bool = False) -> str:
    items = []
    for ln in lines or []:
        url = ln.get("image_url")
        if embed_images and ln.get("pictogram_id"):
            from .pictograms import image_data_uri  # lazy: keeps export import-light

            uri = image_data_uri(ln["pictogram_id"])
            if uri:  # fall back to the URL if the image can't be fetched
                url = uri
        img = ""
        if url:
            alt = _html.escape(ln.get("keyword") or "")
            img = f'<img src="{_html.escape(url)}" alt="{alt}">'
        items.append(f'<li>{img}<span class="txt">{_html.escape(ln.get("text", ""))}</span></li>')
    return '<ol class="easyread">\n' + "\n".join(items) + "\n</ol>"


def document_html(
    *,
    title: str = "Plain-language document",
    lang: str = "en",
    kind: str = "text",
    text: str | None = None,
    lines: list | None = None,
    footer: str | None = None,
    embed_images: bool = False,
) -> str:
    body = _easyread_html(lines, embed_images) if kind == "easyread" else _paragraphs_html(text or "")
    foot = f"<footer>{_html.escape(footer)}</footer>\n" if footer else ""
    return (
        f'<!DOCTYPE html>\n<html lang="{_html.escape(lang)}">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{_html.escape(title)}</title>\n<style>{_CSS}</style>\n</head>\n<body>\n"
        f"<main>\n<h1>{_html.escape(title)}</h1>\n{body}\n{foot}</main>\n</body>\n</html>\n"
    )


def document_pdf(html_doc: str, *, tagged: bool = True) -> bytes:
    """Render accessible HTML to a tagged PDF (PDF/UA-1) via WeasyPrint."""
    try:
        from weasyprint import HTML
    except Exception as e:  # not installed, or system libs (GTK/pango/cairo) missing
        raise RuntimeError(
            'PDF export needs WeasyPrint: pip install "clara[pdf]" '
            "(on Windows it also needs the GTK runtime). Or open the accessible HTML "
            "and print to PDF — browsers tag it from the semantic markup."
        ) from e
    try:
        return HTML(string=html_doc).write_pdf(pdf_variant="pdf/ua-1" if tagged else None)
    except TypeError:
        return HTML(string=html_doc).write_pdf()  # older WeasyPrint without pdf_variant
