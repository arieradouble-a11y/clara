"""Symbol lookup for Easy Read — pluggable picture sets behind one interface.

Easy Read pairs each line with a picture. Which picture *set* matters: the
default, ARASAAC, is ~13k multilingual symbols but licensed CC BY-NC-SA — the
non-commercial clause carries downstream. So the set is a provider:

  - ArasaacProvider (default) — https://arasaac.org, CC BY-NC-SA. Has a real
    search API, so a reviewer can browse alternatives.
  - MulberryProvider — https://mulberrysymbols.org, CC BY-SA. Commercial-
    compatible. A fixed set of ~3.4k English SVGs with no search API, matched
    against a bundled label index; art is fetched from the CDN at runtime.

Pick one with CLARA_SYMBOLS (default "arasaac") or per call. Every network call
is cached on disk and fails soft: if the set is unreachable the text still works,
just without a picture.

Attribution — ARASAAC pictograms are property of the Government of Aragón, author
Sergio Palao, CC BY-NC-SA. Mulberry Symbols by Steve Lee / Straight Street,
CC BY-SA. See the README before shipping either.
"""
from __future__ import annotations

import base64
import json
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

_CACHE_DIR = Path(os.environ.get("CLARA_CACHE", Path.home() / ".cache" / "clara"))
_DATA_DIR = Path(__file__).resolve().parent / "data"


@dataclass
class Symbol:
    """One candidate picture. `id` is opaque per provider (ARASAAC: a numeric id;
    Mulberry: a filename)."""
    id: int | str
    label: str
    image_url: str
    provider: str


# --- shared disk cache --------------------------------------------------------

