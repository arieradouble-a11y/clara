# Roadmap

Direction for Clara, ordered by what makes the tool *honest and useful on real
documents for real people* — not by what is fun to build. Contributions welcome
on any item; the ones tagged **good first issue** are self-contained.

Found a gap not listed here? Open an issue — real-world documents that break
the faithfulness check are the most valuable bug reports we get.

## Phase 1 — Make the core honest on real inputs — mostly done

The faithfulness checker had known false positives that fire constantly in real
use. These were correctness work, not features. Number words, negation
re-expression, long-document chunking, and the eval harness are **done**; only
identifier suffixes remain (lower priority — see below).

- [x] **Number words.** "five hundred" ↔ "500" now compare equal — per-language
  number lexicons in the packs + a shared parser, emitted only for amounts
  (value ≥ 100 or ≥ 2 words) to avoid prose noise. en/ru/es/de. *fr deferred:
  the soixante-dix / quatre-vingts system would misparse (24 for 80) — better to
  not extract than to extract a wrong value; needs a dedicated French parser.*
- [x] **Negation pairs.** "not permitted" → "forbidden" no longer warns — a
  per-language `negation_implicit` list (forbidden/prohibited/запрещено…)
  suppresses the "lost negation" warning when the output re-expresses it.
- [ ] **Identifier suffixes** (lower priority). "27B" reduces to "27", so
  "Form 27A" vs "Form 27B" compare equal (a *missed difference*, not a false
  positive — IDs otherwise match on both sides). Capture alphanumeric IDs as
  atomic tokens, but carefully — naive matching also grabs "2nd", "mp3".
- [x] **Long documents.** `simplify` now splits text on paragraph (then
  sentence) boundaries into chunks under `_CHUNK_CHARS`, simplifies each, and
  rejoins — so a long PDF isn't truncated mid-document by `max_tokens`. Short
  text is still one call. Faithfulness/readability run on the full source vs
  full output.
- [x] **Evaluation harness.** `tests/test_eval.py` pins the checker against a
  golden set — faithful pairs must come back clean (precision), unfaithful ones
  must be caught (recall). No model needed; it guards the deterministic layer in
  CI. Started at 15 cases across en/ru/es/de — grow it from real documents.

## Phase 2 — Real documents in, real documents out — done

- [x] **OCR for scanned PDFs** (`ocrmypdf`/tesseract behind an `[ocr]` extra) —
  official notices in the wild are very often scans. `from_pdf` detects a missing
  text layer (`_needs_ocr`) and OCRs it; `--ocr auto|force|off`. Degrades honestly
  when the extra isn't installed.
- [x] **Structure preservation.** Headings and lists from DOCX/HTML are carried
  through simplification into the exported HTML/PDF (h2/h3, ul/ol) via a `Block`
  model (`clara/structure.py`) instead of flattening to paragraphs. `simplify
  --html` preserves structure automatically; `--flatten` opts out. Faithfulness
  and readability still run on the flattened text.
- [x] **Semantic check with a second opinion.** The semantic faithfulness check
  can run on a *different* provider than the one that simplified
  (anti-self-grading) via `CLARA_CHECK_PROVIDER` / `--check-provider`. Falls back
  to the simplify provider when no second one is configured.

## Phase 3 — Easy Read that experts accept

- [ ] **Reviewer picks the pictogram.** The keyword is already returned; add UI
  to click a picture and choose among ARASAAC alternatives (search endpoint).
- [x] **Pluggable symbol sets.** `SymbolProvider` interface in `pictograms.py`
  with ARASAAC (CC BY-NC-SA, default) and **Mulberry Symbols** (CC BY-SA,
  commercial-compatible) behind `CLARA_SYMBOLS` / `--symbols`. Mulberry matches a
  bundled label index (no search API); art streams from its CDN.
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
