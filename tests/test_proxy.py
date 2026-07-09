import os
import tempfile

import pytest

from clara.llm.base import MockProvider
from clara.proxy import (
    ProxyResult,
    completion_response,
    models_response,
    parse_model,
    proxy_chat,
    stream_events,
)

# api.main creates its stores at import time; point them at a temp DB so the
# endpoint tests never touch the developer's real ~/.clara/reviews.db.
os.environ.setdefault("CLARA_DB", os.path.join(tempfile.mkdtemp(), "reviews.db"))


@pytest.fixture(autouse=True)
def _clean_proxy_env(monkeypatch):
    for var in ("CLARA_PROVIDER", "CLARA_PROXY_LEVEL", "CLARA_PROXY_GRADE",
                "CLARA_PROXY_LANG", "CLARA_PROXY_ANNOTATE"):
        monkeypatch.delenv(var, raising=False)


# --- model-name routing ---------------------------------------------------------

def test_parse_model_levels():
    assert parse_model("clara-plain") == ("plain", None)
    assert parse_model("clara-easy-read") == ("easy_read", None)
    assert parse_model("Clara-Grade-7") == ("grade", 7)
    assert parse_model("gpt-4o-mini") == (None, None)   # unknown -> env default
    assert parse_model("") == (None, None)


# --- providers: multi-turn chat --------------------------------------------------

def test_mock_chat_echoes_last_user_message():
    msgs = [
        {"role": "system", "content": "be nice"},
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "second"},
    ]
    assert MockProvider().chat(msgs) == "second"
    assert MockProvider(response="canned").chat(msgs) == "canned"


def test_base_chat_fallback_flattens(monkeypatch):
    # A custom single-turn provider (no chat override) still works behind the proxy.
    from clara.llm.base import LLMProvider

    seen = {}

    class SingleTurn(LLMProvider):
        def complete(self, system, prompt, *, max_tokens=2000, temperature=0.2):
            seen.update(system=system, prompt=prompt)
            return "answer"

    msgs = [{"role": "system", "content": "rules"},
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "q2"}]
    assert SingleTurn().chat(msgs) == "answer"
    assert seen["system"] == "rules"
    assert "q2" in seen["prompt"] and "a1" in seen["prompt"]   # transcript preserved


# --- the pipeline ----------------------------------------------------------------

def test_echo_upstream_is_faithful():
    res = proxy_chat([{"role": "user", "content": "Pay 500 dollars by 2024-01-31."}],
                     provider=MockProvider())
    assert res.content == "Pay 500 dollars by 2024-01-31."
    assert res.original == res.content
    assert res.faithfulness.ok
    assert res.level == "plain"


def test_lossy_simplifier_is_flagged_and_warned():
    upstream = MockProvider(response="You must pay 500 dollars by 2024-01-31.")
    lossy = MockProvider(response="You must pay soon.")
    res = proxy_chat([{"role": "user", "content": "What do I owe?"}],
                     provider=upstream, simplifier=lossy)
    assert not res.faithfulness.ok
    assert "500" in res.faithfulness.dropped_quantities
    assert "2024-01-31" in res.faithfulness.dropped_dates
    assert res.content.startswith("You must pay soon.")
    assert "⚠" in res.content                       # plain-language warning appended
    assert res.original == "You must pay 500 dollars by 2024-01-31."


def test_warning_is_localized():
    upstream = MockProvider(response="Оплатите 500 рублей до 2024-01-31.")
    lossy = MockProvider(response="Оплатите скоро.")
    res = proxy_chat([{"role": "user", "content": "Сколько я должен?"}],
                     provider=upstream, simplifier=lossy, options={"lang": "ru"})
    assert "Проверьте этот ответ" in res.content    # ru warning, not en


def test_annotate_can_be_disabled():
    upstream = MockProvider(response="Pay 500 dollars.")
    lossy = MockProvider(response="Pay.")
    res = proxy_chat([{"role": "user", "content": "?"}], provider=upstream,
                     simplifier=lossy, options={"annotate": False})
    assert not res.faithfulness.ok
    assert "⚠" not in res.content                   # report still carries the finding


def test_model_name_selects_grade_level():
    res = proxy_chat([{"role": "user", "content": "Hello."}],
                     provider=MockProvider(), model="clara-grade-7")
    assert res.level == "grade"
    assert res.grade == 7


# --- OpenAI wire format -----------------------------------------------------------

def _result() -> ProxyResult:
    return proxy_chat([{"role": "user", "content": "Pay 500 by 2024-01-31."}],
                      provider=MockProvider())


def test_completion_response_shape():
    d = completion_response(_result(), "clara-plain")
    assert d["object"] == "chat.completion"
    assert d["model"] == "clara-plain"
    assert d["choices"][0]["message"]["role"] == "assistant"
    assert d["choices"][0]["finish_reason"] == "stop"
    assert d["clara"]["faithful"] is True
    assert d["clara"]["original_content"] == d["choices"][0]["message"]["content"]
    assert "dropped_quantities" in d["clara"]["faithfulness"]


def test_stream_events_are_valid_sse():
    events = list(stream_events(_result(), "clara-plain"))
    assert all(e.startswith("data: ") and e.endswith("\n\n") for e in events)
    assert any('"content": "Pay 500 by 2024-01-31."' in e for e in events)
    assert '"finish_reason": "stop"' in events[-2]
    assert events[-1] == "data: [DONE]\n\n"


def test_models_response_lists_levels():
    ids = [m["id"] for m in models_response()["data"]]
    assert "clara-plain" in ids and "clara-easy-read" in ids


# --- HTTP endpoints (FastAPI) ------------------------------------------------------

fastapi = pytest.importorskip("fastapi")


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    import api.main as api_main
    return TestClient(api_main.app)


def test_endpoint_completions(client, monkeypatch):
    monkeypatch.setenv("CLARA_PROVIDER", "mock")
    r = client.post("/v1/chat/completions", json={
        "model": "clara-plain",
        "messages": [{"role": "user", "content": "Pay 500 by 2024-01-31."}],
    })
    assert r.status_code == 200
    d = r.json()
    assert d["choices"][0]["message"]["content"] == "Pay 500 by 2024-01-31."
    assert d["clara"]["faithful"] is True


def test_endpoint_stream_emulation(client, monkeypatch):
    monkeypatch.setenv("CLARA_PROVIDER", "mock")
    r = client.post("/v1/chat/completions", json={
        "model": "clara-plain", "stream": True,
        "messages": [{"role": "user", "content": "Hello."}],
    })
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    assert "data: [DONE]" in r.text


def test_endpoint_rejects_empty_messages(client):
    r = client.post("/v1/chat/completions", json={"messages": []})
    assert r.status_code == 400
    assert r.json()["error"]["type"] == "invalid_request_error"


def test_endpoint_models(client):
    r = client.get("/v1/models")
    assert r.status_code == 200
    assert r.json()["object"] == "list"
