"""Deterministic fact extraction — the backbone of the faithfulness layer.

We pull out the pieces of a text that MUST survive simplification unchanged:
quantities (numbers, money, percentages) and dates. These are checked
deterministically — no LLM, no network — which is exactly what makes the
faithfulness report trustworthy: a dropped deadline or a flipped amount is a
hard, reproducible signal, not a model's opinion.

Semantic elements (negation, obligation, condition) are also inventoried, but
only as *review hints*: they are heuristic and meant to prompt a human, never
to be trusted blindly.

English-first. Other languages plug in by adding their own month names and
marker words (see ROADMAP in the README).
"""
from __future__ import annotations

import re
from collections import Counter

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12, "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}
_MONTH_RE = "|".join(sorted(_MONTHS, key=len, reverse=True))

# (tag, regex) so normalization does not depend on fragile pattern-string checks.
_DATE_PATTERNS = [
    ("iso", re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")),                              # 2024-01-31
    ("mdy", re.compile(rf"\b({_MONTH_RE})\.?\s+(\d{{1,2}}),?\s+(\d{{4}})\b", re.I)),  # January 31, 2024
    ("dmy", re.compile(rf"\b(\d{{1,2}})\s+({_MONTH_RE})\.?\s+(\d{{4}})\b", re.I)),    # 31 January 2024
    ("slash", re.compile(r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{2,4})\b")),                # 31/01/2024
]

# One pass captures numbers, money and percentages so we don't double-count.
_QTY_RE = re.compile(
    r"(?P<cur>[$€£₽]|\b(?:usd|eur|rub|gbp)\b)?\s*"
    r"(?P<num>\d{1,3}(?:[, \s]\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
    r"\s*(?P<pct>%|\bpercent\b)?",
    re.I,
)

_NEGATION_RE = re.compile(
    r"\b(not|no|never|cannot|can't|won't|don't|doesn't|didn't|without|neither|nor)\b", re.I
)
_OBLIGATION_RE = re.compile(
    r"\b(must|shall|required|mandatory|obliged|obligated|have to|has to)\b", re.I
)
_CONDITION_RE = re.compile(
    r"\b(if|unless|except|provided that|only if|in case|subject to)\b", re.I
)


def _norm_date(tag: str, m: re.Match) -> str:
    """Normalize a matched date to YYYY-MM-DD so the same date written in
    different formats (ISO vs 'January 31, 2024') compares equal. Falls back to
    the lowercased raw string if the parts don't add up."""
    g = m.groups()
    try:
        if tag == "iso":
            y, mo, d = int(g[0]), int(g[1]), int(g[2])
        elif tag == "mdy":
            mo, d, y = _MONTHS[g[0].lower().rstrip(".")], int(g[1]), int(g[2])
        elif tag == "dmy":
            d, mo, y = int(g[0]), _MONTHS[g[1].lower().rstrip(".")], int(g[2])
        else:  # slash — ambiguous D/M vs M/D; use the >12 part as the day, else default D/M/Y
            a, b, y = int(g[0]), int(g[1]), int(g[2])
            if y < 100:
                y += 2000
            if a > 12:
                d, mo = a, b
            elif b > 12:
                d, mo = b, a
            else:
                d, mo = a, b
        return f"{y:04d}-{mo:02d}-{d:02d}"
    except (KeyError, ValueError):
        return m.group(0).lower()


def extract_dates(text: str) -> tuple[list[str], list[tuple[int, int]]]:
    """Return normalized dates and the character spans they occupied (so the
    quantity pass can mask them out and not re-count the year/day digits)."""
    dates: list[str] = []
    spans: list[tuple[int, int]] = []
    for tag, rx in _DATE_PATTERNS:
        for m in rx.finditer(text or ""):
            dates.append(_norm_date(tag, m))
            spans.append((m.start(), m.end()))
    return dates, spans


def _mask(text: str, spans: list[tuple[int, int]]) -> str:
    if not spans:
        return text
    chars = list(text)
    for s, e in spans:
        for i in range(s, e):
            chars[i] = " "
    return "".join(chars)


def extract_quantities(text: str) -> list[str]:
    """Return canonical quantity tokens: '1200', '50%', '$1200'. Thousands
    separators are stripped; percent words normalize to '%'; currency words
    normalize to their symbol."""
    out: list[str] = []
    for m in _QTY_RE.finditer(text or ""):
        num = re.sub(r"[, \s]", "", m.group("num"))
        if m.group("pct"):
            out.append(num + "%")
        elif m.group("cur"):
            cur = (m.group("cur").lower()
                   .replace("usd", "$").replace("eur", "€")
                   .replace("gbp", "£").replace("rub", "₽"))
            out.append(cur + num)
        else:
            out.append(num)
    return out


def inventory(text: str) -> dict:
    """Full deterministic inventory of a text used by the faithfulness check."""
    dates, spans = extract_dates(text or "")
    masked = _mask(text or "", spans)
    return {
        "quantities": Counter(extract_quantities(masked)),
        "dates": Counter(dates),
        "negation": len(_NEGATION_RE.findall(text or "")),
        "obligation": len(_OBLIGATION_RE.findall(text or "")),
        "condition": len(_CONDITION_RE.findall(text or "")),
    }
