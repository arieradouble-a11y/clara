"""Readability scoring, parameterized by language pack.

The formula is Flesch-style for every language but the coefficients differ:
English uses classic Flesch / Flesch-Kincaid; Russian uses the Oborneva
adaptation. A language whose grade-level formula is not validated reports
``flesch_kincaid_grade = None`` rather than a fabricated number.
"""
from __future__ import annotations

from dataclasses import dataclass

from .lang import get_pack


def count_syllables(word: str, lang: str = "en") -> int:
    return get_pack(lang).syllables(word)


@dataclass
class Readability:
    words: int
    sentences: int
    syllables: int
    flesch_reading_ease: float      # higher = easier
    flesch_kincaid_grade: float | None  # school grade; None if not validated for the language


def analyze(text: str, lang: str = "en") -> Readability:
    pack = get_pack(lang)
    words = pack.word_re.findall(text or "")
    n_words = len(words)
    sentences = [s for s in pack.sent_re.split(text or "") if s.strip()]
    n_sent = max(1, len(sentences))
    n_syll = sum(pack.syllables(w) for w in words) or 1

    if n_words == 0:
        grade = None if pack.grade_coeffs is None else 0.0
        return Readability(0, n_sent, 0, 0.0, grade)

    words_per_sentence = n_words / n_sent
    syllables_per_word = n_syll / n_words
    a, b, c = pack.ease_coeffs
    ease = round(a - b * words_per_sentence - c * syllables_per_word, 1)

    grade = None
    if pack.grade_coeffs is not None:
        d, e, f = pack.grade_coeffs
        grade = round(d * words_per_sentence + e * syllables_per_word - f, 1)

    return Readability(n_words, n_sent, n_syll, ease, grade)
