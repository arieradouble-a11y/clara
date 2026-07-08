from clara.i18n import ui_strings

_PLACEHOLDER_KEYS = {"search_symbols_ph": "{set}", "no_symbols_for": "{q}", "versions_n": "{n}"}


def test_english_is_present():
    d = ui_strings()
    assert "en" in d and len(d["en"]) > 50


def test_all_languages_have_the_same_keys():
    d = ui_strings()
    en = set(d["en"])
    for lang, strings in d.items():
        assert set(strings) == en, f"{lang} keys differ from en: {en ^ set(strings)}"


def test_no_empty_strings():
    for lang, strings in ui_strings().items():
        for key, val in strings.items():
            assert val.strip(), f"{lang}.{key} is empty"


def test_placeholders_preserved_in_every_language():
    # Interpolated keys must keep their {token} in every translation, or the
    # runtime substitution silently drops the value.
    for lang, strings in ui_strings().items():
        for key, token in _PLACEHOLDER_KEYS.items():
            assert token in strings[key], f"{lang}.{key} lost {token}"


def test_private_keys_excluded():
    assert not any(k.startswith("_") for k in ui_strings())  # _note is stripped


def test_next_app_bundled_catalog_matches_source():
    # The Next app bundles a copy for an instant, offline-safe first render; it
    # must stay byte-identical to the canonical catalog.
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    src = json.loads((root / "clara" / "data" / "ui_i18n.json").read_text(encoding="utf-8"))
    bundled_path = root / "web-next" / "lib" / "ui_i18n.json"
    if not bundled_path.exists():
        import pytest
        pytest.skip("web-next not present")
    bundled = json.loads(bundled_path.read_text(encoding="utf-8"))
    assert bundled == src, "web-next/lib/ui_i18n.json drifted from clara/data/ui_i18n.json"
