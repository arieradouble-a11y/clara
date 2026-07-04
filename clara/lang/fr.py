"""French language pack.

Reading ease uses the Kandel-Moles adaptation of Flesch for French
(207 - 1.015*ASL - 73.6*ASW). No validated grade-level formula ships, so grade
is reported as null.
"""
from __future__ import annotations

import re

from .base import LanguagePack

_MONTHS = {
    "janvier": 1, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "août": 8, "septembre": 9, "octobre": 10, "novembre": 11,
    "décembre": 12,
}

_STOP = {
    "le", "la", "les", "un", "une", "des", "de", "du", "au", "aux", "et", "à",
    "en", "que", "qui", "dans", "pour", "par", "sur", "ne", "pas", "se", "ce",
    "cette", "ces", "il", "elle", "ils", "elles", "on", "nous", "vous", "je",
    "tu", "est", "sont", "être", "avec", "plus", "son", "sa", "ses", "leur",
    "leurs", "mais", "ou", "où", "comme", "si", "ils", "y", "d", "l", "qu",
}


class FrenchPack(LanguagePack):
    code = "fr"
    name = "French"

    word_re = re.compile(r"[A-Za-zÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸŒÆàâäçéèêëîïôöùûüÿœæ]+"
                         r"(?:[-'][A-Za-zÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸŒÆàâäçéèêëîïôöùûüÿœæ]+)?")
    sent_re = re.compile(r"[.!?…]+")
    keyword_re = re.compile(r"[A-Za-zÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸŒÆàâäçéèêëîïôöùûüÿœæ]{3,}")
    vowels = "aeiouyàâäéèêëîïôöùûüÿœæ"
    group_vowels = True

    ease_coeffs = (207.0, 1.015, 73.6)  # Kandel-Moles
    grade_coeffs = None

    months = _MONTHS
    negation = ["ne", "pas", "non", "ni", "jamais", "sans", "aucun", "aucune", "rien", "nul"]
    obligation = ["doit", "doivent", "devra", "obligatoire", "nécessaire", "requis", "faut"]
    condition = ["si", "sauf", "sinon", "à moins que", "à condition que", "en cas de"]
    stopwords = _STOP

    pictogram_lang = "fr"
    simplify_note = "Écris en français simple et clair. Réponds uniquement en français."
