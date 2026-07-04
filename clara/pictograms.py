"""Pictogram lookup via ARASAAC — ~13k multilingual Creative Commons symbols,
used to pair Easy Read text with a picture per line.

Network calls are cached on disk and fail soft: if ARASAAC is unreachable the
text still works, just without images. Only definitive answers (a real hit or a
real "no match") are cached — transient network errors are not, so a picture can
appear on the next run.

Attribution: pictograms are the property of the Government of Aragón, created by
Sergio Palao for ARASAAC (https://arasaac.org), licensed CC BY-NC-SA. The
non-commercial clause carries downstream — see the README before shipping.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

_API = "https://api.arasaac.org/v1/pictograms"
_STATIC = "https://static.arasaac.org/pictograms"

_CACHE_DIR = Path(os.environ.get("CLARA_CACHE", Path.home() / ".cache" / "clara"))
_CACHE_FILE = _CACHE_DIR / "arasaac.json"
_cache: dict | None = None


def image_url(pictogram_id: int, size: int = 300) -> str:
    return f"{_STATIC}/{pictogram_id}/{pictogram_id}_{size}.png"


def _load_cache() -> dict:
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            _cache = {}
    return _cache


def _save_cache() -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _CACHE_FILE.write_text(json.dumps(_cache, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def best_id(keyword: str, lang: str = "en", *, timeout: float = 8.0) -> int | None:
    """Best ARASAAC pictogram id for a keyword, or None. Cached; soft-fails."""
    keyword = (keyword or "").strip().lower()
    if not keyword:
        return None
    cache = _load_cache()
    key = f"{lang}:{keyword}"
    if key in cache:
        return cache[key]

    pid: int | None = None
    definitive = False
    try:
        import httpx

        r = httpx.get(f"{_API}/{lang}/bestsearch/{keyword}", timeout=timeout)
        if r.status_code == 200:
            definitive = True
            data = r.json()
            if isinstance(data, list) and data:
                pid = int(data[0]["_id"])
        elif r.status_code == 404:
            definitive = True  # a real "no pictogram for this word"
    except Exception:
        definitive = False  # network hiccup — don't poison the cache

    if definitive:
        cache[key] = pid
        _save_cache()
    return pid
