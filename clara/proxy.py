"""OpenAI-compatible accessibility proxy — Clara between a person and any LLM.

LLMs are rapidly becoming how people get information, and raw model output is a
wall of text many readers can't use. This module lets any OpenAI-compatible chat
client point at Clara instead of the vendor: the conversation is forwarded to
the configured upstream provider, and the answer passes through the Clara
pipeline before the person sees it — simplified to the chosen reading level and
checked by the deterministic faithfulness layer, so a simplification that drops
a number or a date is flagged, never silent.

    chat client → POST /v1/chat/completions
                → upstream provider answers (full conversation)
                → simplify(answer) → verify(answer, simplified)
                → OpenAI-format response (+ `clara` extension block)

Configuration (env), overridable per request:
    CLARA_PROVIDER        upstream provider (also the default simplifier)
    CLARA_PROXY_LEVEL     plain | easy_read | grade      (default plain)
    CLARA_PROXY_GRADE     target grade for level=grade   (default 5)
    CLARA_PROXY_LANG      language pack for verification (default en)
    CLARA_PROXY_ANNOTATE  append a plain-language warning when facts were
                          lost (default on; "0" to disable)

Per request: the model name picks the level (`clara-plain`, `clara-easy-read`,
`clara-grade-7`; any other name keeps the env default), and an optional `clara`
object in the request body overrides level/grade/lang/annotate.

Honest costs: two model calls per turn (answer + simplify) — the faithfulness
check itself is deterministic and free. True token streaming is impossible
(the pipeline needs the whole answer), so `stream: true` is emulated. The proxy
ignores incoming Authorization and uses its own upstream keys; add your own
auth in front before exposing it publicly.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import time
from collections.abc import Iterator
from dataclasses import dataclass

from .llm import get_provider
from .llm.base import LLMProvider
from .serialize import faithfulness_dict
from .simplify import simplify
from .verify import FaithfulnessReport, verify

_MODEL_GRADE = re.compile(r"^clara-grade-(\d{1,2})$")

# Appended when verification finds lost facts. It must itself be plain language,
# in the reader's language — a warning the reader can't read is no warning.
_FACTS_WARNING = {
    "en": "⚠ Check this answer. Some facts (numbers or dates) may be missing from the simple version.",
    "ru": "⚠ Проверьте этот ответ. В простой версии могли потеряться факты (числа или даты).",
    "es": "⚠ Revisa esta respuesta. En la versión simple pueden faltar datos (números o fechas).",
    "de": "⚠ Prüfen Sie diese Antwort. In der einfachen Fassung können Fakten (Zahlen oder Daten) fehlen.",
    "fr": "⚠ Vérifiez cette réponse. Des faits (nombres ou dates) peuvent manquer dans la version simple.",
}


def parse_model(model: str) -> tuple[str | None, int | None]:
    """(level, grade) encoded in a requested model name, or (None, None).

    `clara-plain` / `clara-easy-read` / `clara-grade-7` select the level, so any
    chat client with a model picker can switch reading levels with no custom UI.
    """
    m = (model or "").strip().lower()
    if m == "clara-plain":
        return "plain", None
    if m in ("clara-easy-read", "clara-easyread"):
        return "easy_read", None
    g = _MODEL_GRADE.match(m)
    if g:
        return "grade", int(g.group(1))
    return None, None


@dataclass
class ProxyResult:
    content: str                    # what the person sees (simplified, maybe + warning)
    original: str                   # the upstream answer, unmodified
    level: str
    grade: int | None
    lang: str
    faithfulness: FaithfulnessReport


def proxy_chat(
    messages: list[dict],
    *,
    model: str = "",
    provider: LLMProvider | None = None,
    simplifier: LLMProvider | None = None,
    options: dict | None = None,
    max_tokens: int = 2000,
    temperature: float = 0.2,
) -> ProxyResult:
    """Answer a conversation upstream, then simplify + verify the answer.

    Resolution order for level/grade/lang/annotate: explicit `options` (the
    request's `clara` object) > the model name > CLARA_PROXY_* env > defaults.
    """
    options = options or {}
    m_level, m_grade = parse_model(model)
    level = options.get("level") or m_level or os.environ.get("CLARA_PROXY_LEVEL", "plain")
    grade = int(options.get("grade") or m_grade or os.environ.get("CLARA_PROXY_GRADE", "5"))
    lang = options.get("lang") or os.environ.get("CLARA_PROXY_LANG", "en")
    annotate = options.get("annotate")
    if annotate is None:
        annotate = os.environ.get("CLARA_PROXY_ANNOTATE", "1").strip().lower() not in ("0", "false", "off", "no")

    provider = provider or get_provider()
    simplifier = simplifier or provider

    answer = provider.chat(messages, max_tokens=max_tokens, temperature=temperature)
    simplified = simplify(answer, level=level, provider=simplifier, grade=grade, lang=lang)
    fr = verify(answer, simplified, lang)

    content = simplified
    if annotate and not fr.ok:
        content = f"{content}\n\n{_FACTS_WARNING.get(lang, _FACTS_WARNING['en'])}"
    return ProxyResult(
        content=content,
        original=answer,
        level=level,
        grade=grade if level == "grade" else None,
        lang=lang,
        faithfulness=fr,
    )


def _display_model(res: ProxyResult, model: str) -> str:
    return model or "clara-" + res.level.replace("_", "-")


def completion_response(res: ProxyResult, model: str = "") -> dict:
    """An OpenAI chat-completion response, plus a `clara` extension block.

    Standard clients ignore unknown fields; capable clients can render the
    faithfulness report or offer "show the original answer"."""
    return {
        "id": f"chatcmpl-clara-{secrets.token_hex(12)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": _display_model(res, model),
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": res.content},
            "finish_reason": "stop",
        }],
        # The provider layer doesn't surface token counts; zeros are honest placeholders.
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "clara": {
            "level": res.level,
            "grade": res.grade,
            "lang": res.lang,
            "faithful": res.faithfulness.ok,
            "faithfulness": faithfulness_dict(res.faithfulness),
            "original_content": res.original,
        },
    }


def stream_events(res: ProxyResult, model: str = "") -> Iterator[str]:
    """Emulated SSE stream for `stream: true` clients.

    True token streaming is impossible here — the pipeline must see the whole
    answer before it can simplify and verify — so the finished text is sent in
    standard chunk frames instead, ending with [DONE]."""
    base = {
        "id": f"chatcmpl-clara-{secrets.token_hex(12)}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": _display_model(res, model),
    }

    def frame(delta: dict, finish: str | None = None) -> str:
        payload = {**base, "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    yield frame({"role": "assistant", "content": ""})
    yield frame({"content": res.content})
    yield frame({}, "stop")
    yield "data: [DONE]\n\n"


def models_response() -> dict:
    """The model list clients fetch to populate their picker — one entry per
    reading level (grade shown at its WCAG-ish default; any clara-grade-N works)."""
    return {
        "object": "list",
        "data": [
            {"id": mid, "object": "model", "created": 1700000000, "owned_by": "clara"}
            for mid in ("clara-plain", "clara-easy-read", "clara-grade-5")
        ],
    }
