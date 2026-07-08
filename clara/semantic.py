"""LLM-based semantic faithfulness check — layered ON TOP of the deterministic
one in verify.py.

The deterministic check catches hard facts (numbers, dates, negation counts).
This one catches meaning drift the regexes can't see: a weakened obligation, a
subtly changed condition, an added implication. It costs an LLM call, so it is
opt-in, and it degrades to "unavailable" when no capable provider returns usable
JSON (e.g. the offline mock) rather than inventing a verdict.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from .llm import get_provider
from .llm.base import LLMProvider

_SYSTEM = (
    "You are a strict fact-checker for plain-language rewrites. Compare the "
    "ORIGINAL and the SIMPLIFIED text and report only genuine problems where the "
    "simplified text LOSES, ADDS, or CHANGES meaning.\n"
    "Issue types:\n"
    "- omission: a fact, number, date, condition, or obligation was dropped\n"
    "- addition: information not present in the original was introduced\n"
    "- contradiction: the meaning was inverted (e.g. a negation flipped)\n"
    "- distortion: the meaning was changed or weakened\n"
    "If the simplified text is faithful, return an empty issues list.\n"
    "Respond with ONLY a JSON object, no prose:\n"
    '{"faithful": true, "issues": [{"type": "omission", "detail": "..."}]}'
)


@dataclass
class SemanticIssue:
    type: str
    detail: str


@dataclass
class SemanticReport:
    available: bool = False       # did a provider return a usable verdict?
    faithful: bool | None = None
    issues: list[SemanticIssue] = field(default_factory=list)


def _extract_json(text: str) -> dict | None:
    """Pull a JSON object out of a model response, tolerating code fences and
    surrounding prose."""
    if not text:
        return None
    i, j = text.find("{"), text.rfind("}")
    if i == -1 or j == -1 or j < i:
        return None
    try:
        obj = json.loads(text[i:j + 1])
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def semantic_check(
    source: str,
    output: str,
    provider: LLMProvider | None = None,
    lang: str = "en",
) -> SemanticReport:
    provider = provider or get_provider()
    prompt = f"ORIGINAL:\n{source}\n\nSIMPLIFIED:\n{output}"
    try:
        raw = provider.complete(_SYSTEM, prompt)
    except Exception:
        return SemanticReport(available=False)

    data = _extract_json(raw)
    if data is None or "issues" not in data:
        return SemanticReport(available=False)

    issues = [
        SemanticIssue(type=str(it.get("type", "")), detail=str(it.get("detail", "")))
        for it in data.get("issues", [])
        if isinstance(it, dict)
    ]
    faithful = bool(data.get("faithful", not issues)) and not issues
    return SemanticReport(available=True, faithful=faithful, issues=issues)
