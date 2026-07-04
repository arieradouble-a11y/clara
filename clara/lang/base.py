"""A language pack is pure data plus a syllable counter.

The extraction and scoring mechanics live in facts.py, readability.py, and
easyread.py; they read these attributes. Keeping packs data-only means adding a
language is a single self-contained file and never touches the core — the
healthy open-source shape.
"""
from __future__ import annotations

import re


class LanguagePack:
    code = "en"
    name = "English"

    # Tokenization
    word_re = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
    sent_re = re.compile(r"[.!?]+")           # for counting sentences
    keyword_re = re.compile(r"[A-Za-z]{3,}")  # pictogram-keyword candidates
    vowels = "aeiouy"

    # Flesch-style readability: ease = a - b*ASL - c*ASW ; grade = d*ASL + e*ASW - f.
    # grade_coeffs = None means this language ships no validated grade-level metric.
    ease_coeffs: tuple = (206.835, 1.015, 84.6)
    grade_coeffs: tuple | None = (0.39, 11.8, 15.59)

    # Fact-extraction vocabulary
    months: dict = {}
    negation: list = []
    obligation: list = []
    condition: list = []

    # Easy Read
    stopwords: set = set()

    # Integrations
    pictogram_lang = "en"   # ARASAAC locale
    simplify_note = ""      # appended to the simplification system prompt

    def __init__(self):
        self.negation_re = self._markers(self.negation)
        self.obligation_re = self._markers(self.obligation)
        self.condition_re = self._markers(self.condition)

    @staticmethod
    def _markers(words: list) -> re.Pattern:
        if not words:
            return re.compile(r"(?!x)x")  # matches nothing
        alt = "|".join(re.escape(w) for w in words)
        return re.compile(rf"\b(?:{alt})\b", re.IGNORECASE | re.UNICODE)

    def syllables(self, word: str) -> int:
        """Default: one syllable per vowel — right for languages like Russian
        where vowels don't cluster. English overrides this with a heuristic."""
        word = word.lower()
        if not word:
            return 0
        return max(1, sum(1 for ch in word if ch in self.vowels))

    def lemmatize(self, word: str) -> str:
        """Base form of a word, for pictogram lookup. Default is identity;
        inflected languages (Russian) override this."""
        return word
