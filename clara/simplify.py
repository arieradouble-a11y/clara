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

import re

from .lang import get_pack
from .llm import get_provider
from .llm.base import LLMProvider
from .structure import HEADING, Block

# A long document must be simplified in pieces — one giant call gets truncated by
# the model's max_tokens mid-document. We split on paragraph (then sentence)
# boundaries so each piece is self-contained, simplify each, and rejoin.
_CHUNK_CHARS = 2500

_HARD_RULES = (
    "You rewrite complex text into clearer language for readers with cognitive "
    "disabilities, aphasia, low literacy, or limited proficiency in the language.\n"
    "HARD RULES — never break these:\n"
    "- Preserve every fact. Keep all numbers, amounts, dates and deadlines exactly.\n"
    "- Never invert meaning. Keep every negation ('not', 'no') and every condition "
    "('if', 'unless', 'except').\n"
    "- Never add information that is not in the source.\n"
    "- Write in the same language as the source text.\n"
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


def build_system(level: str = "plain", grade: int | None = None, lang: str = "en",
                 extra: str = "") -> str:
    if level == "grade":
        g = grade or 5
        style = (
            f"STYLE — write at US grade {g} reading level.\n"
            "- Short sentences and common words. Active voice.\n"
        )
    else:
        style = _STYLES.get(level, _STYLES["plain"])
    note = get_pack(lang).simplify_note
    out = _HARD_RULES + style + (f"\n{note}\n" if note else "")
    if extra:
        # Per-reader constraints (an accessibility profile) on top of the style.
        out += f"\nREADER PROFILE — additional constraints:\n{extra}\n"
    return out


def _split_paragraph(paragraph: str, max_chars: int) -> list[str]:
    """Split one over-long paragraph on sentence boundaries."""
    out: list[str] = []
    buf = ""
    for sentence in re.split(r"(?<=[.!?…])\s+", paragraph):
        if buf and len(buf) + len(sentence) + 1 > max_chars:
            out.append(buf)
            buf = sentence
        else:
            buf = f"{buf} {sentence}" if buf else sentence
    if buf:
        out.append(buf)
    return out


def chunk_text(text: str, max_chars: int = _CHUNK_CHARS) -> list[str]:
    """Group paragraphs into chunks under max_chars, keeping paragraph
    boundaries; an over-long paragraph is split by sentences."""
    chunks: list[str] = []
    buf = ""
    for para in re.split(r"\n\s*\n", (text or "").strip()):
        para = para.strip()
        if not para:
            continue
        if len(para) > max_chars:
            if buf:
                chunks.append(buf)
                buf = ""
            chunks.extend(_split_paragraph(para, max_chars))
        elif buf and len(buf) + len(para) + 2 > max_chars:
            chunks.append(buf)
            buf = para
        else:
            buf = f"{buf}\n\n{para}" if buf else para
    if buf:
        chunks.append(buf)
    return chunks


def simplify(
    text: str,
    level: str = "plain",
    provider: LLMProvider | None = None,
    grade: int | None = None,
    lang: str = "en",
    max_chars: int = _CHUNK_CHARS,
    extra: str = "",
) -> str:
    provider = provider or get_provider()
    system = build_system(level, grade, lang, extra)
    parts = chunk_text(text, max_chars)
    if len(parts) <= 1:
        return provider.complete(system, text).strip()
    return "\n\n".join(provider.complete(system, part).strip() for part in parts)


def simplify_blocks(
    blocks: list[Block],
    level: str = "plain",
    provider: LLMProvider | None = None,
    grade: int | None = None,
    lang: str = "en",
    max_chars: int = _CHUNK_CHARS,
) -> list[Block]:
    """Simplify a structured document block by block, preserving the scaffolding.

    Each block's text is rewritten under the same hard rules, but its type, level
    and list-ordering are carried through unchanged — so a heading stays a
    heading and a numbered step stays a numbered step. Headings are short and
    rarely need simplifying, so they're passed through verbatim to avoid an LLM
    call inflating a two-word label into a sentence.
    """
    provider = provider or get_provider()
    system = build_system(level, grade, lang)
    out: list[Block] = []
    for b in blocks:
        text = b.text.strip()
        if not text or b.type == HEADING:
            out.append(Block(type=b.type, text=text, level=b.level, ordered=b.ordered))
            continue
        # A paragraph can be long enough to need chunking; a list item won't be.
        parts = chunk_text(text, max_chars)
        simplified = "\n\n".join(provider.complete(system, p).strip() for p in parts) if parts else ""
        out.append(Block(type=b.type, text=simplified.strip(), level=b.level, ordered=b.ordered))
    return out
