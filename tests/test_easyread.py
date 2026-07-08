from clara.easyread import _keywords, _split_lines, easy_read
from clara.llm.base import MockProvider
from clara.pictograms import Symbol, SymbolProvider


class StubSymbols(SymbolProvider):
    """A symbol set with a fixed keyword->id map, so tests need no network."""
    name = "stub"

    def __init__(self, mapping):
        self.mapping = mapping

    def best(self, keyword, lang="en"):
        pid = self.mapping.get(keyword)
        return Symbol(id=pid, label=keyword, image_url=f"http://x/{pid}.png", provider=self.name) if pid else None

    def search(self, keyword, lang="en", limit=12):
        s = self.best(keyword, lang)
        return [s] if s else []

    def image_url(self, symbol_id, size=300):
        return f"http://x/{symbol_id}.png"


def test_keywords_skip_stopwords():
    kws = _keywords("You must pay the fine.")
    assert "pay" in kws and "fine" in kws
    assert "you" not in kws and "the" not in kws and "must" not in kws


def test_keywords_prefer_nouns_over_modifiers():
    # "large" is a generic modifier (soft stopword) -> demoted below the noun.
    kws = _keywords("Pay the large fine.")
    assert kws.index("fine") < kws.index("large")
    assert kws[0] == "pay"  # the verb keeps its lead over the adjective


def test_picks_noun_not_leading_modifier():
    # Only "fine" has a symbol; selection must reach it past the earlier "large".
    res = easy_read("A large fine is due.", provider=MockProvider(),
                    symbols=StubSymbols({"fine": 42, "large": 7}))
    # Both have symbols here, but the noun outranks the modifier.
    assert res.lines[0].keyword == "fine"
    assert res.lines[0].pictogram_id == 42


def test_split_lines_from_sentences():
    assert _split_lines("You must pay. Do it by Friday.") == ["You must pay.", "Do it by Friday."]


def test_split_lines_prefers_existing_breaks():
    assert _split_lines("Line one.\nLine two.\n\nLine three.") == [
        "Line one.", "Line two.", "Line three.",
    ]


def test_easy_read_attaches_pictogram():
    res = easy_read("You must pay 500 by 2024-01-01.", provider=MockProvider(),
                    symbols=StubSymbols({"pay": 123}))
    assert res.faithfulness.ok  # mock echoes source -> nothing dropped
    assert res.lines[0].pictogram_id == 123
    assert "123" in res.lines[0].image_url
    assert res.lines[0].keyword == "pay"
    assert res.lines[0].symbol_source == "stub"
    assert res.symbol_source == "stub"


def test_easy_read_degrades_without_pictograms():
    res = easy_read("Pay the fine.", provider=MockProvider(),
                    symbols=StubSymbols({}))  # simulate the set down / no match
    assert res.lines[0].text == "Pay the fine."
    assert res.lines[0].pictogram_id is None  # still fine, just no image


def test_easy_read_can_skip_network():
    res = easy_read("Pay the fine.", provider=MockProvider(), with_pictograms=False)
    assert all(ln.pictogram_id is None for ln in res.lines)
