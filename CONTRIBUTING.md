# Contributing to Clara

Thanks for helping make dense text readable for people who are shut out by it.
Issues and pull requests are welcome — **especially language packs** and
real-world documents that break the faithfulness check (those are gold).

## Principles a change should respect

These are what make Clara trustworthy — please keep them:

1. **Faithfulness over fluency.** The deterministic check (numbers, dates,
   negations) must keep working. If you touch simplification, don't weaken it.
2. **Human-in-the-loop.** Clara assists authors and reviewers; it is not an
   oracle. Features should support review, not replace it.
3. **Don't fabricate data.** If a readability coefficient, a formula, or a
   dataset isn't validated, ship the part you can and report the gap (e.g. set
   `grade_coeffs = None`) rather than inventing a number. There are several
   examples of this in the codebase and README — follow them.
4. **Keep the core light.** The engine's only hard dependency is `httpx`. New
   capabilities that need a library go behind an optional extra with a graceful
   fallback when it's absent.

## Dev setup

```bash
git clone https://github.com/arieradouble-a11y/clara
cd clara
pip install -e ".[dev]"
python -m pytest -q          # tests are offline and hermetic
```

Run the reference UI (zero dependencies):

```bash
py web/serve.py              # http://localhost:8000
```

Or the Next.js app (see `web-next/README.md`).

## Adding a language pack

This is the most valuable contribution. A pack is one file, `clara/lang/<code>.py`:

1. Copy an existing pack (`es.py` is a good template) and set: `code`, `name`,
   `word_re`, `sent_re`, `keyword_re`, `vowels`, `months`, negation/obligation/
   condition words, `stopwords`, `pictogram_lang`, `simplify_note`.
2. **Readability coefficients** (`ease_coeffs`, `grade_coeffs`): use a
   *validated* adaptation of Flesch for the language, and **cite the source in a
   docstring**. If there is no validated grade-level formula, set
   `grade_coeffs = None` — do not invent one.
3. Set `group_vowels = True` if the language has diphthongs (Latin/Germanic);
   leave it off for languages where every vowel is a syllable (e.g. Russian).
4. Optional lemmatization for pictogram matching: set `use_simplemma = True`
   (simplemma covers many languages) and add the language to the extras in
   `pyproject.toml`. Russian uses pymorphy3 instead — see `ru.py`.
5. Register the pack in `clara/lang/__init__.py`.
6. Add tests to `tests/test_lang.py` (reading ease, dates, markers, lemmatize).

## Pull requests

- Match the style of the surrounding code (naming, comment density, idioms).
- Add or update tests; `python -m pytest -q` must pass. CI runs the suite plus
  a `web-next` build.
- One focused change per PR. Describe what and why.

By contributing you agree your work is licensed under the project's MIT license.
