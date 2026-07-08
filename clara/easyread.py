"""Easy Read: simplified text laid out one idea per line, each line paired with a
pictogram. This is the format the Easy Read standard (Inclusion Europe) uses for
readers with intellectual disabilities.

The text still passes through the faithfulness check — pictures never excuse a
dropped fact. Pictogram matching is best-effort and meant to be reviewed by a
human: the chosen keyword is returned so a reviewer can swap the image. Stopwords,
the word alphabet, and the pictogram locale come from the language pack.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .lang import get_pack
from .llm import get_provider
from .llm.base import LLMProvider
from .pictograms import SymbolProvider, get_symbol_provider
from .readability import Readability, analyze
from .simplify import simplify
from .verify import FaithfulnessReport, verify

# Sentence terminators are effectively universal across the languages we target.
_SENT_SPLIT = re.compile(r"(?<=[.!?…])\s+")


def _keywords(line: str, pack=None) -> list[str]:
    """Content words of a line as pictogram candidates, best first: likely
    nouns/verbs before generic modifiers (see LanguagePack.keyword_rank), ties
    broken by original order."""
    pack = pack or get_pack("en")
    words = [w for w in pack.keyword_re.findall(line.lower()) if w not in pack.stopwords]
    return [w for _, w in sorted(enumerate(words), key=lambda iw: (pack.keyword_rank(iw[1]), iw[0]))]


def _split_lines(text: str) -> list[str]:
    """Easy Read = one idea per line. Prefer the model's own line breaks; if the
    text is a single block, fall back to sentence splitting (keeps terminators)."""
    lines = [ln.strip(" \t-*•").strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    if len(lines) <= 1:
        lines = [s.strip() for s in _SENT_SPLIT.split(text.strip()) if s.strip()]
    return lines


@dataclass
class EasyReadLine:
    text: str
    keyword: str | None = None
    pictogram_id: int | str | None = None
    image_url: str | None = None
    symbol_source: str | None = None   # which symbol set the picture came from


@dataclass
class EasyReadResult:
    original: str
    lines: list[EasyReadLine] = field(default_factory=list)
    # Always set by easy_read(); the None default is just a dataclass placeholder.
    source_readability: Readability = None  # type: ignore[assignment]
    output_readability: Readability = None  # type: ignore[assignment]
    faithfulness: FaithfulnessReport = None  # type: ignore[assignment]
    symbol_source: str | None = None   # the symbol set used (arasaac / mulberry)


def easy_read(
    text: str,
    provider: LLMProvider | None = None,
    lang: str = "en",
    with_pictograms: bool = True,
    symbols: SymbolProvider | str | None = None,
) -> EasyReadResult:
    provider = provider or get_provider()
    pack = get_pack(lang)
    sym = symbols if isinstance(symbols, SymbolProvider) else get_symbol_provider(symbols)
    simplified = simplify(text, level="easy_read", provider=provider, lang=lang)

    lines: list[EasyReadLine] = []
    for line_text in _split_lines(simplified):
        line = EasyReadLine(text=line_text)
        if with_pictograms:
            for kw in _keywords(line_text, pack):
                lemma = pack.lemmatize(kw)  # 'воду' -> 'вода' so the symbol set matches
                hit = sym.best(lemma, lang=pack.pictogram_lang)
                if hit:
                    line.keyword = lemma
                    line.pictogram_id = hit.id
                    line.image_url = hit.image_url
                    line.symbol_source = hit.provider
                    break
        lines.append(line)

    joined = "\n".join(ln.text for ln in lines)
    return EasyReadResult(
        original=text,
        lines=lines,
        source_readability=analyze(text, lang),
        output_readability=analyze(joined, lang),
        faithfulness=verify(text, joined, lang),
        symbol_source=sym.name,
    )
