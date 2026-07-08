"""Deterministic fact extraction — the backbone of the faithfulness layer.

We pull out the pieces that MUST survive simplification unchanged: quantities
(numbers, money, percentages) and dates. These are checked deterministically —
no LLM, no network — which is what makes the faithfulness report trustworthy: a
dropped deadline or a flipped amount is a hard, reproducible signal.

Language-specific vocabulary (month names, negation/obligation/condition words,
the word alphabet) comes from the language pack; the mechanics here are shared.
"""
from __future__ import annotations

import re
from collections import Counter

from .lang import get_pack

# Number / money / percent — language-independent (digits). One pass so a value
# is not counted twice.
_QTY_RE = re.compile(
    r"(?P<cur>[$€£₽]|\b(?:usd|eur|rub|gbp)\b)?\s*"
    r"(?P<num>\d{1,3}(?:[, \s]\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
    r"\s*(?P<pct>%|\bpercent\b|\bпроцент\w*)?",
    re.IGNORECASE,
)

_ISO_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")            # 2024-01-31
_SLASH_RE = re.compile(r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{2,4})\b")  # 31/01/2024 or 31.01.2024

_pattern_cache: dict[str, list] = {}


def _date_patterns(pack) -> list:
    if pack.code in _pattern_cache:
        return _pattern_cache[pack.code]
    pats = [("iso", _ISO_RE), ("slash", _SLASH_RE)]
    if pack.months:
        m = "|".join(sorted(pack.months, key=len, reverse=True))
        pats.append(("mdy", re.compile(rf"\b({m})\.?\s+(\d{{1,2}}),?\s+(\d{{4}})\b", re.IGNORECASE)))
        # day [.] [de] month [.] [de] year — covers "31 January 2024", "10. Januar 2024",
        # "10 de enero de 2024", "31 января 2024".
        pats.append(("dmy", re.compile(
            rf"\b(\d{{1,2}})\.?\s+(?:de\s+)?({m})\.?\s+(?:de\s+)?(\d{{4}})\b", re.IGNORECASE)))
    _pattern_cache[pack.code] = pats
    return pats


def _norm_date(tag: str, m: re.Match, months: dict) -> str:
    """Normalize to YYYY-MM-DD so the same date in different formats compares
    equal. Falls back to the lowercased raw string if the parts don't add up."""
    g = m.groups()
    try:
        if tag == "iso":
            y, mo, d = int(g[0]), int(g[1]), int(g[2])
        elif tag == "mdy":
            mo, d, y = months[g[0].lower().rstrip(".")], int(g[1]), int(g[2])
        elif tag == "dmy":
            d, mo, y = int(g[0]), months[g[1].lower().rstrip(".")], int(g[2])
        else:  # slash — ambiguous D/M vs M/D; the part >12 is the day
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


def extract_dates(text: str, lang: str = "en") -> tuple[list[str], list[tuple[int, int]]]:
    pack = get_pack(lang)
    dates: list[str] = []
    spans: list[tuple[int, int]] = []
    for tag, rx in _date_patterns(pack):
        for m in rx.finditer(text or ""):
            dates.append(_norm_date(tag, m, pack.months))
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
    """Canonical quantity tokens: '1200', '50%', '$1200'."""
    out: list[str] = []
    for m in _QTY_RE.finditer(text or ""):
        num = re.sub(r"[, \s]", "", m.group("num"))
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


_LETTERS_RE = re.compile(r"[^\W\d_]+", re.UNICODE)  # runs of letters, any language


def _words_to_number(run: list, units: dict, scales: dict, join: set) -> int:
    result, current = 0, 0
    for tok in run:
        if tok in join:
            continue
        if tok in units:
            current += units[tok]
        elif tok in scales:
            s = scales[tok]
            if s == 100:
                current = (current or 1) * 100          # "five hundred" -> 500
            else:
                current = (current or 1) * s
                result += current
                current = 0
    return result + current


def _extract_number_words(text: str, pack) -> list[str]:
    """Spelled-out numbers as canonical digit strings, so "five hundred" matches
    "500". Only emits values >= 100 or runs of >= 2 number words — a bare "one"
    in prose is left alone to avoid noise."""
    units = pack.number_units
    if not units:
        return []
    scales, join = pack.number_scales, pack.number_join
    tokens = _LETTERS_RE.findall((text or "").lower())
    out: list[str] = []
    i, n = 0, len(tokens)
    while i < n:
        run, count = [], 0
        while i < n and (tokens[i] in units or tokens[i] in scales or (run and tokens[i] in join)):
            if tokens[i] not in join:
                count += 1
            run.append(tokens[i])
            i += 1
        if count:
            value = _words_to_number(run, units, scales, join)
            if value >= 100 or count >= 2:
                out.append(str(value))
        else:
            i += 1
    return out


def inventory(text: str, lang: str = "en") -> dict:
    pack = get_pack(lang)
    dates, spans = extract_dates(text, lang)
    masked = _mask(text or "", spans)
    quantities = extract_quantities(masked) + _extract_number_words(masked, pack)
    return {
        "quantities": Counter(quantities),
        "dates": Counter(dates),
        "negation": len(pack.negation_re.findall(text or "")),
        "obligation": len(pack.obligation_re.findall(text or "")),
        "condition": len(pack.condition_re.findall(text or "")),
    }
