# Roadmap

Direction for Clara, ordered by what makes the tool *honest and useful on real
documents for real people* — not by what is fun to build. Contributions welcome
on any item; the ones tagged **good first issue** are self-contained.

Found a gap not listed here? Open an issue — real-world documents that break
the faithfulness check are the most valuable bug reports we get.

## Phase 1 — Make the core honest on real inputs

The faithfulness checker has known false positives that will fire constantly in
real use. These are correctness work, not features.

- [ ] **Number words.** Plain language spells numbers out; the checker only sees
  digits. "five hundred" → "500" is flagged as *invented*; "500" → "five
  hundred" as *dropped*. Fix: per-language number-word lexicons in the language
  packs (data-only, fits the pack architecture), normalized before inventory.
  en/ru/es/de/fr.
- [ ] **Negation pairs.** Removing a double negative ("not permitted" →
  "forbidden") is a classic simplification and currently warns. Fix: a small
  per-language antonym/negated-form list so the warning only fires on genuine
  polarity loss.
- [ ] **Identifier noise.** "Form 27B", "office 14" are counted as quantities.
  Fix: exclude numbers glued to identifiers (letter suffixes, "No.", "form/
  office/room" contexts) from the quantity inventory — they still must survive,
  but as identifiers, not amounts.
- [ ] **Long documents.** `simplify` sends the whole text in one call;
  `max_tokens` truncates long PDFs mid-document. Fix: chunk by paragraphs/
  sections, simplify + verify per chunk, merge results. This is the blocker for
  "ingest a real 20-page notice".
- [ ] **Evaluation harness.** A golden set of (source → known-good rewrite)
  pairs per language; CI measures checker precision/recall and catches prompt
  or model regressions. Start tiny (20 pairs/language), grow from issues.

## Phase 2 — Real documents in, real documents out

- [ ] **OCR for scanned PDFs** (`ocrmypdf`/tesseract behind an `[ocr]` extra) —
  official notices in the wild are very often scans.
- [ ] **Structure preservation.** Headings and lists from DOCX/HTML currently
  flatten to paragraphs; carry them through simplification into the exported
  HTML/PDF (h2/h3, ul/ol).
- [ ] **Semantic check with a second opinion.** Allow the semantic faithfulness
  check to run on a *different* provider than the one that simplified
  (anti-self-grading). One parameter, honest win.

## Phase 3 — Easy Read that experts accept

- [ ] **Reviewer picks the pictogram.** The keyword is already returned; add UI
  to click a picture and choose among ARASAAC alternatives (search endpoint).
- [ ] **Pluggable symbol sets.** ARASAAC is CC BY-NC-SA (non-commercial). Add a
  provider interface + Mulberry Symbols (CC BY-SA) as a commercial-compatible
  alternative. The source is already isolated in `pictograms.py`.
- [ ] **Smarter keyword choice** — prefer nouns/verbs over "first content word"
  (POS tagging where a light tagger exists). **good first issue** per language.

## Phase 4 — People (this is a social project)

- [ ] **Localize the UIs themselves.** The chrome is English-only — ironic for
  an accessibility tool. Dictionary-based UI strings for ru/es/de/fr in both
  the reference UI and the Next app.
- [ ] **WCAG audit of our own UIs** (axe + keyboard + screen reader pass) and a
  stated conformance level. An accessibility tool must dogfood accessibility.
- [ ] **Validation with target readers.** The Easy Read standard (Inclusion
  Europe) requires validation by people with intellectual disabilities. Find a
  partner NGO / SLP group, run a small validation protocol, publish the
  method and findings. Until then the README must keep saying "assistive, not
  authoritative" — and it will stay true after, too.
- [ ] **Review workflow hardening**: enforce roles (approve = admin/assigned
  validator), per-review assignment, login rate-limiting, session pruning.

## Phase 5 — Distribution

- [ ] **PyPI release.** Check name availability first ("clara" is likely taken;
  candidate: `clara-plain`). Versioning + CHANGELOG + GitHub Releases.
- [ ] **Docker / compose** for the two-process setup (uvicorn + Next) and a
  single-process option (`web/serve.py`).
- [ ] **CI hardening**: ruff + mypy on the engine, JS syntax check for the
  reference UI. **good first issue**
- [ ] **Public demo instance** (mock or rate-limited provider) so people can
  try it without installing.

## Non-goals (for now)

- Replacing human review — the whole design assumes a person signs off.
- Fabricated metrics: languages without a validated grade-level formula keep
  reporting `null`. That stays.
- Heavy NLP dependencies in the core: everything beyond `httpx` remains an
  optional extra with graceful fallback.
