"""Simplification prompts, one per output standard.

Three distinct targets — they are genuinely different audiences and are often
conflated:
  - plain      : Plain Language (ISO 24495-1). General cognitive load, wide public.
  - easy_read  : Easy Read / E2R. Intellectual disabilities. One idea per line, images.
  - grade      : hit a target US reading grade (e.g. WCAG AAA ≈ grade 5).

The system message carries HARD RULES about preserving facts; the source text is
passed as the user prompt (this also lets MockProvider echo it verbatim).
"""
from __future__ import annotations

from .llm import get_provider
from .llm.base import LLMProvider

_HARD_RULES = (
    "You rewrite complex text into clearer language for readers with cognitive "
    "disabilities, aphasia, low literacy, or limited proficiency in the language.\n"
    "HARD RULES — never break these:\n"
    "- Preserve every fact. Keep all numbers, amounts, dates and deadlines exactly.\n"
    "- Never invert meaning. Keep every negation ('not', 'no') and every condition "
    "('if', 'unless', 'except').\n"
    "- Never add information that is not in the source.\n"
    "- If something is genuinely unclear, keep it rather than guess.\n"
    "- Output only the rewritten text. No preamble, no notes.\n"
)

_STYLES = {
    "plain": (
        "STYLE — Plain Language:\n"
        "- Short sentences, aim under 20 words.\n"
        "- Active voice. Everyday words. Explain any jargon in plain terms.\n"
        "- Keep the logical structure of the original.\n"
    ),
    "easy_read": (
        "STYLE — Easy Read:\n"
        "- One idea per sentence, one sentence per line.\n"
        "- Use short, common words. Explain any hard word in brackets.\n"
        "- Speak directly to the reader ('you'). Use active voice.\n"
    ),
}


def build_system(level: str = "plain", grade: int | None = None) -> str:
    if level == "grade":
        g = grade or 5
        style = (
            f"STYLE — write at US grade {g} reading level.\n"
            "- Short sentences and common words. Active voice.\n"
        )
    else:
        style = _STYLES.get(level, _STYLES["plain"])
    return _HARD_RULES + style


def simplify(
    text: str,
    level: str = "plain",
    provider: LLMProvider | None = None,
    grade: int | None = None,
) -> str:
    provider = provider or get_provider()
    system = build_system(level, grade)
    return provider.complete(system, text).strip()
