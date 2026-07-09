# LLM Accessibility Profile — draft v0.1

A tiny, portable JSON document in which a person states their accessibility
needs for AI answers **once**, so any chat client can apply them.

> **Status: draft.** The format is deliberately small. Feedback — especially
> from assistive-technology users and the organisations that work with them —
> is the input this draft is waiting for. Open an issue.

## Why this exists

Operating systems have accessibility settings that applications respect. Games
ship remappable controls, subtitles, readable-font modes. The LLM ecosystem has
**nothing**: every conversation starts from zero, and the person least able to
re-explain their needs — "short sentences, no hard words, no tables" — is the
one who must do it most often, in every new chat, in every new app.

Vendor-specific "custom instructions" exist but don't transfer, aren't
machine-readable, and nothing verifies they were honoured. A profile is the
missing piece: one file, any client, checkable.

## The format

```json
{
  "a11y_profile": "0.1",
  "language": "ru",
  "reading": {
    "level": "easy_read",
    "grade": 5,
    "max_sentence_words": 15,
    "one_idea_per_line": true,
    "define_hard_words": true
  },
  "format": {
    "prefer_lists": true,
    "avoid_tables": true,
    "avoid_emoji": true,
    "short_answers": true
  },
  "verify": {
    "facts": true,
    "warn_inline": true
  },
  "symbols": {
    "set": "arasaac"
  }
}
```

Machine-readable schema: [`accessibility-profile.schema.json`](accessibility-profile.schema.json).

### Field reference

Everything except `a11y_profile` is optional; an absent field means
*no preference*, never *off*.

| Field | Meaning |
|---|---|
| `a11y_profile` | Spec version string. Required. |
| `language` | Language the reader wants answers in (`"ru"`, `"en"`, …). |
| `reading.level` | `"plain"` (plain language), `"easy_read"` (Easy Read / E2R), or `"grade"` (a school reading level). |
| `reading.grade` | Target grade 1–12, used with `level: "grade"`. |
| `reading.max_sentence_words` | Hard cap on sentence length. |
| `reading.one_idea_per_line` | One idea per sentence, one sentence per line. |
| `reading.define_hard_words` | Explain difficult words in simple terms. |
| `format.prefer_lists` | Short bulleted lists over long paragraphs. |
| `format.avoid_tables` | No tables (they read poorly in screen readers). |
| `format.avoid_emoji` | No emoji or decorative symbols. |
| `format.short_answers` | As short as the question allows. |
| `verify.facts` | The reader wants simplified answers **fact-checked** against the original (numbers, dates, negations). |
| `verify.warn_inline` | Put warnings in the answer text itself, not only in metadata the reader may never see. |
| `symbols.set` | Preferred pictogram set for symbol-supported output (`"arasaac"`, `"mulberry"`). Reserved in v0.1 — defined here so profiles are stable; Clara's Easy Read endpoints accept the same values. |

## How clients apply a profile

**Mode A — instruction injection.** Render the profile into a system-prompt
block and prepend it to the conversation. Works with *any* model and *any*
client today. Honest limitation: it is a **request** — nothing checks the model
obeyed. The reference renderer is `clara profile render` (or
`clara.profile.render_instructions()`), producing a deterministic English
instruction block a person can paste into any client's custom instructions.

**Mode B — verified pipeline.** A profile-aware endpoint enforces what Mode A
can only ask for. The reference implementation is **clara-proxy**
(`/v1/chat/completions`): `reading.level`/`grade` select a real simplification
pass; the reading-detail constraints go into that pass's instructions; the
deterministic faithfulness layer then *checks* the result, and per
`verify.warn_inline` a plain-language warning (in `language`) is appended when
facts were lost. `format.*` and `language` are injected upstream (Mode A
inside Mode B — formatting can't be verified deterministically; the spec is
honest about which fields are enforced and which are requested).

### Rules for implementations

1. **Ignore unknown fields.** A newer profile must degrade, not break.
2. **Absent ≠ off.** Only apply stated preferences.
3. **Never fail silently.** If a profile can't be loaded or a stated need can't
   be met, say so — a person who believes protections are on when they aren't
   is the worst outcome. (clara-proxy refuses the request if `CLARA_PROFILE`
   points at a broken file, and reports `profile_applied` in every response.)
4. **The user's active choice wins.** An explicit per-conversation action (e.g.
   picking `clara-easy-read` in a model picker) outranks the standing profile.

## Using it with Clara today

```bash
clara profile example > my-profile.json     # starter profile; edit it
clara profile check  --file my-profile.json # validate
clara profile render --file my-profile.json # Mode A: paste into any chat client

# Mode B: the verified path — every answer simplified and fact-checked
CLARA_PROFILE=my-profile.json uvicorn api.main:app
# point any OpenAI-compatible client at http://localhost:8000/v1
```

A profile can also travel per request in the body: `"clara": {"profile": {…}}`.

## Versioning

`a11y_profile` is the spec version. Within 0.x, changes are additive — new
optional fields only. Field removal or semantic change bumps the major version.
