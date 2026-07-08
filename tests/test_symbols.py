import pytest

from clara.pictograms import (
    ArasaacProvider,
    MulberryProvider,
    SymbolProvider,
    get_symbol_provider,
)

# --- registry -----------------------------------------------------------------

def test_default_provider_is_arasaac(monkeypatch):
    monkeypatch.delenv("CLARA_SYMBOLS", raising=False)
    assert get_symbol_provider().name == "arasaac"


def test_env_selects_provider(monkeypatch):
    monkeypatch.setenv("CLARA_SYMBOLS", "mulberry")
    assert isinstance(get_symbol_provider(), MulberryProvider)


def test_unknown_symbol_set_raises():
    with pytest.raises(ValueError, match="Unknown symbol set"):
        get_symbol_provider("crayon")


def test_providers_expose_license():
    assert "NC" in ArasaacProvider().license           # non-commercial
    assert ArasaacProvider().license != MulberryProvider().license  # Mulberry is BY-SA


# --- ARASAAC (offline bits only) ----------------------------------------------

def test_arasaac_image_url_shape():
    assert ArasaacProvider().image_url(2417).endswith("/2417/2417_300.png")


def test_arasaac_empty_keyword_is_none():
    assert ArasaacProvider().best("") is None


# --- Mulberry (matches the bundled index, no network) -------------------------

def test_mulberry_exact_match():
    m = MulberryProvider()
    for kw in ["house", "water", "car", "money", "food"]:
        s = m.best(kw)
        assert s is not None and s.provider == "mulberry"
        assert s.id == kw   # cleanest filename == the bare word


def test_mulberry_first_token_and_variants():
    m = MulberryProvider()
    assert m.best("help").id == "help_,_to"     # only a verb form exists
    assert m.best("doctor").id == "doctor_1a"   # no bare "doctor"; pick cleanest variant


def test_mulberry_no_match_is_soft():
    assert MulberryProvider().best("pay") is None   # not in the set -> None, not an error


def test_mulberry_search_ranks_exact_first():
    hits = MulberryProvider().search("car", limit=5)
    assert hits and hits[0].id == "car"             # exact leading-word match ranks first
    assert all(h.provider == "mulberry" for h in hits)


def test_mulberry_image_url_is_svg():
    m = MulberryProvider()
    assert m.image_url("house").endswith("/EN/house.svg")
    assert m.mimetype == "image/svg+xml"


def test_symbol_provider_is_abstract():
    with pytest.raises(TypeError):
        SymbolProvider()   # can't instantiate the interface directly
