"""Language pack registry.

    from clara.lang import get_pack
    pack = get_pack("ru")

Add a language by dropping a module in this package and registering its class in
_CLASSES — nothing else in the core needs to change.
"""
from __future__ import annotations

from .base import LanguagePack
from .en import EnglishPack
from .ru import RussianPack

_CLASSES = {"en": EnglishPack, "ru": RussianPack}
_PACKS: dict = {}


def get_pack(code: str | None = None) -> LanguagePack:
    code = (code or "en").lower()
    cls = _CLASSES.get(code)
    if cls is None:
        raise ValueError(f"Unknown language '{code}'. Available: {', '.join(_CLASSES)}")
    if code not in _PACKS:
        _PACKS[code] = cls()
    return _PACKS[code]


def available() -> list[str]:
    return list(_CLASSES)


__all__ = ["LanguagePack", "get_pack", "available"]
