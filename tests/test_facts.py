from clara.facts import extract_dates, extract_identifiers, extract_quantities, inventory


def test_numbers_and_dates():
    inv = inventory("Pay 1,200 dollars by 2024-01-31.")
    assert inv["quantities"]["1200"] == 1
    assert inv["dates"]["2024-01-31"] == 1


def test_iso_and_month_name_normalize_equal():
    a, _ = extract_dates("Due 2024-01-31.")
    b, _ = extract_dates("Due January 31, 2024.")
    assert a == b == ["2024-01-31"]


def test_percent_normalizes():
    assert "50%" in extract_quantities("A 50% discount")
    assert "50%" in extract_quantities("A 50 percent discount")


def test_currency_symbol():
    assert "$1000" in extract_quantities("The fine is $1,000.")


def test_year_inside_date_not_counted_as_quantity():
    inv = inventory("The deadline is 2024-01-31.")
    assert inv["quantities"] == {}  # 2024 / 01 / 31 belong to the date, not quantities


def test_number_words_become_digits():
    assert "500" in inventory("Pay five hundred dollars.")["quantities"]


def test_number_words_hyphenated():
    assert "23" in inventory("There are twenty-three items.")["quantities"]


def test_bare_small_number_word_is_not_a_quantity():
    # "one" in prose is not an amount — don't invent a quantity from it.
    assert inventory("Give me one moment.")["quantities"] == {}


def test_russian_number_word():
    assert "500" in inventory("Штраф пятьсот рублей.", lang="ru")["quantities"]


def test_identifiers_captured():
    assert extract_identifiers("Submit Form 27A and Section 12B.") == ["27a", "12b"]
    assert extract_identifiers("Use Model X1 on A4 paper.") == ["x1", "a4"]


def test_identifiers_exclude_ordinals_units_and_formats():
    # The tokens a naive rule wrongly grabs — all excluded (no uppercase / ordinal).
    for text in ["the 2nd form", "save as mp3", "weighs 5kg", "100km away", "runs 24h"]:
        assert extract_identifiers(text) == [], text


def test_identifier_number_part_still_counts_as_quantity():
    # "27A" keeps its "27" as a quantity (so a faithful copy stays clean) AND
    # surfaces the whole id (so a changed suffix is catchable).
    inv = inventory("Form 27A")
    assert inv["quantities"]["27"] == 1
    assert inv["identifiers"]["27a"] == 1


def test_negation_and_obligation_counted():
    inv = inventory("You must not enter unless you have a permit.")
    assert inv["negation"] >= 1
    assert inv["obligation"] >= 1
    assert inv["condition"] >= 1
