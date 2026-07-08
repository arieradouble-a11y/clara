"""Golden-set regression guard for the faithfulness checker.

No model involved — this pins the behaviour of the deterministic `verify` layer
against known-good and known-bad rewrites, so a change to normalization or the
language data can't silently reintroduce a false positive (a faithful rewrite
flagged) or a false negative (a real drop/inversion missed).

Start small; grow it from real documents and bug reports. A faithful pair should
come back completely clean (ok, no warnings); an unfaithful pair must be caught
by *something* (a dropped/invented fact or a warning).
"""
import pytest

from clara.verify import verify

# fmt: off
FAITHFUL = [
    ("en", "date reformat", "You must pay 500 dollars by 2024-01-31.",
     "You must pay 500 dollars by 31 January 2024."),
    ("en", "number words", "Pay five hundred dollars.", "Pay 500 dollars."),
    ("en", "number words reverse", "The fee is 500 dollars.", "The fee is five hundred dollars."),
    ("en", "negation re-expressed", "It is not permitted to enter.", "Entry is forbidden."),
    ("en", "percent kept", "You get a 50% discount.", "You get a 50 percent discount."),
    ("en", "identifier kept", "Submit Form 27A by 2024-01-31.",
     "Send Form 27A by 31 January 2024."),
    ("ru", "date reformat", "Оплатите 500 рублей до 2024-01-31.",
     "Заплатите 500 рублей до 31 января 2024."),
    ("ru", "number words", "Штраф пятьсот рублей.", "Штраф 500 рублей."),
    ("es", "spanish date", "Pague 500 euros antes del 2024-01-31.",
     "Pague 500 euros antes del 31 de enero de 2024."),
    ("de", "german date", "Zahlen Sie 500 Euro bis 2024-01-31.",
     "Zahlen Sie 500 Euro bis zum 31. Januar 2024."),
]

UNFAITHFUL = [
    ("en", "dropped amount", "Pay 500 dollars by 2024-01-31.", "Pay by 2024-01-31."),
    ("en", "changed amount", "The fine is 500 dollars.", "The fine is 600 dollars."),
    ("en", "dropped date", "Apply before 2024-01-31.", "Apply soon."),
    ("en", "inverted negation", "You must not enter.", "You must enter."),
    ("en", "changed identifier", "Submit Form 27A.", "Submit Form 27B."),
    ("ru", "dropped amount", "Штраф 500 рублей.", "Штраф есть."),
    ("es", "dropped date", "Pague antes del 2024-01-31.", "Pague pronto."),
]
# fmt: on


def _clean(r) -> bool:
    return r.ok and not r.warnings


@pytest.mark.parametrize("lang,note,source,rewrite", FAITHFUL, ids=[f"{c[0]}-{c[1]}" for c in FAITHFUL])
def test_faithful_rewrites_are_clean(lang, note, source, rewrite):
    r = verify(source, rewrite, lang=lang)
    assert _clean(r), (
        f"false positive [{lang}: {note}] — dropped={r.dropped_quantities} "
        f"invented={r.invented_quantities} dates={r.dropped_dates}/{r.invented_dates} "
        f"ids={r.dropped_identifiers}/{r.invented_identifiers} warnings={r.warnings}"
    )


@pytest.mark.parametrize("lang,note,source,rewrite", UNFAITHFUL, ids=[f"{c[0]}-{c[1]}" for c in UNFAITHFUL])
def test_unfaithful_rewrites_are_caught(lang, note, source, rewrite):
    r = verify(source, rewrite, lang=lang)
    assert not _clean(r), f"missed a real change [{lang}: {note}]"
