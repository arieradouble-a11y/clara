"""AAC-style symbol board — composing a request by tapping pictures.

Prompting is a cognitive skill: for many people with intellectual disabilities,
aphasia, or low literacy, an empty text box is the barrier. AAC (Augmentative
and Alternative Communication) practice solves this with symbol boards — grids
of pictograms organised by category, tapped in sequence to build a message.

This module serves that board for Clara's UIs: a curated core vocabulary
(clara/data/board.json, labels in en/ru/es/de/fr) with each word's picture
resolved through the pluggable symbol providers. Base forms only — turning
"я хотеть понять письмо" into an answer is the model's job (see the AAC-aware
system prompt in easyread.ask).

Fails soft everywhere: a word without a matching pictogram is still a tappable
tile with its label, and with the Mulberry set the whole board works offline.
"""
from __future__ import annotations

import json
from pathlib import Path

from .lang import get_pack
from .pictograms import SymbolProvider, get_symbol_provider

_PATH = Path(__file__).resolve().parent / "data" / "board.json"
_data: dict | None = None


def _load() -> dict:
    global _data
    if _data is None:
        try:
            _data = json.loads(_PATH.read_text(encoding="utf-8"))
        except Exception:
            _data = {"categories": []}
    return _data


def _label(labels: dict, lang: str) -> str:
    """The label for a language, falling back to English, then to anything."""
    if not isinstance(labels, dict):
        return ""
    return labels.get(lang) or labels.get("en") or next(iter(labels.values()), "")


def board(lang: str = "en", symbols: SymbolProvider | str | None = None) -> dict:
    """The board with labels in `lang` and pictures from the chosen symbol set.

    Lookups: the localized label against the pack's pictogram locale, falling
    back to the English label (Mulberry's index is English-only, so it looks up
    English directly while the visible label stays localized). Lookups are
    disk-cached by the providers, so the first request warms the board and the
    rest are instant.
    """
    try:
        pack = get_pack(lang)
    except ValueError:          # unknown UI language -> degrade to English lookups
        pack = get_pack("en")
    provider = symbols if isinstance(symbols, SymbolProvider) else get_symbol_provider(symbols)
    categories = []
    for cat in _load().get("categories", []):
        words = []
        for w in cat.get("words", []):
            labels = w.get("label", {})
            label = _label(labels, lang)
            label_en = labels.get("en", label) if isinstance(labels, dict) else label
            lookup = label_en if provider.name == "mulberry" else label
            sym = provider.best(lookup, lang=pack.pictogram_lang)
            if sym is None and lookup != label_en:
                sym = provider.best(label_en, lang="en")   # concept fallback
            words.append({
                "key": w.get("key"),
                "label": label,
                "pictogram_id": sym.id if sym else None,
                "image_url": sym.image_url if sym else None,
            })
        categories.append({
            "id": cat.get("id"),
            "label": _label(cat.get("label", {}), lang),
            "words": words,
        })
    return {"lang": lang, "symbols": provider.name, "categories": categories}
