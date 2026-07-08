"""UI string catalog loader.

The chrome of both front-ends (the reference UI and the Next app) reads its
strings from one JSON catalog, served at /i18n, so a translation is written once
and stays in sync. English is the source of truth; a missing language or key
falls back to English in the clients.
"""
from __future__ import annotations

import json
from pathlib import Path

_PATH = Path(__file__).resolve().parent / "data" / "ui_i18n.json"
_cache: dict | None = None


def ui_strings() -> dict:
    """The full catalog: {lang: {key: string}}. Cached; excludes private keys."""
    global _cache
    if _cache is None:
        try:
            data = json.loads(_PATH.read_text(encoding="utf-8"))
        except Exception:
            data = {"en": {}}
        _cache = {lang: strings for lang, strings in data.items() if not lang.startswith("_")}
    return _cache
