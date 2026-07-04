"""Easy Read: simplified text laid out one idea per line, each line paired with a
pictogram. This is the format the Easy Read standard (Inclusion Europe) uses for
readers with intellectual disabilities.

The text still passes through the faithfulness check — pictures never excuse a
dropped fact. Pictogram matching is best-effort and meant to be reviewed by a
human: the chosen keyword is returned so a reviewer can swap the image.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .llm import get_provider
from .llm.base import LLMProvider
from .pictograms import best_id, image_url
from .readability import Readability, analyze
from .simplify import simplify
from .verify import FaithfulnessReport, verify

# Function words we never try to illustrate — a picture of "the" helps no one.
_STOP = {
    "the", "a", "an", "you", "your", "i", "we", "they", "he", "she", "it", "this",
    "that", "these", "those", "and", "or", "but", "if", "unless", "of", "to", "in",
    "on", "at", "by", "for", "with", "from", "as", "is", "are", "was", "were", "be",
    "been", "being", "do", "does", "did", "have", "has", "had", "will", "shall",
    "must", "may", "can", "should", "would", "could", "not", "no", "than", "then",
    "there", "here", "who", "what", "when", "where", "how", "any", "all", "some",
    "one", "please", "must",
}


def _keywords(line: str) -> list[str]:
    """Content words of a line, in order, as pictogram candidates."""
    return [w for w in re.findall(r"[A-Za-z]{3,}", line.lower()) if w not in _STOP]


def _split_lines(text: str) -> list[str]:
    """Easy Read = one idea per line. Prefer the model's own line breaks; if the
    text is a single block, fall back to sentence splitting."""
    lines = [ln.strip(" \t-*•").strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    if len(lines) <= 1:
        lines = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    return lines


@dataclass
class EasyReadLine:
    text: str
    keyword: str | None = None
    pictogram_id: int | None = None
    image_url: str | None = None


@dataclass
class EasyReadResult:
    original: str
    lines: list[EasyReadLine] = field(default_factory=list)
    source_readability: Readability = None
    output_readability: Readability = None
    faithfulness: FaithfulnessReport = None


def easy_read(
    text: str,
    provider: LLMProvider | None = None,
    lang: str = "en",
    with_pictograms: bool = True,
) -> EasyReadResult:
    provider = provider or get_provider()
    simplified = simplify(text, level="easy_read", provider=provider)

    lines: list[EasyReadLine] = []
    for line_text in _split_lines(simplified):
        line = EasyReadLine(text=line_text)
        if with_pictograms:
            for kw in _keywords(line_text):
                pid = best_id(kw, lang=lang)
                if pid:
                    line.keyword = kw
                    line.pictogram_id = pid
                    line.image_url = image_url(pid)
                    break
        lines.append(line)

    joined = "\n".join(ln.text for ln in lines)
    return EasyReadResult(
        original=text,
        lines=lines,
        source_readability=analyze(text),
        output_readability=analyze(joined),
        faithfulness=verify(text, joined),
    )
