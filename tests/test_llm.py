import pytest

from clara.llm import MockProvider, get_check_provider, get_provider


def test_default_provider_is_mock(monkeypatch):
    monkeypatch.delenv("CLARA_PROVIDER", raising=False)
    assert isinstance(get_provider(), MockProvider)


def test_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unknown provider"):
        get_provider("nope")


def test_check_provider_falls_back_to_default(monkeypatch):
    # No CLARA_CHECK_PROVIDER set -> same default as the simplifier (mock).
    monkeypatch.delenv("CLARA_CHECK_PROVIDER", raising=False)
    monkeypatch.delenv("CLARA_PROVIDER", raising=False)
    assert isinstance(get_check_provider(), MockProvider)


def test_check_provider_prefers_its_own_env(monkeypatch):
    # An independent grader is configured; the simplifier stays on mock.
    monkeypatch.setenv("CLARA_PROVIDER", "mock")
    monkeypatch.setenv("CLARA_CHECK_PROVIDER", "ollama")
    checker = get_check_provider()
    assert checker.__class__.__name__ == "OllamaProvider"  # not the mock simplifier


def test_check_provider_explicit_name_wins(monkeypatch):
    monkeypatch.setenv("CLARA_CHECK_PROVIDER", "ollama")
    # An explicit argument overrides the env.
    assert get_check_provider("mock").__class__.__name__ == "MockProvider"
