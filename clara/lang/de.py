"""German language pack.

Reading ease uses the Amstad adaptation of Flesch for German
(180 - ASL - 58.5*ASW), which accounts for German's longer words. No validated
grade-level formula ships, so grade is reported as null.
"""
from __future__ import annotations

import re

from .base import LanguagePack

_MONTHS = {
    "januar": 1, "februar": 2, "märz": 3, "april": 4, "mai": 5, "juni": 6,
    "juli": 7, "august": 8, "september": 9, "oktober": 10, "november": 11,
    "dezember": 12,
}

_STOP = {
    "der", "die", "das", "und", "in", "zu", "den", "dem", "mit", "sich", "des",
    "auf", "für", "ist", "im", "ein", "eine", "einen", "einem", "einer", "als",
    "auch", "es", "an", "aus", "er", "sie", "wir", "hat", "dass", "nach", "bei",
    "um", "am", "sind", "noch", "wie", "über", "so", "zum", "zur", "war", "nur",
    "vor", "bis", "durch", "man", "sein", "von", "oder", "aber", "mehr", "dann",
}


class GermanPack(LanguagePack):
    code = "de"
    name = "German"

    word_re = re.compile(r"[A-Za-zÄÖÜäöüß]+(?:-[A-Za-zÄÖÜäöüß]+)?")
    sent_re = re.compile(r"[.!?…]+")
    keyword_re = re.compile(r"[A-Za-zÄÖÜäöüß]{3,}")
    vowels = "aeiouäöü"
    group_vowels = True

    ease_coeffs = (180.0, 1.0, 58.5)  # Amstad (Flesch for German)
    grade_coeffs = None

    months = _MONTHS
    negation = ["nicht", "kein", "keine", "keinen", "nie", "niemals", "ohne",
                "weder", "nichts"]
    obligation = ["muss", "müssen", "soll", "sollen", "erforderlich",
                  "verpflichtet", "notwendig"]
    condition = ["wenn", "falls", "außer", "sofern", "es sei denn"]
    stopwords = _STOP

    pictogram_lang = "de"
    simplify_note = "Schreibe in einfacher, klarer Sprache. Antworte nur auf Deutsch."
    use_simplemma = True
