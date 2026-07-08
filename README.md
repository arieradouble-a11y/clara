# Clara

[![CI](https://github.com/arieradouble-a11y/clara/actions/workflows/ci.yml/badge.svg)](https://github.com/arieradouble-a11y/clara/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Turn complex text into verified plain language.**

Clara rewrites bureaucratic, legal, and medical text into clearer language for
people who are shut out by dense prose — readers with cognitive disabilities,
aphasia after a stroke, intellectual disabilities, low literacy, or limited
proficiency in the language. It is open source, self-hostable, and multilingual
by design.

Any model can shorten text. What makes Clara different is that it **checks the
result did not lie**: dropped deadlines, flipped negations, and invented numbers
are caught deterministically and flagged for a human.

> **Status:** early alpha. The core engine (simplify → verify → score) runs and
> is tested. PDF ingestion, Easy Read image pairing, tagged-PDF output, a review
> workflow, and the web UI are on the roadmap below.

---

## Why this is not "just a wrapper around an LLM"

Two design commitments carry the project:

### 1. A faithfulness layer, not blind trust
Simplifying a law or a medical instruction is dangerous precisely where it
matters: the model can drop a deadline, an amount, or a condition, or **invert a
negation** ("you must not" → "you must"). Clara extracts the hard facts from the
source — numbers, money, percentages, dates, and alphanumeric identifiers
("Form 27A" vs "27B") — **without an LLM**, then verifies each one survived in the
output. A mismatch is a reproducible signal, not an opinion. Negations,
obligations (`must`/`shall`), and conditions (`if`/`unless`) are inventoried too
and raised as review warnings.

On top of that deterministic layer, an **optional LLM semantic check**
(`clara/semantic.py`; `--semantic` on the CLI, or the "Run AI semantic check"
button) compares source and output for meaning drift the regexes can't see — a
weakened obligation, a changed condition, an added implication — and returns
typed issues (omission / addition / contradiction / distortion). It costs a model
call, so it is opt-in, and it degrades to "unavailable" rather than guessing when
no capable provider answers.

By default the check can run on an **independent grader** so a model never grades
its own rewrite (models tend to approve their own output). Set
`CLARA_CHECK_PROVIDER` — or pass `--check-provider` — to point the semantic check
at a different provider than the one that did the simplification.

### 2. Human-in-the-loop by principle
The Easy Read standard (Inclusion Europe) asks that simplified text be validated
by the people it is for. Clara is built to **assist authors and reviewers**, not
to be an oracle. It shows the original next to the rewrite with drift
highlighted and expects a human to approve — which is both the ethical stance
and the reason it can be trusted with legal and medical content.

---

## Quickstart

```bash
git clone <this repo>
cd clara
pip install -e ".[dev]"

# Runs offline out of the box (mock provider echoes the text) — proves the pipeline:
clara simplify --text "Applicants must submit form 27B by 2024-01-31 unless exempt."

# Use a real model:
CLARA_PROVIDER=anthropic ANTHROPIC_API_KEY=sk-... \
  clara simplify --file notice.txt --level easy_read
```

Example output:

```
--- Simplified (plain) ---
You must send form 27B by 31 January 2024. You do not have to if you are exempt.

Readability : grade 12.4 -> 5.1   (Flesch ease 31.0 -> 82.0)
Faithfulness: OK - all numbers and dates preserved.
```

If the model had dropped the date, you'd see:

```
Faithfulness: REVIEW
  Dropped dates: 2024-01-31
```

### As a library

```python
from clara import simplify_text

res = simplify_text("Long legal paragraph...", level="plain")
print(res.simplified)
print(res.output_readability.flesch_kincaid_grade)
print(res.faithfulness.ok, res.faithfulness.warnings)
```

### Reference UI (web)

A zero-dependency reviewer — no Node toolchain, no build step, no API key:

```bash
py web/serve.py            # http://localhost:8000
```

Two modes, side by side with drift highlighted:
- **Simplify** — source → model → simplified + faithfulness report.
- **Check a rewrite** — paste an original and any plain-language rewrite; get the
  faithfulness report. Needs no model and works fully offline.

For a richer application there is a **Next.js app** in [`web-next/`](web-next/)
(App Router + TypeScript) that talks to the FastAPI backend through a proxy
route — see its README to run it.

### As an HTTP API

```bash
pip install -e ".[api]"
uvicorn api.main:app --reload
# GET  /            reference UI
# POST /simplify    {"text": "...", "level": "plain"}
# POST /verify      {"source": "...", "output": "..."}   (no LLM, offline)
```

---

## Output levels

These are genuinely different audiences — Clara keeps them distinct:

| Level        | Standard              | For                                         |
|--------------|-----------------------|---------------------------------------------|
| `plain`      | Plain Language (ISO 24495-1) | general cognitive load, wide public  |
| `easy_read`  | Easy Read / E2R       | intellectual disabilities (one idea/line)   |
| `grade`      | target reading grade  | e.g. WCAG AAA ≈ grade 5 (`--grade 5`)       |

---

## Easy Read + pictograms

Easy Read lays the text out one idea per line and pairs each line with a
pictogram — the format the standard uses for readers with intellectual
disabilities. The text still goes through the faithfulness check; a picture
never excuses a dropped fact.

```bash
clara easyread --text "Applicants must submit Form 27B by 2024-01-31."
# → each line with a matched pictogram id, keyword, and image URL

# In the web UI, pick the "Easy Read" level to see the picture layout.
```

Pictograms come from a pluggable **symbol set**. Two ship today, chosen with
`CLARA_SYMBOLS` or `easyread --symbols`:

- **ARASAAC** (default) — ~13k multilingual symbols with a real search API, so a
  reviewer can browse alternatives. **CC BY-NC-SA** (non-commercial).
- **Mulberry** — ~3.4k English SVGs, **CC BY-SA** (commercial-compatible). No
  search API, so matching uses a bundled label index; the art is fetched from the
  Mulberry CDN and cached.

Matching is best-effort, so the picture is a suggestion, not a verdict: in the
reference UI each Easy Read line's picture is a button — a reviewer clicks it to
search the symbol set for a better match or remove it, and the choice flows into
the exported document and the saved review. Lookups are cached on disk and fail
soft — if the set is unreachable the text still works, just without pictures.

Inflected languages are lemmatized before lookup so more words match: Russian via
pymorphy3 (`pip install "clara[ru]"`), Spanish/German/French via simplemma
(`clara[es]` / `clara[de]` / `clara[fr]`). Without the optional dependency it
falls back to the raw word.

> **Attribution & licensing.** ARASAAC pictograms are the property of the
> Government of Aragón, created by Sergio Palao, licensed **CC BY-NC-SA**. The
> **non-commercial** clause carries downstream: if you build a commercial product,
> switch to `CLARA_SYMBOLS=mulberry` — Mulberry Symbols (by Steve Lee / Straight
> Street) are **CC BY-SA**, which permits commercial use with attribution.
> Symbol sets are providers in `clara/pictograms.py`; add another by implementing
> `SymbolProvider`.

---

## Ingestion

Feed real documents in, not just pasted text. `--file` dispatches by extension
and `--url` fetches and extracts the main text; the web UI has "Import URL" and
"Import file".

```bash
clara simplify --file notice.pdf
clara easyread --url https://example.gov/notice --lang en
```

- **Plain text / HTML** — always available (HTML uses a stdlib fallback;
  `trafilatura` gives cleaner main-content extraction when installed).
- **URL** — fetched with stdlib `urllib` (no extra dependency).
- **PDF (pypdf) / DOCX (python-docx)** — `pip install "clara[ingest]"`. Without
  the library the call returns a clear message instead of a broken result.
- **Scanned PDFs (OCR)** — `pip install "clara[ocr]"` (plus the `tesseract`
  binary). When a PDF has no usable text layer — an official notice that's really
  a photo of paper — Clara runs OCR to recover the text. It's `--ocr auto` by
  default (only fires when the PDF looks scanned), with `--ocr force` and
  `--ocr off`. Without the extra, `auto` degrades quietly and `force` says so.

Structure is preserved: from HTML and DOCX, headings and lists are carried
through simplification into the exported HTML/PDF (`<h2>`/`<h3>`, `<ul>`/`<ol>`)
instead of flattening to paragraphs — run `clara simplify --file notice.docx
--html` (add `--flatten` to opt out). Readability and faithfulness still run on
the flattened text. PDF text is extracted best-effort — PDFs are a visual format,
so line breaks can be rough.

---

## Accessible output

Close the loop: export the result as an accessible document.

```bash
clara simplify --html --file notice.txt > notice.html
clara easyread --html --lang ru --file уведомление.txt > easyread.html
```

- **Semantic HTML** — pure Python, no dependencies, always available: correct
  `lang`, a single `<h1>`, real paragraphs, and for Easy Read an ordered list of
  picture + text rows with `alt` text. Good contrast and spacing. In the web UI,
  "Download accessible HTML".
- **Tagged PDF (PDF/UA-1)** — via WeasyPrint (`pip install "clara[pdf]"`;
  "Download tagged PDF" in the UI). If WeasyPrint or its system libraries aren't
  present, the endpoint returns a clear message instead of a broken file — the
  HTML stays the reliable path, and browsers produce a tagged PDF when you print
  the semantic HTML.

For Easy Read, **"Embed pictures (offline)"** (CLI `clara easyread --html
--embed-images`) inlines the ARASAAC pictograms as base64 data URIs, so the
document is fully self-contained and works with no network. Off by default (URLs
are lighter); the PNGs are cached on disk, and any that can't be fetched fall
back to their URL.

---

## Review workflow

Simplified public-information text should be validated by people — the Easy Read
standard asks for it. Clara persists reviews so that can happen: save a result,
and a reviewer can comment, request changes, save a revised version, and approve.

- Web UI: "Save to review" on any result, then the **Reviews** tab to triage —
  filter by status, open one, comment, change status, edit a revision.
- CLI: `clara review list`, `clara review show <id>`,
  `clara review status <id> approved`.

State lives in a stdlib-sqlite store (`clara/review.py`, default
`~/.clara/reviews.db`, override with `CLARA_DB`). Statuses: draft, in_review,
approved, rejected, changes_requested. Every revision is versioned.

### Multi-user

Reviews are single-user by default. Set `CLARA_AUTH=1` to require a login: the
review endpoints then need a bearer token, and reviews and comments are
attributed to the signed-in user.

```bash
CLARA_AUTH=1 clara user add alice --password ...   # first user becomes admin
# the web UI then shows a login; POST /auth/login returns a bearer token
```

Passwords are hashed with stdlib pbkdf2 (no external dependency); sessions are
opaque tokens in the same sqlite DB. Registration is open only for the first
user (bootstrap); after that, add users with `clara user add`. The engine
endpoints (simplify/verify/…) never require auth.

---

## LLM providers

Provider-agnostic. Set `CLARA_PROVIDER` (default `mock`, which runs offline):

| Provider    | Env                                             |
|-------------|-------------------------------------------------|
| `mock`      | none — offline echo, for tests/demos            |
| `openai`    | `OPENAI_API_KEY` (+ `OPENAI_BASE_URL` for compatibles) |
| `anthropic` | `ANTHROPIC_API_KEY`                             |
| `ollama`    | none — **local, nothing leaves the machine**    |

`CLARA_MODEL` overrides the model. The **Ollama** path is first-class on
purpose: medical and legal documents should not have to travel to a third-party
API.

---

## Architecture

```
ingest → structure → fact spine → simplify (LLM) → VERIFY ← the point
                                                      ↓
                              readability score → pictograms → accessible output
                                                      ↓
                                    review loop: original ↔ simplified, approve
```

Current code:

```
clara/
  facts.py        deterministic fact extraction (numbers, dates, negation...)
  verify.py       faithfulness report — the heart
  readability.py  Flesch scoring (English; language packs plug in)
  simplify.py     standard-aware prompts (plain / easy_read / grade)
  pipeline.py     simplify → verify → score, one call
  llm/            provider-agnostic layer (mock/openai/anthropic/ollama)
  cli.py          `clara simplify`, `clara score`
api/main.py       optional FastAPI endpoint
tests/            hermetic, offline (mock provider)
```

---

## Languages

Ships **English, Russian, Spanish, German, French**. Pick with `--lang` (CLI),
the `lang` field (API), or the language selector (web UI):

```bash
clara simplify --lang ru --text "Плата вносится не позднее 10 числа месяца."
clara easyread --lang ru --file уведомление.txt
```

A language pack (`clara/lang/<code>.py`) is pure data plus a syllable counter:

- readability coefficients — English: Flesch/Flesch-Kincaid; Russian: Oborneva;
  Spanish: Szigriszt-Pazos (INFLESZ); German: Amstad; French: Kandel-Moles,
- month names and negation/obligation/condition words for fact extraction,
- the word alphabet and stopwords for tokenizing and pictogram keywords,
- the ARASAAC pictogram locale and an optional simplification note.

Adding a language is one self-contained file plus a line in
`clara/lang/__init__.py` — the core never changes.

> **Honest gap:** only English ships a *grade-level* metric. The other packs
> ship a validated *reading-ease* metric but no grade formula (no widely-agreed
> coefficient set), so `flesch_kincaid_grade` is reported as `null` rather than a
> fabricated number. A pull request with a validated formula is welcome.

---

## Roadmap

Done so far (below) — and the forward plan lives in [ROADMAP.md](ROADMAP.md):
known false positives in the faithfulness checker (number words, negation
pairs), long-document chunking, OCR, pluggable symbol sets, UI localization,
and validation with target readers.

- [x] Core: simplify → verify → score, provider-agnostic, CLI, tests
- [x] Reference UI: source ↔ simplified side by side, drift highlighted, approve
      (zero-dependency dev server; a full Next.js app is a later evolution)
- [x] Easy Read: one idea per line, pluggable symbols (ARASAAC / Mulberry),
      reviewer-chosen pictograms
- [x] Accessible output: semantic HTML (always) + tagged PDF/UA via WeasyPrint
- [x] Ingestion: text / HTML / URL (stdlib) + PDF / DOCX (optional `[ingest]`),
      scanned-PDF OCR (optional `[ocr]`), with headings/lists preserved through export
- [x] LLM-based semantic faithfulness check (opt-in, on top of deterministic)
- [x] Language packs: English + Russian (add one in `clara/lang/`)
- [x] Review workflow: versions, comments, status sign-off; optional multi-user auth

---

## Contributing

Issues and PRs welcome — especially language packs and real-world documents that
break the faithfulness check (those are gold). If you work with people who use
Easy Read or Plain Language, your review is worth more than any metric here.

## License

MIT — see [LICENSE](LICENSE).
