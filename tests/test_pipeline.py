from clara.llm.base import MockProvider
from clara.pipeline import simplify_text


def test_echo_is_faithful():
    # MockProvider echoes the source, so nothing is dropped or invented.
    res = simplify_text("Pay 500 by 2024-01-01.", provider=MockProvider())
    assert res.faithfulness.ok


def test_dropped_fact_is_caught():
    bad = MockProvider(response="Pay by 2024-01-01.")  # dropped the amount
    res = simplify_text("Pay 500 by 2024-01-01.", provider=bad)
    assert "500" in res.faithfulness.dropped_quantities
    assert not res.faithfulness.ok


def test_levels_build_without_error():
    for level in ("plain", "easy_read", "grade"):
        res = simplify_text("You must apply.", level=level, provider=MockProvider())
        assert res.level == level
