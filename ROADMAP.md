# Roadmap

Direction for Clara, ordered by what makes the tool *honest and useful on real
documents for real people* — not by what is fun to build. Contributions welcome
on any item; the ones tagged **good first issue** are self-contained.

Found a gap not listed here? Open an issue — real-world documents that break
the faithfulness check are the most valuable bug reports we get.

## Phase 1 — Make the core honest on real inputs — done

The faithfulness checker had known false positives that fire constantly in real
use. These were correctness work, not features. Number words, negation
re-expression, long-document chunking, the eval harness, and identifier suffixes
are all **done**.

- [x] **Number words.** "five hundred" ↔ "500" now compare equal — per-language
  number lexicons in the packs + a shared parser, emitted only for amounts
  (value ≥ 100 or ≥ 2 words) to avoid prose noise. en/ru/es/de. *fr deferred:
  the soixante-dix / quatre-vingts system would misparse (24 for 80) — better to
  not extract than to extract a wrong value; needs a dedicated French parser.*
- [x] **Negation pairs.** "not permitted" → "forbidden" no longer warns — a
  per-language `negation_implicit` list (forbidden/prohibited/запрещено…)
  suppresses the "lost negation" warning when the output re-expresses it.
- [x] **Identifier suffixes.** Alphanumeric IDs ("Form 27A" vs "Form 27B") are
  captured as atomic tokens (`extract_identifiers`) and compared as a hard fact,
  so a changed suffix no longer passes silently. Precision-first: an uppercase
  letter next to a digit is required, which cleanly excludes "2nd", "mp3", "5kg",
  "100km" (the tradeoff is that a lowercase id like "form 27a" isn't caught).
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

## Phase 3 — Easy Read that experts accept — done

- [x] **Reviewer picks the pictogram.** Each Easy Read line's picture is a button;
  clicking it opens a picker that searches the active symbol set (`/pictograms/
  search`) so a reviewer can choose a better symbol or remove it. The choice flows
  into the export and the saved review.
- [x] **Pluggable symbol sets.** `SymbolProvider` interface in `pictograms.py`
  with ARASAAC (CC BY-NC-SA, default) and **Mulberry Symbols** (CC BY-SA,
  commercial-compatible) behind `CLARA_SYMBOLS` / `--symbols`. Mulberry matches a
  bundled label index (no search API); art streams from its CDN.
- [x] **Smarter keyword choice** — pictogram candidates are ranked so likely
  nouns/verbs beat generic modifiers ("large fine" → pictures the fine), via a
  per-pack `soft_stopwords` list + `keyword_rank` hook a real POS tagger can
  override. English list shipped; **good first issue** to add one per language.

## Phase 4 — People (this is a social project)

- [x] **Localize the UIs themselves.** A shared string catalog
  (`clara/data/ui_i18n.json`, 111 keys × en/ru/es/de/fr) served at `/i18n` drives
  both the reference UI (`data-i18n` + a `t()` helper) and the Next app (an
  `I18nProvider`/`useI18n` hook, with the catalog bundled for an instant,
  offline-safe first render). The language selector switches chrome + content
  language and updates `<html lang>`. A parity + drift test guards the catalog.
- [x] **WCAG audit of our own UIs** and a stated conformance level — see
  [ACCESSIBILITY.md](ACCESSIBILITY.md). The reference UI targets **WCAG 2.2 AA**
  (manual audit + accessibility tree + keyboard): language-of-parts on content
  panels, ARIA tabs keyboard pattern, reduced-motion scrolling, verified
  contrast. *Remaining: an automated axe-core CI gate, the Next.js app, and
  testing with real assistive-tech users.*
- [~] **Validation with target readers.** The Easy Read standard (Inclusion
  Europe) requires validation by people with intellectual disabilities. The
  **method is drafted and published** —
  [docs/validation-protocol.md](docs/validation-protocol.md) — but the validation
  itself is human work that **cannot be done in code**: it needs a partner NGO /
  SLP self-advocacy group. Until a round is run and published, the README keeps
  saying "assistive, not authoritative" — and it stays true after, too.
- [x] **Review workflow hardening**: approve/reject now requires an admin or the
  review's assigned validator (`can_approve`), per-review assignment
  (`assign_review` + admin-only `/reviews/assign`, `/auth/users`), login
  rate-limiting (`RateLimitedError` → HTTP 429), and session pruning
  (`prune_sessions`, on startup and each login). Enforced in both servers.

## Phase 5 — Distribution

- [x] **PyPI release** (prepared). `clara` was taken (a 2019 chit-chat utility),
  so the distribution is **`clara-plain`** (import + CLI stay `clara`). Metadata,
  project URLs, classifiers, `CHANGELOG.md`, and a tag-triggered release workflow
  (`.github/workflows/release.yml`, PyPI Trusted Publishing) are in place; the
  wheel builds with the data files bundled. Publishing = push a `v*` tag once the
  PyPI publisher is configured.
- [x] **Docker / compose.** A `Dockerfile` (engine + API) whose default command
  runs the single-process reference server; a multi-stage `web-next/Dockerfile`
  (Next standalone output); and a `docker-compose.yml` wiring uvicorn + Next
  (`CLARA_API` proxy). `.dockerignore` for both.
- [x] **CI hardening**: a `lint` job runs **ruff** (E/F/W/I/B/UP) on
  `clara`/`api`/`web`/`tests`, **mypy** on the engine (`clara`), and a **JS
  syntax check** of the reference UI's inline script (`scripts/check_ui_js.py`,
  which has no build step to catch it otherwise). `pip install -e ".[lint]"`.
