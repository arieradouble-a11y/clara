import json
import os
import tempfile
from pathlib import Path

import pytest

from clara.board import board
from clara.easyread import ask
from clara.llm.base import MockProvider
from clara.pictograms import Symbol, SymbolProvider

# api.main creates its stores at import time; keep endpoint tests off the real DB.
os.environ.setdefault("CLARA_DB", os.path.join(tempfile.mkdtemp(), "reviews.db"))


class StubSymbols(SymbolProvider):
    """Maps a fixed set of keywords; records what was looked up."""
    name = "stub"

    def __init__(self, known=()):
        self.known = set(known)
        self.lookups: list[str] = []

    def best(self, keyword, lang="en"):
        self.lookups.append(keyword)
        if keyword in self.known:
            return Symbol(id=keyword, label=keyword, image_url=f"http://x/{keyword}.png", provider=self.name)
        return None

    def search(self, keyword, lang="en", limit=12):
        s = self.best(keyword, lang)
        return [s] if s else []

    def image_url(self, symbol_id, size=300):
        return f"http://x/{symbol_id}.png"


# --- board data sanity -----------------------------------------------------------

def test_every_word_has_all_five_labels():
    data = json.loads((Path(__file__).resolve().parent.parent
                       / "clara" / "data" / "board.json").read_text(encoding="utf-8"))
    langs = {"en", "ru", "es", "de", "fr"}
    for cat in data["categories"]:
        assert langs <= set(cat["label"]), f"category {cat['id']} misses labels"
        for w in cat["words"]:
            assert langs <= set(w["label"]), f"word {w['key']} misses labels"


# --- board() ----------------------------------------------------------------------

def test_board_structure_and_localized_labels():
    b = board(lang="ru", symbols=StubSymbols())
    assert b["lang"] == "ru" and b["symbols"] == "stub"
    cats = b["categories"]
    assert len(cats) >= 5
    people = next(c for c in cats if c["id"] == "people")
    assert people["label"] == "Люди"
    labels = [w["label"] for w in people["words"]]
    assert "я" in labels and "врач" in labels          # localized, not English


def test_board_unknown_language_falls_back_to_english():
    b = board(lang="xx", symbols=StubSymbols())
    people = next(c for c in b["categories"] if c["id"] == "people")
    assert people["label"] == "People"


def test_board_words_without_pictures_stay_tappable():
    b = board(lang="en", symbols=StubSymbols(known={"water"}))
    things = next(c for c in b["categories"] if c["id"] == "things")
    by_key = {w["key"]: w for w in things["words"]}
    assert by_key["water"]["image_url"] == "http://x/water.png"
    assert by_key["letter"]["image_url"] is None       # no picture, still a tile
    assert by_key["letter"]["label"] == "letter"


def test_board_falls_back_to_english_keyword():
    # ru label misses, en concept hits -> the tile still gets a picture.
    stub = StubSymbols(known={"water"})
    b = board(lang="ru", symbols=stub)
    things = next(c for c in b["categories"] if c["id"] == "things")
    water = next(w for w in things["words"] if w["key"] == "water")
    assert water["label"] == "вода"                    # label stays localized
    assert water["image_url"] == "http://x/water.png"  # picture via en fallback
    assert "вода" in stub.lookups and "water" in stub.lookups


def test_board_with_mulberry_is_fully_offline():
    # Mulberry matches its bundled English index — no network at all.
    b = board(lang="ru", symbols="mulberry")
    assert b["symbols"] == "mulberry"
    things = next(c for c in b["categories"] if c["id"] == "things")
    water = next(w for w in things["words"] if w["key"] == "water")
    assert water["label"] == "вода"
    assert water["image_url"] and water["image_url"].endswith("/EN/water.svg")


# --- ask() ------------------------------------------------------------------------

def test_ask_echo_roundtrip():
    # Mock echoes the question as the answer; the answer then flows through
    # easy_read, so lines + faithfulness come back like any Easy Read result.
    res = ask("я хотеть понять письмо", provider=MockProvider(), lang="ru",
              symbols=StubSymbols())
    assert res.original == "я хотеть понять письмо"
    assert res.lines and res.lines[0].text == "я хотеть понять письмо"
    assert res.faithfulness.ok


def test_ask_lines_get_pictograms():
    res = ask("what is water", provider=MockProvider(response="Water is a drink."),
              lang="en", symbols=StubSymbols(known={"water"}))
    assert res.original == "Water is a drink."
    assert res.lines[0].keyword == "water"
    assert res.lines[0].pictogram_id == "water"


# --- HTTP endpoints -----------------------------------------------------------------

fastapi = pytest.importorskip("fastapi")


@pytest.fixture()
def client(monkeypatch):
    from fastapi.testclient import TestClient

    import api.main as api_main
    monkeypatch.setenv("CLARA_PROVIDER", "mock")
    return TestClient(api_main.app)


def test_endpoint_board_offline_with_mulberry(client):
    r = client.get("/board", params={"lang": "ru", "symbols": "mulberry"})
    assert r.status_code == 200
    d = r.json()
    assert d["lang"] == "ru"
    assert any(c["id"] == "questions" for c in d["categories"])


def test_endpoint_ask(client):
    r = client.post("/ask", json={"text": "я хотеть понять письмо", "lang": "ru",
                                  "symbols": "mulberry"})
    assert r.status_code == 200
    d = r.json()
    assert d["question"] == "я хотеть понять письмо"
    assert d["original"] == "я хотеть понять письмо"   # mock echo
    assert d["lines"] and d["faithfulness"]["ok"] is True
