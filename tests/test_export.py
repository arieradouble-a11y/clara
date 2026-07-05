from clara.export import document_html, document_pdf


def test_html_has_lang_title_and_paragraphs():
    doc = document_html(title="Notice", lang="ru", kind="text",
                        text="Первый абзац.\nВторой абзац.")
    assert '<html lang="ru">' in doc
    assert "<title>Notice</title>" in doc
    assert "<h1>Notice</h1>" in doc
    assert doc.count("<p>") == 2


def test_html_escapes_content():
    doc = document_html(kind="text", text='a < b & c "d"')
    assert "&lt;" in doc and "&amp;" in doc
    assert "<script>" not in document_html(kind="text", text="<script>x</script>")


def test_easyread_html_has_list_images_and_alt():
    lines = [
        {"text": "Close the water.", "keyword": "water", "image_url": "https://x/1.png"},
        {"text": "Pay.", "keyword": None, "image_url": None},
    ]
    doc = document_html(kind="easyread", lines=lines, title="Easy Read")
    assert '<ol class="easyread">' in doc
    assert 'src="https://x/1.png"' in doc
    assert 'alt="water"' in doc
    assert doc.count("<li>") == 2
    assert "<img" in doc and doc.count("<img") == 1  # second line has no picture


def test_footer_included_when_given():
    assert "assistive" in document_html(kind="text", text="hi", footer="assistive note")


def test_easyread_embeds_images(monkeypatch):
    import clara.pictograms as pics
    monkeypatch.setattr(pics, "image_data_uri", lambda pid, size=300: f"data:image/png;base64,ABC{pid}")
    lines = [{"text": "Water.", "keyword": "water", "image_url": "https://x/1.png", "pictogram_id": 11}]
    doc = document_html(kind="easyread", lines=lines, embed_images=True)
    assert "data:image/png;base64,ABC11" in doc
    assert "https://x/1.png" not in doc  # replaced by the data URI


def test_easyread_embed_falls_back_to_url(monkeypatch):
    import clara.pictograms as pics
    monkeypatch.setattr(pics, "image_data_uri", lambda pid, size=300: None)
    lines = [{"text": "Water.", "keyword": "water", "image_url": "https://x/1.png", "pictogram_id": 11}]
    doc = document_html(kind="easyread", lines=lines, embed_images=True)
    assert "https://x/1.png" in doc  # unreachable image -> URL fallback


def test_easyread_default_uses_url_not_data():
    lines = [{"text": "Water.", "keyword": "water", "image_url": "https://x/1.png", "pictogram_id": 11}]
    doc = document_html(kind="easyread", lines=lines)  # embed_images defaults False
    assert "https://x/1.png" in doc
    assert "data:image" not in doc


def test_pdf_produces_pdf_or_raises_clearly():
    # Three valid states: WeasyPrint absent, present-but-missing-system-libs
    # (both -> a clear RuntimeError), or fully working (-> a real PDF).
    doc = document_html(kind="text", text="hello", title="t")
    try:
        out = document_pdf(doc)
    except RuntimeError as e:
        assert "WeasyPrint" in str(e)
    else:
        assert out[:4] == b"%PDF"
