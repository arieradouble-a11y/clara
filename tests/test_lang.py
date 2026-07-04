from clara.facts import extract_dates, inventory
from clara.lang import available, get_pack
from clara.readability import analyze
from clara.verify import verify


def test_available_packs():
    assert set(available()) >= {"en", "ru"}


def test_english_still_reports_grade():
    r = analyze("You must pay the fine.", lang="en")
    assert r.flesch_kincaid_grade is not None


def test_russian_reading_ease_and_no_grade():
    r = analyze("Заявитель должен подать заявление до 31 января 2024 года.", lang="ru")
    assert r.words > 0
    assert isinstance(r.flesch_reading_ease, float)
    assert r.flesch_kincaid_grade is None  # no validated Russian grade formula ships


def test_russian_syllables_count_vowels():
    pack = get_pack("ru")
    assert pack.syllables("молоко") == 3
    assert pack.syllables("дом") == 1


def test_russian_date_extraction():
    dates, _ = extract_dates("Оплатить до 31 января 2024.", lang="ru")
    assert "2024-01-31" in dates


def test_russian_negation_and_obligation():
    inv = inventory("Жильцы не должны открывать кран.", lang="ru")
    assert inv["negation"] >= 1
    assert inv["obligation"] >= 1


def test_russian_verify_flags_dropped_number():
    r = verify("Штраф 500 рублей до 2024-01-31.", "Штраф до 2024-01-31.", lang="ru")
    assert "500" in r.dropped_quantities
    assert not r.ok


def test_unknown_lang_raises():
    import pytest
    with pytest.raises(ValueError):
        get_pack("xx")


def test_english_lemmatize_is_identity():
    assert get_pack("en").lemmatize("running") == "running"


def test_russian_lemmatize_base_form():
    import pytest
    pytest.importorskip("pymorphy3")
    assert get_pack("ru").lemmatize("воду") == "вода"
    assert get_pack("ru").lemmatize("рублей") == "рубль"


def test_easyread_looks_up_lemma(monkeypatch):
    import clara.easyread as er
    from clara.easyread import easy_read
    from clara.llm.base import MockProvider

    pack = get_pack("ru")
    monkeypatch.setattr(pack, "lemmatize", lambda w: "вода" if w == "воду" else w)
    seen = []

    def fake_best_id(kw, lang="ru"):
        seen.append(kw)
        return 111 if kw == "вода" else None

    monkeypatch.setattr(er, "best_id", fake_best_id)
    res = easy_read("Закройте воду.", provider=MockProvider(), lang="ru")
    assert "вода" in seen  # ARASAAC was queried with the lemma, not "воду"
    assert res.lines[0].pictogram_id == 111
    assert res.lines[0].keyword == "вода"
