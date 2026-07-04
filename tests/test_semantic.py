from clara.llm.base import MockProvider
from clara.semantic import semantic_check


def test_reports_issues_from_json():
    resp = '{"faithful": false, "issues": [{"type": "omission", "detail": "dropped the fee"}]}'
    r = semantic_check("Pay $500.", "Pay.", provider=MockProvider(response=resp))
    assert r.available
    assert r.faithful is False
    assert r.issues[0].type == "omission"
    assert "fee" in r.issues[0].detail


def test_faithful_when_no_issues():
    resp = '{"faithful": true, "issues": []}'
    r = semantic_check("Pay $500.", "Pay 500 dollars.", provider=MockProvider(response=resp))
    assert r.available and r.faithful and not r.issues


def test_issues_force_not_faithful_even_if_model_says_true():
    resp = '{"faithful": true, "issues": [{"type": "distortion", "detail": "weaker"}]}'
    r = semantic_check("a", "b", provider=MockProvider(response=resp))
    assert r.available and r.faithful is False


def test_tolerates_code_fence_and_prose():
    resp = 'Here is my analysis:\n```json\n{"faithful": true, "issues": []}\n```'
    r = semantic_check("a", "a", provider=MockProvider(response=resp))
    assert r.available and r.faithful


def test_unavailable_on_non_json():
    r = semantic_check("a", "a", provider=MockProvider(response="not json at all"))
    assert not r.available
    assert r.faithful is None


def test_unavailable_on_echo_mock():
    # The default mock echoes the prompt -> no usable JSON -> degrade gracefully.
    r = semantic_check("Pay $500.", "Pay.", provider=MockProvider())
    assert not r.available
