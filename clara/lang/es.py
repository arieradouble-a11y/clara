"""Spanish language pack.

Reading ease uses Szigriszt-Pazos (206.835 - ASL - 62.3*ASW), the basis of the
INFLESZ scale widely used for Spanish plain-language and health texts — and it
fits the words-per-sentence / syllables-per-word form. No validated grade-level
formula ships, so grade is reported as null rather than fabricated. ARASAAC is
Spanish in origin, so pictogram coverage is excellent.
"""
from __future__ import annotations

import re

from .base import LanguagePack

_MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

_STOP = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al",
    "que", "y", "a", "en", "por", "con", "su", "sus", "para", "como", "más",
    "o", "u", "este", "esta", "esto", "ese", "esa", "eso", "se", "lo", "le",
    "les", "me", "mi", "tu", "te", "no", "sí", "es", "son", "ser", "está",
    "están", "hay", "muy", "ya", "pero", "porque", "cuando", "sobre", "entre",
    "hasta", "desde", "también", "todo", "toda", "todos", "todas", "cada",
}


class SpanishPack(LanguagePack):
    code = "es"
    name = "Spanish"

    word_re = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:-[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)?")
    sent_re = re.compile(r"[.!?…]+")
    keyword_re = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3,}")
    vowels = "aeiouáéíóúü"
    group_vowels = True

    ease_coeffs = (206.835, 1.0, 62.3)  # Szigriszt-Pazos (INFLESZ)
    grade_coeffs = None

    months = _MONTHS
    negation = ["no", "ni", "nunca", "nada", "sin", "tampoco", "jamás"]
    obligation = ["debe", "deben", "deberá", "obligatorio", "obligatoria",
                  "necesario", "necesaria", "requiere", "tiene que", "tienen que"]
    condition = ["si", "salvo", "excepto", "a menos que", "siempre que", "en caso de"]
    stopwords = _STOP

    pictogram_lang = "es"
    simplify_note = "Escribe en español claro y sencillo. Responde solo en español."
    use_simplemma = True
