---
name: Language pack
about: Add or improve support for a language
labels: language-pack
---

**Language**
Name and ISO code (e.g. Italian / `it`).

**Readability formula**
Is there a *validated* Flesch-style adaptation for this language? Please link a
source and give the coefficients (average sentence length and syllables-per-word
terms). If there's no validated grade-level formula, that's fine — we ship
reading-ease only and set `grade_coeffs = None` rather than inventing one.

**Pictograms**
Does ARASAAC have this locale? Does the language need lemmatization for pictogram
matching (does simplemma support it)?

**Offering to submit a PR?**
See CONTRIBUTING.md → "Adding a language pack". Happy to help review.
