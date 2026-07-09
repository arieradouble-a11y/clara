import json
import os
import tempfile

import pytest

from clara.llm.base import LLMProvider, MockProvider
from clara.profile import (
    EXAMPLE_PROFILE,
    load_profile,
    proxy_options,
    reading_notes,
    render_instructions,
    validate_profile,
)
from clara.proxy import proxy_chat

# api.main creates its stores at import time; keep endpoint tests off the real DB.
os.environ.setdefault("CLARA_DB", os.path.join(tempfile.mkdtemp(), "reviews.db"))


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in ("CLARA_PROVIDER", "CLARA_PROFILE", "CLARA_PROXY_LEVEL",
                "CLARA_PROXY_GRADE", "CLARA_PROXY_LANG", "CLARA_PROXY_ANNOTATE"):
        monkeypatch.delenv(var, raising=False)


class Capture(LLMProvider):
    """Records what it was asked, answers a canned string."""

    def __init__(self, response="The answer."):
        self.response = response
        self.system: str | None = None
        self.messages: list | None = None

    def complete(self, system, prompt, *, max_tokens=2000, temperature=0.2):
        self.system = system
        return self.response

    def chat(self, messages, *, max_tokens=2000, temperature=0.2):
        self.messages = messages
        return self.response


# --- validation ---------------------------------------------------------------

def test_example_profile_is_valid():
    assert validate_profile(EXAMPLE_PROFILE) == []


def test_version_is_required():
    assert any("a11y_profile" in e for e in validate_profile({}))


def test_bad_values_are_reported():
    errs = validate_profile({
        "a11y_profile": "0.1",
        "reading": {"level": "simple", "grade": 0, "max_sentence_words": True},
        "format": {"avoid_tables": "yes"},
    })
    joined = " | ".join(errs)
    assert "reading.level" in joined
    assert "reading.grade" in joined
    assert "max_sentence_words" in joined
    assert "format.avoid_tables" in joined


def test_unknown_fields_are_ignored():
    # Forward compatibility: a newer profile degrades, never breaks.
    assert validate_profile({"a11y_profile": "0.9", "haptics": {"strength": 3},
                             "reading": {"level": "plain", "font": "large"}}) == []


def test_non_object_is_rejected():
    assert validate_profile(["not", "a", "profile"]) == ["profile must be a JSON object"]


# --- rendering (Mode A) ---------------------------------------------------------

def test_render_full_profile():
    text = render_instructions(EXAMPLE_PROFILE)
    assert text.startswith("ACCESSIBILITY PROFILE")
    assert "Easy Read" in text
    assert "under 15 words" in text
    assert "Do not use tables" in text
    assert "Always answer in English." in text


def test_render_without_reading_keeps_format_only():
    text = render_instructions(EXAMPLE_PROFILE, include_reading=False)
    assert "Do not use tables" in text
    assert "Easy Read" not in text and "under 15 words" not in text


def test_render_empty_profile_is_empty():
    assert render_instructions({"a11y_profile": "0.1"}) == ""


def test_render_grade_level_and_unknown_language():
    text = render_instructions({"a11y_profile": "0.1", "language": "uk",
                                "reading": {"level": "grade", "grade": 4}})
    assert "grade 4 reading level" in text
    assert "Always answer in uk." in text          # unknown code passes through


def test_reading_notes():
    notes = reading_notes(EXAMPLE_PROFILE)
    assert "- Keep every sentence under 15 words." in notes
    assert "one sentence per line" in notes


# --- mapping (Mode B) -------------------------------------------------------------

def test_proxy_options_mapping():
    assert proxy_options(EXAMPLE_PROFILE) == {"level": "easy_read", "lang": "en", "annotate": True}
    assert proxy_options({"a11y_profile": "0.1", "verify": {"warn_inline": False}}) == {"annotate": False}
    # facts:false means no fact wish at all -> never annotate either
    assert proxy_options({"a11y_profile": "0.1",
                          "verify": {"facts": False, "warn_inline": True}}) == {"annotate": False}
    assert proxy_options({"a11y_profile": "0.1"}) == {}


# --- file loading -----------------------------------------------------------------

def test_load_profile_roundtrip(tmp_path):
    p = tmp_path / "profile.json"
    p.write_text(json.dumps(EXAMPLE_PROFILE), encoding="utf-8")
    assert load_profile(p)["reading"]["level"] == "easy_read"


def test_load_profile_rejects_invalid(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"reading": {"level": "wat"}}), encoding="utf-8")
    with pytest.raises(ValueError, match="a11y_profile"):
        load_profile(p)


# --- proxy integration --------------------------------------------------------------

def test_inline_profile_sets_level_and_flag():
    res = proxy_chat([{"role": "user", "content": "Hello."}], provider=MockProvider(),
                     options={"profile": EXAMPLE_PROFILE})
    assert res.level == "easy_read"
    assert res.lang == "en"
    assert res.profile_applied is True


