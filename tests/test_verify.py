from clara.verify import verify


def test_clean_passes():
    r = verify("Pay 500 by 2024-01-01.", "Pay 500 by 2024-01-01.")
    assert r.ok
    assert not r.warnings


def test_dropped_number_flagged():
    r = verify("You must pay 500 by 2024-01-01.", "You must pay by 2024-01-01.")
    assert "500" in r.dropped_quantities
    assert not r.ok


def test_invented_number_flagged():
    r = verify("Pay the fee.", "Pay the 500 fee.")
    assert "500" in r.invented_quantities
    assert not r.ok


def test_dropped_date_flagged():
    r = verify("Apply before 2024-01-31.", "Apply before the deadline.")
    assert "2024-01-31" in r.dropped_dates
    assert not r.ok


def test_reformatted_date_still_matches():
    # Model rewrote the ISO date as a month name — same date, must NOT be flagged.
    r = verify("Apply before 2024-01-31.", "Apply before January 31, 2024.")
    assert r.ok


def test_number_words_match_digits_both_directions():
    assert verify("Pay five hundred dollars by 2024-01-31.", "Pay 500 dollars by 2024-01-31.").ok
    assert verify("The fine is 500 dollars.", "The fine is five hundred dollars.").ok


def test_changed_identifier_is_caught():
    r = verify("Submit Form 27A.", "Submit Form 27B.")
    assert not r.ok
    assert r.dropped_identifiers == ["27a"] and r.invented_identifiers == ["27b"]


def test_same_identifier_is_clean():
    r = verify("Submit Form 27A by 2024-01-31.", "Send Form 27A by 31 January 2024.")
    assert r.ok and not r.dropped_identifiers and not r.invented_identifiers


def test_reexpressed_negation_does_not_warn():
    # "not permitted" -> "forbidden" keeps the meaning; don't cry lost negation.
    r = verify("It is not permitted to smoke here.", "Smoking is forbidden here.")
    assert not r.warnings


def test_lost_negation_warns_but_hard_facts_ok():
    r = verify("You must not enter.", "You must enter.")
    assert r.ok  # no numbers/dates changed
    assert r.warnings  # but meaning may be inverted -> human review