- [x] **Public demo instance** (recipe ready). [`render.yaml`](render.yaml) is a
  one-click Render Blueprint deploying the single-process server with the offline
  `mock` provider — no key, no cost; the faithfulness "Check a rewrite" tab is a
  genuine live demo offline. `web/serve.py` honours `$PORT` for hosting.
  *Remaining: click deploy, and add rate-limiting if switching to a real
  provider.*

## Phase 6 — LLM accessibility layer

Clara's pipeline generalises beyond documents. LLMs are rapidly becoming how
people get information — and access to *them* is uneven: answers are walls of
text, prompting is a cognitive skill, voice modes exclude people with speech
disabilities. Same principles apply: assistive, verified, honest.

- [x] **clara-proxy.** An OpenAI-compatible endpoint (`POST /v1/chat/completions`,
  `GET /v1/models`) between any chat client and any provider: the upstream
  answer is simplified to the chosen reading level and checked by the
  deterministic faithfulness layer before the person sees it. Level via the
  model name (`clara-plain`, `clara-easy-read`, `clara-grade-7`) or
  `CLARA_PROXY_*` env; a `clara` extension block carries the report and the
  unmodified original; lost facts append a localized plain-language warning;
  streaming is emulated. Providers grew a native multi-turn `chat()`.
- [x] **Accessibility profile.** A small portable JSON spec — the LLM equivalent
  of OS-level accessibility settings, which today don't exist anywhere. Spec +
  JSON Schema in [docs/accessibility-profile.md](docs/accessibility-profile.md);
  reference implementation in `clara/profile.py` (dependency-free on purpose).
  Two modes: **A** — `clara profile render` produces instructions to paste into
  any chat client (a request); **B** — clara-proxy enforces the reading fields
  through the verified simplify pass, injects format/language wishes upstream,
  reports `profile_applied`, and fails loudly on a broken `CLARA_PROFILE` file.
  *Next: circulate the draft for feedback from AT users and partner orgs.*
- [x] **Pictogram prompt builder.** Input, not just output: the reference UI's
  **Ask** tab is an AAC-style symbol board (curated core vocabulary in
  `clara/data/board.json`, labels in all five languages, pictures resolved
  through the symbol providers — fully offline with Mulberry). Taps compose a
  telegraphic question; an AAC-aware system prompt tells the model to interpret
  it kindly; the answer comes back as **Easy Read lines with pictograms** and
  per-line read-aloud — accessible in, accessible out. `GET /board`, `POST
  /ask` on both servers. *Next: bring the board to the Next app; grow the
  vocabulary with validator feedback.*
- [ ] **Barriers research.** With partner disability organisations, document how
  people with different disabilities actually experience LLM chat interfaces;
  publish the findings. Feeds the profile spec and the proxy defaults.

## Non-goals (for now)

- Replacing human review — the whole design assumes a person signs off.
- Fabricated metrics: languages without a validated grade-level formula keep
  reporting `null`. That stays.
- Heavy NLP dependencies in the core: everything beyond `httpx` remains an
  optional extra with graceful fallback.
