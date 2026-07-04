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

## Multilingual

Clara is English-first but structured for language packs. A pack supplies:

- a readability metric (Flesch for English; other languages need their own),
- simplification guidance/examples for the prompt,
- month names and marker words for fact extraction,
- a pictogram locale (ARASAAC, ~13k CC-licensed symbols, multilingual).

Adding a language is a self-contained pull request — the healthy open-source
shape. Russian is the intended second pack.

---

## Roadmap

- [x] Core: simplify → verify → score, provider-agnostic, CLI, tests
- [x] Reference UI: source ↔ simplified side by side, drift highlighted, approve
      (zero-dependency dev server; a full Next.js app is a later evolution)
- [ ] Ingestion: PDF / DOCX / HTML / URL with structure preservation
- [ ] Easy Read: pictogram pairing (ARASAAC) + layout rules
- [ ] Accessible output: tagged PDF, semantic HTML
- [ ] LLM-based semantic faithfulness check (beyond deterministic numbers/dates)
- [ ] Review workflow: versions, comments, sign-off by validators
- [ ] Language packs: Russian, then community-driven

---

## Contributing

Issues and PRs welcome — especially language packs and real-world documents that
break the faithfulness check (those are gold). If you work with people who use
Easy Read or Plain Language, your review is worth more than any metric here.

## License

MIT — see [LICENSE](LICENSE).
