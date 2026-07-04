"""Readability scoring. English-first (Flesch), structured so other languages
plug in their own metric via a language pack.

We implement the formulas ourselves (rather than pull a dependency) so the
scoring is transparent and easy to extend per language — the metric that reads
well for English does not for every language.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_WORD = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
_SENT = re.compile(r"[.!?]+")


def count_syllables(word: str) -> int:
    """Heuristic English syllable count: count vowel groups, drop a silent
    trailing 'e', but keep the syllable a consonant+'le' ending adds
    ('sim-ple', 'ta-ble'). Floor at 1."""
    word = word.lower()
    if not word:
        return 0
    vowels = "aeiouy"
    count, prev_vowel = 0, False
    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if word.endswith("e") and count > 1:
        count -= 1
    if word.endswith("le") and len(word) > 2 and word[-3] not in vowels:
        count += 1
    return max(1, count)


@dataclass
class Readability:
    words: int
    sentences: int
    syllables: int
    flesch_reading_ease: float   # higher = easier (0-100+)
    flesch_kincaid_grade: float  # US school grade level (lower = easier)


def analyze(text: str) -> Readability:
    words = _WORD.findall(text or "")
    n_words = len(words)
    sentences = [s for s in _SENT.split(text or "") if s.strip()]
    n_sent = max(1, len(sentences))
    n_syll = sum(count_syllables(w) for w in words) or 1
    if n_words == 0:
        return Readability(0, n_sent, 0, 0.0, 0.0)

    words_per_sentence = n_words / n_sent
    syllables_per_word = n_syll / n_words
    fre = 206.835 - 1.015 * words_per_sentence - 84.6 * syllables_per_word
    fk = 0.39 * words_per_sentence + 11.8 * syllables_per_word - 15.59
    return Readability(n_words, n_sent, n_syll, round(fre, 1), round(fk, 1))
