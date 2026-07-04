from clara.readability import analyze, count_syllables


def test_simpler_text_lower_grade():
    hard = analyze("The aforementioned stipulations necessitate comprehensive reconsideration.")
    easy = analyze("You must think again. This is important.")
    assert easy.flesch_kincaid_grade < hard.flesch_kincaid_grade
    assert easy.flesch_reading_ease > hard.flesch_reading_ease


def test_empty_text_is_safe():
    r = analyze("")
    assert r.words == 0
    assert r.flesch_kincaid_grade == 0.0


def test_syllables():
    assert count_syllables("cat") == 1
    assert count_syllables("simple") == 2  # silent trailing e dropped from 3 groups
    assert count_syllables("readability") >= 4
