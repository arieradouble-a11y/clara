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
