import pytest

from clara.facts import extract_dates, inventory
from clara.lang import available, get_pack
from clara.readability import analyze
from clara.verify import verify


def test_available_packs():
    assert set(available()) >= {"en", "ru", "es", "de", "fr"}


@pytest.mark.parametrize("lang", ["es", "de", "fr"])
def test_new_packs_reading_ease_no_grade(lang):
    import clara.readability as rd
    texts = {
        "es": "Los inquilinos deben pagar antes del 10 de enero de 2024.",
        "de": "Die Mieter müssen bis zum 10. Januar 2024 zahlen.",
        "fr": "Les locataires doivent payer avant le 10 janvier 2024.",
    }
    r = rd.analyze(texts[lang], lang=lang)
    assert r.words > 0
    assert isinstance(r.flesch_reading_ease, float)
    assert r.flesch_kincaid_grade is None  # no validated grade formula shipped


def test_group_vowel_syllables():
    # Diphthongs count as one syllable (group counting), unlike Russian.
    assert get_pack("es").syllables("aire") == 2      # ai-re
    assert get_pack("fr").syllables("maison") == 2    # mai-son
    assert get_pack("de").syllables("Haus") == 1      # single vowel group


def test_localized_date_and_markers():
    from clara.facts import extract_dates, inventory
    dates, _ = extract_dates("Pagar antes del 10 de enero de 2024.", lang="es")
    assert "2024-01-10" in dates
    de = inventory("Die Mieter müssen nicht zahlen.", lang="de")
    assert de["negation"] >= 1 and de["obligation"] >= 1
    fr = inventory("Les locataires ne doivent pas entrer.", lang="fr")
    assert fr["negation"] >= 1 and fr["obligation"] >= 1


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


@pytest.mark.parametrize("lang,word,base", [
    ("es", "casas", "casa"),
    ("de", "Häuser", "Haus"),
    ("fr", "maisons", "maison"),
])
def test_latin_lemmatize(lang, word, base):
    pytest.importorskip("simplemma")
    assert get_pack(lang).lemmatize(word) == base


def test_latin_lemmatize_soft_fails(monkeypatch):
    pytest.importorskip("simplemma")
    import simplemma

    def boom(*a, **k):
        raise RuntimeError("simulated")

    monkeypatch.setattr(simplemma, "lemmatize", boom)
    assert get_pack("de").lemmatize("Häuser") == "Häuser"  # falls back to the raw word


def test_easyread_looks_up_lemma(monkeypatch):
    from clara.easyread import easy_read
    from clara.llm.base import MockProvider
    from clara.pictograms import Symbol, SymbolProvider

    pack = get_pack("ru")
    monkeypatch.setattr(pack, "lemmatize", lambda w: "вода" if w == "воду" else w)
    seen = []

    class SeenSymbols(SymbolProvider):
        name = "stub"

        def best(self, keyword, lang="en"):
            seen.append(keyword)
            return Symbol(111, keyword, "http://x/111.png", self.name) if keyword == "вода" else None

        def search(self, keyword, lang="en", limit=12):
            return []

        def image_url(self, symbol_id, size=300):
            return f"http://x/{symbol_id}.png"

    res = easy_read("Закройте воду.", provider=MockProvider(), lang="ru", symbols=SeenSymbols())
    assert "вода" in seen  # the symbol set was queried with the lemma, not "воду"
    assert res.lines[0].pictogram_id == 111
    assert res.lines[0].keyword == "вода"
