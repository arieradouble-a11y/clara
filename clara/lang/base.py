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
    # Words that carry negative polarity without an explicit "not" (forbidden,
    # prohibited…). If the output uses one, a dropped "not" was likely just
    # re-expressed, so we don't warn about lost negation.
    negation_implicit: list = []
    obligation: list = []
    condition: list = []

    # Spelled-out numbers, so "five hundred" and "500" compare equal. Empty =
    # no number-word extraction for this language (safe default). units holds
    # atomic values (0-19, tens, and in some languages the hundreds); scales
    # multiply (hundred/thousand/…); join words ("and") may sit inside a run.
    number_units: dict = {}
    number_scales: dict = {}
    number_join: set = set()

    # Easy Read
    stopwords: set = set()
    # Content words that make poor pictogram anchors — generic modifiers and
    # quantifiers (adjectives/adverbs) that a picture can't usefully depict. They
    # are demoted, not dropped, so a noun/verb in the same line wins the picture
    # but an adjective is still used when it's the only candidate with a symbol.
    # Empty by default; per-language lists are a good first issue.
    soft_stopwords: set = set()

    # Syllable counting: count vowel GROUPS (consecutive vowels = 1, right for
    # languages with diphthongs like Spanish/French/German) vs each vowel
    # (right for Russian). English overrides syllables() entirely.
    group_vowels = False

    # Integrations
    pictogram_lang = "en"   # ARASAAC locale
    simplify_note = ""      # appended to the simplification system prompt
    use_simplemma = False   # Latin-script packs opt into simplemma lemmatization

    def __init__(self):
        self.negation_re = self._markers(self.negation)
        self.negation_implicit_re = self._markers(self.negation_implicit)
        self.obligation_re = self._markers(self.obligation)
        self.condition_re = self._markers(self.condition)

    @staticmethod
    def _markers(words: list) -> re.Pattern:
        if not words:
            return re.compile(r"(?!x)x")  # matches nothing
        alt = "|".join(re.escape(w) for w in words)
        return re.compile(rf"\b(?:{alt})\b", re.IGNORECASE | re.UNICODE)

    def syllables(self, word: str) -> int:
        """One syllable per vowel (Russian), or per vowel group when
        group_vowels is set (Spanish/French/German). English overrides this."""
        word = word.lower()
        if not word:
            return 0
        if self.group_vowels:
            count, prev_vowel = 0, False
            for ch in word:
                is_vowel = ch in self.vowels
                if is_vowel and not prev_vowel:
                    count += 1
                prev_vowel = is_vowel
            return max(1, count)
        return max(1, sum(1 for ch in word if ch in self.vowels))

    def keyword_rank(self, word: str) -> int:
        """Pictogram-keyword priority: 0 prefers likely nouns/verbs, 1 demotes
        generic modifiers. Candidates are tried in this order and the first with a
        symbol wins. A pack with a light POS tagger can override this to rank by
        real part of speech instead of the soft-stopword list."""
        return 1 if word.lower() in self.soft_stopwords else 0

    def lemmatize(self, word: str) -> str:
        """Base form of a word, for pictogram lookup. Identity by default; the
        Latin-script packs opt into simplemma via use_simplemma, and Russian
        overrides this with pymorphy3. Soft-fails to the raw word."""
        if not self.use_simplemma:
            return word
        try:
            import simplemma

            return simplemma.lemmatize(word, lang=self.code)
        except Exception:
            return word
