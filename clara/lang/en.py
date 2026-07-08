"""English language pack (the default)."""
from __future__ import annotations

from .base import LanguagePack

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12, "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}

_STOP = {
    "the", "a", "an", "you", "your", "i", "we", "they", "he", "she", "it", "this",
    "that", "these", "those", "and", "or", "but", "if", "unless", "of", "to", "in",
    "on", "at", "by", "for", "with", "from", "as", "is", "are", "was", "were", "be",
    "been", "being", "do", "does", "did", "have", "has", "had", "will", "shall",
    "must", "may", "can", "should", "would", "could", "not", "no", "than", "then",
    "there", "here", "who", "what", "when", "where", "how", "any", "all", "some",
    "one", "please",
}


class EnglishPack(LanguagePack):
    code = "en"
    name = "English"

    ease_coeffs = (206.835, 1.015, 84.6)   # Flesch Reading Ease
    grade_coeffs = (0.39, 11.8, 15.59)     # Flesch-Kincaid Grade Level

    months = _MONTHS
    negation = ["not", "no", "never", "cannot", "can't", "won't", "don't",
                "doesn't", "didn't", "without", "neither", "nor"]
    obligation = ["must", "shall", "required", "mandatory", "obliged",
                  "obligated", "have to", "has to"]
    condition = ["if", "unless", "except", "provided that", "only if",
                 "in case", "subject to"]
    stopwords = _STOP

    number_units = {
        "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
        "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
        "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
        "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
        "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    }
    number_scales = {"hundred": 100, "thousand": 1000, "million": 1_000_000, "billion": 1_000_000_000}
    number_join = {"and"}

    pictogram_lang = "en"

    def syllables(self, word: str) -> int:
        word = word.lower()
        if not word:
            return 0
        count, prev_vowel = 0, False
        for ch in word:
            is_vowel = ch in "aeiouy"
            if is_vowel and not prev_vowel:
                count += 1
            prev_vowel = is_vowel
        if word.endswith("e") and count > 1:
            count -= 1
        if word.endswith("le") and len(word) > 2 and word[-3] not in "aeiouy":
            count += 1
        return max(1, count)
