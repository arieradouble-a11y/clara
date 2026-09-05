# Research: an accessibility layer for LLM interfaces

Evidence base and design brief for Phase 7 — making AI chat interfaces usable by
disabled people, and deciding what Clara should build (and refuse to build).

Produced by a 31-agent research workflow (2026-09-05): 13 parallel evidence
sweeps across disability groups, standards, law and prior art; adversarial
verification of the highest-risk claims; three competing architecture proposals;
an unsparing critique; and a synthesis. 238 findings, 66 claims corrected by
verification (7 outright refuted).

| File | What it is |
|---|---|
| [a11y-layer-design-brief.md](a11y-layer-design-brief.md) | **Start here.** The decision-ready brief: framing, evidence, architecture, module table, build order, adoption strategy, risks. |
| [a11y-layer-critique.md](a11y-layer-critique.md) | The completeness critic's attack on the proposals — including the steelman objection this project must answer. |
| [a11y-evidence-base.md](a11y-evidence-base.md) | All 238 findings with sources and verification verdicts, by dimension. |
| [a11y-verification-corrections.txt](a11y-verification-corrections.txt) | Every claim the adversarial pass refuted or judged overstated. Read before quoting any statistic or legal date. |

## The three things to know

1. **"No AI product ships vision accessibility" is false.** Claude Code documents
   a screen-reader mode, reduced motion, colourblind themes and a magnifier
   cursor; Google publishes an NVDA-audited VPAT for Gemini. The defensible claim
   is narrower and stronger: *no product ships a layer over the **content*** —
   delivery pacing, navigable structure, a document view, or an honest report of
   what a simplification lost.

2. **The overlay line is architectural, not moral.** The FTC's April 2025 final
   order against accessiBe ($1M + a 20-year prohibition) defines the forbidden
   representation precisely. Clara stays on the right side by API shape: the host
   calls in, the layer never reaches out; no AT detection, ever; compiled into the
   adopter's build, never a third-party script tag.

3. **Free code was never the binding constraint on adoption.** Microsoft's
   MIT-licensed Immersive Reader gets ~38k npm downloads/month against axe-core's
   272M. The lever is public-sector procurement (Section 508 + FAR 39.2 today;
   ADA Title II WCAG 2.1 AA by 26 April 2027/2028) — and being the evidence
   nobody else has produced.

## Status

Findings, not commitments. Defaults for delivery pacing and announcement
verbosity are currently **guesses** and must be set by formative sessions with
disabled participants before the spec is written — see §10 of the brief for the
questions to ask partner organisations.
