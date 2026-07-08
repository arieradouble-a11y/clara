from clara.llm.base import MockProvider
from clara.pipeline import simplify_text
from clara.serialize import faithfulness_dict, readability_dict, result_dict
from clara.verify import verify


def test_result_dict_shape():
    res = simplify_text("Pay 500 by 2024-01-01.", provider=MockProvider())
    d = result_dict(res)
    assert set(d) == {
        "level", "original", "simplified", "source_readability",
        "output_readability", "faithfulness",
    }
    assert set(d["faithfulness"]) == {
        "ok", "dropped_quantities", "invented_quantities",
        "dropped_dates", "invented_dates",
        "dropped_identifiers", "invented_identifiers", "warnings",
    }
    assert d["faithfulness"]["ok"] is True


def test_faithfulness_dict_flags_drop():
    d = faithfulness_dict(verify("Pay 500.", "Pay."))
    assert d["ok"] is False
    assert "500" in d["dropped_quantities"]


def test_readability_dict_keys():
    from clara.readability import analyze
    d = readability_dict(analyze("A short sentence."))
    assert set(d) == {"words", "sentences", "flesch_reading_ease", "flesch_kincaid_grade"}
