# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The PyPI distribution is **`clara-plain`** (the name `clara` was taken); the
import package and CLI command stay `clara`.

## [Unreleased]

### Added
- **Ingestion:** OCR for scanned PDFs behind the `[ocr]` extra (ocrmypdf /
  tesseract), with `--ocr auto|force|off` and honest degradation when the extra
  is absent.
- **Structure preservation:** headings and lists from HTML/DOCX are carried
  through simplification into the exported HTML/PDF (`h2`/`h3`, `ul`/`ol`) via a
  `Block` model, instead of flattening to paragraphs.
- **Semantic check second opinion:** the LLM faithfulness check can run on an
  independent provider (`CLARA_CHECK_PROVIDER` / `--check-provider`) so a model
  never grades its own rewrite.
- **Pluggable symbol sets:** a `SymbolProvider` interface with ARASAAC (default,
  CC BY-NC-SA) and Mulberry Symbols (CC BY-SA, commercial-compatible), selected
  with `CLARA_SYMBOLS` / `--symbols`.
- **Reviewer picks the pictogram:** each Easy Read line's picture is a button
  that opens a symbol search (`/pictograms/search`); the choice flows into the
  export and the saved review.
- **Smarter keyword choice:** pictogram candidates rank likely nouns/verbs above
  generic modifiers (per-pack `soft_stopwords` + `keyword_rank`).
- **Review workflow hardening:** roles (approve/reject = admin or assigned
  validator), per-review assignment, login rate-limiting, and session pruning.
- **UI localization:** en/ru/es/de/fr across both the reference UI and the Next
  app, from one shared catalog served at `/i18n`.
- **Accessibility:** WCAG 2.2 AA self-audit of the reference UI and a stated
  conformance level (`ACCESSIBILITY.md`).
- **Docs:** `docs/validation-protocol.md` — the Easy Read validation method
  (execution requires a partner organisation and is not yet done).

### Fixed
- Faithfulness false positives on spelled-out numbers and re-expressed negations.
- Changed identifier suffixes (`Form 27A` vs `27B`) are now caught as a hard fact
  rather than passing silently.
- Long documents are chunked so they are not truncated mid-document.

### Notes
- Clara remains **assistive, not authoritative**: the design assumes a human
  signs off, and Easy Read output is not yet validated with target readers.
