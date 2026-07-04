# Clara

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
source — numbers, money, percentages, dates — **without an LLM**, then verifies
each one survived in the output. A mismatch is a reproducible signal, not an
opinion. Negations, obligations (`must`/`shall`), and conditions (`if`/`unless`)
are inventoried too and raised as review warnings.

On top of that deterministic layer, an **optional LLM semantic check**
(`clara/semantic.py`; `--semantic` on the CLI, or the "Run AI semantic check"
button) compares source and output for meaning drift the regexes can't see — a
weakened obligation, a changed condition, an added implication — and returns
typed issues (omission / addition / contradiction / distortion). It costs a model
call, so it is opt-in, and it degrades to "unavailable" rather than guessing when
no capable provider answers.

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

Pictograms come from **ARASAAC** (~13k symbols, multilingual). Matching is
best-effort and the chosen keyword is returned so a human reviewer can swap the
image. Lookups are cached on disk and fail soft — if ARASAAC is unreachable the
text still works, just without pictures.

For inflected languages (e.g. Russian) matching works best on base word forms —
`мусор` matches, `воду` (accusative) may not. Lemmatization before lookup is a
planned improvement.

> **Attribution & licensing.** ARASAAC pictograms are the property of the
> Government of Aragón, created by Sergio Palao, licensed **CC BY-NC-SA**. The
> **non-commercial** clause carries downstream: if you build a commercial product,
> you must swap in a symbol set whose license permits it. The pictogram source is
> isolated in `clara/pictograms.py` for exactly this reason.

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

Paragraph structure is preserved (blocks separated by blank lines). PDF text is
extracted best-effort — PDFs are a visual format, so line breaks can be rough.

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

Ships **English** and **Russian**. Pick with `--lang` (CLI), the `lang` field
(API), or the language selector (web UI):

```bash
clara simplify --lang ru --text "Плата вносится не позднее 10 числа месяца."
clara easyread --lang ru --file уведомление.txt
```

A language pack (`clara/lang/<code>.py`) is pure data plus a syllable counter:

- readability coefficients (English: Flesch / Flesch-Kincaid; Russian: the
  Oborneva adaptation of Flesch),
- month names and negation/obligation/condition words for fact extraction,
- the word alphabet and stopwords for tokenizing and pictogram keywords,
- the ARASAAC pictogram locale and an optional simplification note.

Adding a language is one self-contained file plus a line in
`clara/lang/__init__.py` — the core never changes.

> **Honest gap:** Russian ships a *validated reading-ease* metric but no
> grade-level one — there is no widely-agreed Russian Flesch-Kincaid coefficient
> set, so `flesch_kincaid_grade` is reported as `null` rather than a fabricated
> number. A pull request with a validated formula is welcome.

---

## Roadmap

- [x] Core: simplify → verify → score, provider-agnostic, CLI, tests
- [x] Reference UI: source ↔ simplified side by side, drift highlighted, approve
      (zero-dependency dev server; a full Next.js app is a later evolution)
- [x] Easy Read: pictogram pairing (ARASAAC), one idea per line
- [x] Accessible output: semantic HTML (always) + tagged PDF/UA via WeasyPrint
- [x] Ingestion: text / HTML / URL (stdlib) + PDF / DOCX (optional `[ingest]`)
- [x] LLM-based semantic faithfulness check (opt-in, on top of deterministic)
- [x] Language packs: English + Russian (add one in `clara/lang/`)
- [ ] Review workflow: versions, comments, sign-off by validators

---

## Contributing

Issues and PRs welcome — especially language packs and real-world documents that
break the faithfulness check (those are gold). If you work with people who use
Easy Read or Plain Language, your review is worth more than any metric here.

## License

MIT — see [LICENSE](LICENSE).
