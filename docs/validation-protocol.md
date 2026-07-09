# Easy Read validation protocol (draft)

> **Русская версия** (адаптация под российский контекст + письмо-предложение
> для партнёрских организаций): [ru/validation-protocol.md](ru/validation-protocol.md),
> [ru/voi-outreach.md](ru/voi-outreach.md).

> **Status: method drafted, not yet run.** This document describes *how* Clara's
> output should be validated by the people it is for. The validation itself has
> not happened. Until it does, Clara is **assistive, not authoritative** — and it
> stays that way after, too. Running this needs a partner organisation; see
> "Getting started".

## Why this exists

The Easy Read standard — Inclusion Europe's *[Information for all](https://www.inclusion-europe.eu/easy-to-read/)*
— is explicit: **Easy Read material must be checked by people with intellectual
disabilities.** A machine (Clara included) and a non-disabled author can make text
that *looks* simple and still fails the reader. Automated readability scores and a
WCAG audit ([ACCESSIBILITY.md](../ACCESSIBILITY.md)) are necessary but **not
sufficient**. Only the readers can tell you if it actually works.

So this is not a nice-to-have. It is the difference between a tool that *claims*
accessibility and one that has earned the word.

## Principles

1. **Nothing about us without us.** Validators with intellectual disabilities are
   co-authors of the standard, not test subjects.
2. **Pay validators** for their expertise and time, at a fair rate.
3. **Comprehension, not preference.** We measure whether the meaning came across —
   not whether people "liked" it.
4. **Consent and dignity.** Informed consent in accessible format; anyone can stop
   at any time, no reason needed; no personal or distressing documents as test
   material.
5. **Support, don't lead.** A supporter may help a validator take part, but must
   not answer for them or steer the answer.

## Who takes part

- **Validators:** 3–6 people with intellectual disabilities per session. Ideally a
  self-advocacy group that already works together.
- **A facilitator** experienced in supported communication (often a
  speech-and-language therapist / SLP, or the group's own facilitator).
- **A note-taker** (can be the Clara contributor) who records findings, not names.

## Materials

- 1–3 short documents per session (a real notice/letter genre, ~1 page each), each
  in two forms: the **original** and Clara's **Easy Read** output (text + chosen
  pictograms).
- Print at a comfortable size; bring the pictograms as shown in the tool.
- A short, accessible consent sheet and a small set of comprehension questions per
  document (written in Easy Read themselves).

## Session protocol

For each document, one at a time:

1. **Read together.** The validator reads (or is read to), line by line.
2. **Ask what it means.** Open questions first: "What is this letter asking you to
   do?" Then targeted comprehension questions covering every *hard fact* Clara is
   meant to preserve — the amount, the deadline, the condition, the action.
3. **Mark the sticking points.** For each line, capture: understood / unclear /
   misunderstood, and *why* (a hard word, a long sentence, a confusing picture).
4. **Check the pictures.** For each pictogram: does it match the idea? Would a
   different one be clearer? (This feeds the reviewer-picks-a-pictogram flow.)
5. **Don't fix it live.** Record the problem; revision happens afterwards with the
   group's input, not on the spot.

Keep sessions short (~60–90 min) with breaks.

## What we record (and publish)

- Per line: comprehension outcome + reason, de-identified.
- Which **hard facts** were understood vs missed — this is the ground truth the
  deterministic faithfulness check is a *proxy* for.
- Pictogram hit/miss and better suggestions.
- Method, sample size, and limitations — published so the claim is falsifiable.

We publish the **method and the findings**, not raw participant data.

## Feeding results back into Clara

Validation is only worth it if it changes the tool. Findings route to:

- **The eval corpus** (`tests/test_eval.py`) — real "hard fact understood/missed"
  pairs become regression cases.
- **Language packs** (`clara/lang/*.py`) — words that confused readers feed the
  simplification note and the `soft_stopwords` / keyword ranking.
- **Symbol choices** — recurring bad matches inform the pictogram keyword logic
  and the default symbol set.
- **This protocol** — improved from what we learn each round.

## Getting started (for maintainers)

This cannot be run solo. To start:

1. Find a partner: a self-advocacy group, an Easy Read validation service, or an
   SLP team. (Inclusion Europe members are a starting point.)
2. Agree ethics, consent, and payment up front.
3. Run one small pilot session with 1–2 documents. Publish the method and what you
   learned — even a pilot of five people is worth more than another benchmark.

Until a round is run and published, the README and UI keep saying **assistive,
not authoritative**.