def test_no_profile_flag_is_false():
    res = proxy_chat([{"role": "user", "content": "Hello."}], provider=MockProvider())
    assert res.profile_applied is False


def test_flat_option_beats_profile():
    res = proxy_chat([{"role": "user", "content": "Hello."}], provider=MockProvider(),
                     options={"level": "plain", "profile": EXAMPLE_PROFILE})
    assert res.level == "plain"


def test_model_name_beats_profile():
    # An active model-picker choice outranks the standing profile.
    res = proxy_chat([{"role": "user", "content": "Hello."}], provider=MockProvider(),
                     model="clara-grade-7", options={"profile": EXAMPLE_PROFILE})
    assert res.level == "grade" and res.grade == 7


def test_invalid_inline_profile_raises():
    with pytest.raises(ValueError, match="Invalid accessibility profile"):
        proxy_chat([{"role": "user", "content": "Hi"}], provider=MockProvider(),
                   options={"profile": {"reading": {"level": "wat"}}})


def test_format_wishes_injected_upstream_reading_kept_out():
    upstream = Capture()
    proxy_chat([{"role": "system", "content": "You are a helper."},
                {"role": "user", "content": "Hello."}],
               provider=upstream, simplifier=MockProvider(),
               options={"profile": EXAMPLE_PROFILE})
    assert upstream.messages is not None
    roles = [m["role"] for m in upstream.messages]
    assert roles == ["system", "system", "user"]        # after the client's setup
    injected = upstream.messages[1]["content"]
    assert "ACCESSIBILITY PROFILE" in injected
    assert "Do not use tables" in injected
    assert "Easy Read" not in injected                  # reading is the pipeline's job


def test_reading_constraints_reach_the_simplifier():
    simplifier = Capture(response="Short answer.")
    proxy_chat([{"role": "user", "content": "Hello."}],
               provider=MockProvider(response="A long answer."), simplifier=simplifier,
               options={"profile": EXAMPLE_PROFILE})
    assert simplifier.system is not None
    assert "READER PROFILE" in simplifier.system
    assert "under 15 words" in simplifier.system


def test_env_profile_applies(tmp_path, monkeypatch):
    p = tmp_path / "profile.json"
    p.write_text(json.dumps(EXAMPLE_PROFILE), encoding="utf-8")
    monkeypatch.setenv("CLARA_PROFILE", str(p))
    res = proxy_chat([{"role": "user", "content": "Hello."}], provider=MockProvider())
    assert res.level == "easy_read" and res.profile_applied


def test_broken_env_profile_fails_loudly(tmp_path, monkeypatch):
    p = tmp_path / "broken.json"
    p.write_text("{not json", encoding="utf-8")
    monkeypatch.setenv("CLARA_PROFILE", str(p))
    with pytest.raises(RuntimeError, match="CLARA_PROFILE"):
        proxy_chat([{"role": "user", "content": "Hello."}], provider=MockProvider())


# --- CLI ----------------------------------------------------------------------------

def test_cli_profile_workflow(tmp_path, capsys):
    from clara.cli import main

    assert main(["profile", "example"]) == 0
    example = capsys.readouterr().out
    p = tmp_path / "profile.json"
    p.write_text(example, encoding="utf-8")

    assert main(["profile", "check", "--file", str(p)]) == 0
    assert "valid" in capsys.readouterr().out

    assert main(["profile", "render", "--file", str(p)]) == 0
    assert "ACCESSIBILITY PROFILE" in capsys.readouterr().out


def test_cli_profile_check_rejects_bad_file(tmp_path, capsys):
    from clara.cli import main

    p = tmp_path / "bad.json"
    p.write_text('{"reading": {"level": "wat"}}', encoding="utf-8")
    assert main(["profile", "check", "--file", str(p)]) == 1
    assert "a11y_profile" in capsys.readouterr().err


# --- HTTP endpoint --------------------------------------------------------------------

fastapi = pytest.importorskip("fastapi")


def test_endpoint_accepts_inline_profile(monkeypatch):
    from fastapi.testclient import TestClient

    import api.main as api_main
    monkeypatch.setenv("CLARA_PROVIDER", "mock")
    client = TestClient(api_main.app)
    r = client.post("/v1/chat/completions", json={
        "messages": [{"role": "user", "content": "Pay 500 by 2024-01-31."}],
        "clara": {"profile": EXAMPLE_PROFILE},
    })
    assert r.status_code == 200
    d = r.json()
    assert d["clara"]["level"] == "easy_read"
    assert d["clara"]["profile_applied"] is True


def test_endpoint_rejects_invalid_profile(monkeypatch):
    from fastapi.testclient import TestClient

    import api.main as api_main
    monkeypatch.setenv("CLARA_PROVIDER", "mock")
    client = TestClient(api_main.app)
    r = client.post("/v1/chat/completions", json={
        "messages": [{"role": "user", "content": "Hi"}],
        "clara": {"profile": {"reading": {"level": "wat"}}},
    })
    assert r.status_code == 400
    assert "profile" in r.json()["error"]["message"]
