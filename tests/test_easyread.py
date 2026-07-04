import clara.easyread as er
from clara.easyread import _keywords, _split_lines, easy_read
from clara.llm.base import MockProvider


def test_keywords_skip_stopwords():
    kws = _keywords("You must pay the fine.")
    assert "pay" in kws and "fine" in kws
    assert "you" not in kws and "the" not in kws and "must" not in kws


def test_split_lines_from_sentences():
    assert _split_lines("You must pay. Do it by Friday.") == ["You must pay.", "Do it by Friday."]


def test_split_lines_prefers_existing_breaks():
    assert _split_lines("Line one.\nLine two.\n\nLine three.") == [
        "Line one.", "Line two.", "Line three.",
    ]


def test_easy_read_attaches_pictogram(monkeypatch):
    monkeypatch.setattr(er, "best_id", lambda kw, lang="en": 123 if kw == "pay" else None)
    res = easy_read("You must pay 500 by 2024-01-01.", provider=MockProvider())
    assert res.faithfulness.ok  # mock echoes source -> nothing dropped
    assert res.lines[0].pictogram_id == 123
    assert "123" in res.lines[0].image_url
    assert res.lines[0].keyword == "pay"


def test_easy_read_degrades_without_pictograms(monkeypatch):
    monkeypatch.setattr(er, "best_id", lambda *a, **k: None)  # simulate ARASAAC down/no match
    res = easy_read("Pay the fine.", provider=MockProvider())
    assert res.lines[0].text == "Pay the fine."
    assert res.lines[0].pictogram_id is None  # still fine, just no image


def test_easy_read_can_skip_network():
    res = easy_read("Pay the fine.", provider=MockProvider(), with_pictograms=False)
    assert all(ln.pictogram_id is None for ln in res.lines)
