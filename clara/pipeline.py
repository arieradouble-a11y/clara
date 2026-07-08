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
from .simplify import simplify, simplify_blocks
from .structure import Block, blocks_to_text
from .verify import FaithfulnessReport, verify


@dataclass
class SimplifyResult:
    original: str
    simplified: str
    level: str
    source_readability: Readability
    output_readability: Readability
    faithfulness: FaithfulnessReport


@dataclass
class StructuredResult:
    original: str
    blocks: list[Block]          # simplified blocks (structure preserved)
    level: str
    source_readability: Readability
    output_readability: Readability
    faithfulness: FaithfulnessReport


def simplify_text(
    text: str,
    level: str = "plain",
    provider: LLMProvider | None = None,
    grade: int | None = None,
    lang: str = "en",
) -> SimplifyResult:
    provider = provider or get_provider()
    simplified = simplify(text, level=level, provider=provider, grade=grade, lang=lang)
    return SimplifyResult(
        original=text,
        simplified=simplified,
        level=level,
        source_readability=analyze(text, lang),
        output_readability=analyze(simplified, lang),
        faithfulness=verify(text, simplified, lang),
    )


def simplify_structured(
    blocks: list[Block],
    level: str = "plain",
    provider: LLMProvider | None = None,
    grade: int | None = None,
    lang: str = "en",
) -> StructuredResult:
    """Simplify a document while preserving its headings and lists.

    Readability and faithfulness still run on the *flattened* text of both sides,
    so the structural view and the verification view stay consistent.
    """
    provider = provider or get_provider()
    original = blocks_to_text(blocks)
    out_blocks = simplify_blocks(blocks, level=level, provider=provider, grade=grade, lang=lang)
    simplified = blocks_to_text(out_blocks)
    return StructuredResult(
        original=original,
        blocks=out_blocks,
        level=level,
        source_readability=analyze(original, lang),
        output_readability=analyze(simplified, lang),
        faithfulness=verify(original, simplified, lang),
    )
