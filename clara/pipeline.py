"""The end-to-end pipeline: simplify -> verify -> score.

This is the single entry point most callers want. It returns a SimplifyResult
carrying the original, the simplified text, both readability scores, and the
faithfulness report so a UI can render the source and output side by side with
drift highlighted.
"""
from __future__ import annotations

from dataclasses import dataclass

from .llm import get_provider
from .llm.base import LLMProvider
from .readability import Readability, analyze
from .simplify import simplify
from .verify import FaithfulnessReport, verify


@dataclass
class SimplifyResult:
    original: str
    simplified: str
    level: str
    source_readability: Readability
    output_readability: Readability
    faithfulness: FaithfulnessReport


def simplify_text(
    text: str,
    level: str = "plain",
    provider: LLMProvider | None = None,
    grade: int | None = None,
) -> SimplifyResult:
    provider = provider or get_provider()
    simplified = simplify(text, level=level, provider=provider, grade=grade)
    return SimplifyResult(
        original=text,
        simplified=simplified,
        level=level,
        source_readability=analyze(text),
        output_readability=analyze(simplified),
        faithfulness=verify(text, simplified),
    )