def _cache_read(name: str) -> dict:
    try:
        return json.loads((_CACHE_DIR / name).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _cache_write(name: str, data: dict) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (_CACHE_DIR / name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _fetch_bytes(url: str, cache_path: Path, timeout: float) -> bytes | None:
    """Fetch (and disk-cache) the bytes at a URL. Soft-fails to None."""
    try:
        if cache_path.exists():
            return cache_path.read_bytes()
    except Exception:
        pass
    try:
        import httpx

        r = httpx.get(url, timeout=timeout)
        if r.status_code == 200 and r.content:
            try:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_bytes(r.content)
            except Exception:
                pass
            return r.content
    except Exception:
        return None
    return None


# --- interface ----------------------------------------------------------------

class SymbolProvider(ABC):
    name: str = ""
    license: str = ""
    attribution: str = ""
    mimetype: str = "image/png"

    @abstractmethod
    def best(self, keyword: str, lang: str = "en") -> Symbol | None:
        """The single best-matching symbol for a keyword, or None."""

    @abstractmethod
    def search(self, keyword: str, lang: str = "en", limit: int = 12) -> list[Symbol]:
        """Ordered alternatives for a keyword, so a reviewer can pick another."""

    @abstractmethod
    def image_url(self, symbol_id: int | str, size: int = 300) -> str:
        ...

    def data_uri(self, symbol_id: int | str, size: int = 300, *, timeout: float = 10.0) -> str | None:
        """A data: URI for a symbol, so exported HTML/PDF works offline. Returns
        None (caller falls back to the URL) if the image can't be fetched."""
        if not symbol_id:
            return None
        ext = "svg" if self.mimetype.endswith("svg+xml") else "png"
        path = _CACHE_DIR / "img" / self.name / f"{symbol_id}_{size}.{ext}"
        data = _fetch_bytes(self.image_url(symbol_id, size), path, timeout)
        if not data:
            return None
        return f"data:{self.mimetype};base64," + base64.b64encode(data).decode("ascii")


# --- ARASAAC ------------------------------------------------------------------

class ArasaacProvider(SymbolProvider):
    name = "arasaac"
    license = "CC BY-NC-SA"
    attribution = "ARASAAC — Government of Aragón, author Sergio Palao"
    mimetype = "image/png"

    _API = "https://api.arasaac.org/v1/pictograms"
    _STATIC = "https://static.arasaac.org/pictograms"

    def image_url(self, symbol_id, size: int = 300) -> str:
        return f"{self._STATIC}/{symbol_id}/{symbol_id}_{size}.png"

    def best(self, keyword: str, lang: str = "en", *, timeout: float = 8.0) -> Symbol | None:
        keyword = (keyword or "").strip().lower()
        if not keyword:
            return None
        cache = _cache_read("arasaac.json")
        key = f"{lang}:{keyword}"
        if key in cache:
            pid = cache[key]
            return self._symbol(pid, keyword) if pid else None

        pid: int | None = None
        definitive = False
        try:
            import httpx

            r = httpx.get(f"{self._API}/{lang}/bestsearch/{keyword}", timeout=timeout)
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
            _cache_write("arasaac.json", cache)
        return self._symbol(pid, keyword) if pid else None

    def search(self, keyword: str, lang: str = "en", limit: int = 12, *, timeout: float = 8.0) -> list[Symbol]:
        keyword = (keyword or "").strip().lower()
        if not keyword:
            return []
        try:
            import httpx

            r = httpx.get(f"{self._API}/{lang}/search/{keyword}", timeout=timeout)
            if r.status_code != 200:
                return []
            data = r.json()
        except Exception:
            return []
        out: list[Symbol] = []
        for hit in data if isinstance(data, list) else []:
            try:
                pid = int(hit["_id"])
            except Exception:
                continue
            label = keyword
            kws = hit.get("keywords") or []
            if kws and isinstance(kws[0], dict) and kws[0].get("keyword"):
                label = kws[0]["keyword"]
            out.append(self._symbol(pid, label))
            if len(out) >= limit:
                break
        return out

    def _symbol(self, pid: int, label: str) -> Symbol:
        return Symbol(id=pid, label=label, image_url=self.image_url(pid), provider=self.name)


# --- Mulberry -----------------------------------------------------------------

class MulberryProvider(SymbolProvider):
    name = "mulberry"
    license = "CC BY-SA"
    attribution = "Mulberry Symbols — Steve Lee / Straight Street"
    mimetype = "image/svg+xml"

    _RAW = "https://raw.githubusercontent.com/mulberrysymbols/mulberry-symbols/master/EN"
    _VARIANT = re.compile(r"_\d+[a-z]?$")  # trailing "_2", "_1a" mark near-duplicates

    _names: list[str] | None = None
    _tokens: dict[str, list[str]] | None = None   # first token -> filenames
    _exact: dict[str, str] | None = None          # full normalized label -> filename

    @classmethod
    def _index(cls):
        if cls._names is not None:
            return
        try:
            raw = json.loads((_DATA_DIR / "mulberry_en.json").read_text(encoding="utf-8"))
            names = raw.get("names", [])
        except Exception:
            names = []
        cls._names = names
        tokens: dict[str, list[str]] = {}
        exact: dict[str, str] = {}
        for n in names:
            toks = cls._norm(n).split()
            if not toks:
                continue
            label = " ".join(toks)
            # keep the "cleanest" filename for a given label / first token
            if label not in exact or cls._rank(n) < cls._rank(exact[label]):
                exact[label] = n
            tokens.setdefault(toks[0], []).append(n)
        cls._tokens, cls._exact = tokens, exact

    @staticmethod
    def _norm(name: str) -> str:
        s = name.replace("_,_to", " to").replace("_", " ").replace(",", " ").lower()
        return " ".join(s.split())

    @classmethod
    def _rank(cls, name: str) -> tuple:
        # Prefer variant-free, then shorter, then alphabetical — a stable "cleanest".
        return (1 if cls._VARIANT.search(name) else 0, len(name), name)

    def image_url(self, symbol_id, size: int = 300) -> str:
        return f"{self._RAW}/{symbol_id}.svg"  # SVG scales; size is ignored

    def best(self, keyword: str, lang: str = "en") -> Symbol | None:
        self._index()
        keyword = (keyword or "").strip().lower()
        if not keyword or not self._names:
            return None
        if keyword in self._exact:  # exact label match ("house", "money")
            return self._symbol(self._exact[keyword], keyword)
        first = self._tokens.get(keyword)  # keyword is the leading word ("help_,_to")
        if first:
            return self._symbol(min(first, key=self._rank), keyword)
        anywhere = [n for n in self._names if keyword in self._norm(n).split()]
        if anywhere:
            return self._symbol(min(anywhere, key=self._rank), keyword)
        return None

    def search(self, keyword: str, lang: str = "en", limit: int = 12) -> list[Symbol]:
        self._index()
        keyword = (keyword or "").strip().lower()
        if not keyword or not self._names:
            return []
        hits = [n for n in self._names if keyword in self._norm(n).split()]
        hits.sort(key=lambda n: (self._norm(n).split()[0] != keyword, self._rank(n)))
        return [self._symbol(n, self._norm(n)) for n in hits[:limit]]

    def _symbol(self, filename: str, label: str) -> Symbol:
        return Symbol(id=filename, label=label, image_url=self.image_url(filename), provider=self.name)


# --- registry -----------------------------------------------------------------

_PROVIDERS = {"arasaac": ArasaacProvider, "mulberry": MulberryProvider}
_INSTANCES: dict[str, SymbolProvider] = {}


def get_symbol_provider(name: str | None = None) -> SymbolProvider:
    name = (name or os.environ.get("CLARA_SYMBOLS", "arasaac")).lower()
    if name not in _PROVIDERS:
        raise ValueError(f"Unknown symbol set '{name}'. Options: {', '.join(_PROVIDERS)}")
    if name not in _INSTANCES:
        _INSTANCES[name] = _PROVIDERS[name]()
    return _INSTANCES[name]


# --- backward-compatible shims (ARASAAC) --------------------------------------
# Existing callers used these module functions before the provider split; they
# stay ARASAAC-specific so nothing silently changes symbol set underneath them.

def best_id(keyword: str, lang: str = "en", *, timeout: float = 8.0) -> int | None:
    s = ArasaacProvider().best(keyword, lang, timeout=timeout)
    return s.id if s else None


def image_url(pictogram_id: int, size: int = 300) -> str:
    return ArasaacProvider().image_url(pictogram_id, size)


def image_data_uri(pictogram_id: int, size: int = 300, *, timeout: float = 10.0) -> str | None:
    return ArasaacProvider().data_uri(pictogram_id, size, timeout=timeout)
