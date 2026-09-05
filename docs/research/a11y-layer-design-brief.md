# Clara Accessibility Layer — Final Design Brief

**Status:** decision-ready. Written to be turned into code.
**Date:** 2026-09-05
**Repo:** github.com/arieradouble-a11y/clara

---

## 1. The honest framing

### What this should be

Two separable things, shipped and licensed separately, with the second able to run without the first:

**(A) A conversational-stream behaviour contract** — a small normative spec plus an executable test suite plus copyable reference implementations, covering how a streaming AI answer is structured, paced, announced, focused and re-read. This is AT plumbing. It has no incumbent: the ARIA Authoring Practices Guide has no pattern for chat, conversation, message logs, streaming or live regions (https://www.w3.org/WAI/ARIA/apg/patterns/), and W3C ARIA-AT has no test plan for any of it.

**(B) A content layer** — the thing only Clara is positioned to build: restructuring a conversation into something readable, reporting what a transformation lost, and never asserting that anything is correct. Its flagship is not the rewriter. It is a **document view** (§7, §5 row 1).

### What this should not be

- **Not a "vision accessibility layer."** That framing is falsifiable in thirty seconds (§3) and it points at the wrong build.
- **Not a widget with font-size and contrast buttons.** That is the overlay signature.
- **Not a product that claims conformance.** The FTC's April 2025 final order against accessiBe defines the prohibited representation precisely — that an automated product makes a site WCAG-compliant absent supporting evidence — and cost $1M plus a 20-year prohibition (https://www.ftc.gov/news-events/news/press-releases/2025/04/ftc-approves-final-order-requiring-accessibe-pay-1-million).
- **Not "an accessibility layer that model operators embed."** That goal has a near-zero success probability and every comparable case is against it (§7). Continuing to state it is the failure mode.

### The overlay line, head-on

An overlay is defined by four **architectural** properties, not by intent or quality:

1. Third-party script injected into a page the vendor does not own.
2. Substitution for source remediation.
3. Duplication of capability the user already has configured at OS/browser/AT level.
4. Detection of assistive technology.

Nothing in the Overlay Fact Sheet (https://overlayfactsheet.com/en/), the EDF/IAAP joint statement (https://www.edf-feph.org/publications/joint-statement-on-accessibility-overlays/), NFB/ACB/AFB resolutions, or NHS service-manual guidance (https://service-manual.nhs.uk/accessibility/design) condemns a product shipping its own accessibility affordances. A settings pane in Slack, VS Code or iOS is not an overlay. Wikipedia's 2024 "Accessibility for reading" work — which raised the base font from 14px to 16px for everyone and put controls in the product's own Appearance menu — is the accepted first-party pattern (https://www.mediawiki.org/wiki/Reading/Web/Accessibility_for_reading).

So the line Clara must hold is architectural, enforced by the API shape and by repo layout, not asserted in a README:

- **The host calls in; the layer never reaches out.** The integration surface is `turnStarted()` / `chunk()` / `turnComplete()` / `interrupted()`. There is no method that accepts a selector for host content. No MutationObserver on host DOM, no automatic relabelling, no injected landmarks.
- **No AT detection, by any means, for any reason** — not for better defaults, not to duck TTS, not for telemetry. AT detection plus a browser fingerprint identifies a specific person as disabled, which is GDPR Article 9 special-category data (https://tink.uk/accessibe-and-data-protection/).
- **Compiled into the adopter's build.** Never a third-party `<script>` tag. The phrase "one line of code" never appears in any Clara material — it is the overlay industry's exact marketing phrase.
- **The browser extension moves out** (§8). A Manifest V3 extension that overlays simplified text on arbitrary pages is architecturally the overlay pattern. It is defensible only because the *user* installs it for themselves, and that distinction is real, subtle, unaddressed by any community statement, and not one Clara gets to adjudicate for itself.

### One correction to how the overlay evidence is usually applied

The redundancy test ("can the OS already do this?") is a good gate and it is routinely **over-applied**, because its entire evidence base is blindness-organisation-derived: Kubesch's 21 participants were all visually impaired (https://overlays.dnikub.dev/), and NFB/ACB/AFB are blindness organisations. Two consequences:

- **Read Aloud is not redundant for everyone.** It duplicates what a screen-reader user already has, configured better. It does not duplicate anything for a dyslexic reader, a low-literacy reader, a person with aphasia, or a low-vision user who does not run a screen reader. Word, Edge and Pocket all ship it as a first-party feature. Clara's rule is therefore: opt-in, never auto-play, pausable, never a default, never in the same channel as the live region — not "banned."
- **In-product text size is not automatically redundant either.** Browser zoom scales the whole layout; a reader who wants larger *message* text at the same UI density has no route to it. Wikipedia — the precedent everyone cites approvingly — ships exactly this control on the web. On desktop/Electron it is unambiguously earned (Claude Code issue #78635 is an open request from a user with a named visual impairment).

The test that actually matters is the one the redundancy argument was posing all along: **does the OS or browser do this *for this population*?** Apply it per-population, not with a blind-user prior.

---

## 2. What the evidence actually says

Twelve findings that drive the design. Each is load-bearing; each has a source.

**1. Live-region change events are queued one per mutation, with no specified coalescing for `aria-atomic="false"`.** A streaming message with `aria-live="polite"` or `role="log"` therefore generates an unbounded, un-deduplicated announcement queue. You cannot engineer out of it with `aria-busy`/`aria-atomic`/`aria-relevant`: support is inconsistent and `aria-busy` is read through by everything except JAWS. (https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Guides/Screen_Reader_Implementors; https://www.sarasoueidan.com/blog/accessible-notifications-with-aria-live-regions-part-1/)

**2. The only production-evidenced pattern is to decouple announcement from content:** a separate visually-hidden region, outside the transcript, mounted *empty* at init, receiving short status strings and cleared between them. A pre-populated live region announces nothing — the most common silent failure, and it looks correct in code review. (https://github.com/microsoft/BotFramework-WebChat/issues/3236; https://tetralogical.com/blog/2024/05/01/why-are-my-live-regions-not-working/)

**3. The dominant real-world failure blind users report is not the live region at all** — it is that AI responses are structurally unnavigable (no headings, no prompt-to-response shortcut) and that nothing tells the user when generation finished, forcing them to "dig for it." All 19 participants demonstrated unlabeled copy/regenerate/downvote buttons live. (ASSETS '24, n=19: https://maitraye.github.io/files/papers/BLV_GenAI_ASSETS24.pdf)

**4. Structure must be headings, not landmarks.** ~72% of screen-reader users find information by heading; 3.7% primarily by landmark. (https://webaim.org/projects/screenreadersurvey10/)

**5. A chat interface measurably degrades blind users' comprehension relative to a navigable document interface — 40% fewer main topics, double the error rate — while users subjectively prefer the chat.** Satisfaction is an actively misleading success metric for this population. This is the single strongest *comparative* finding in the whole base, and it is a finding about interface *form*, not about announcement. (ASSETS '26 preprint: https://arxiv.org/html/2608.25382v1)

**6. Dynamically changing content is the documented catastrophic failure mode for magnifier users**, who work at 8x–45x — an order of magnitude past WCAG's 400% reflow ceiling — and "do not have the luxury of time to manually pan before the content changes." A small displacement of the magnification window makes a whole line disappear. (https://oscarlab.github.io/papers/chi18-billah.pdf; https://par.nsf.gov/servlets/purl/10186664; https://arxiv.org/abs/2303.16346)

**7. The same DOM mutation destroys reading position across four unrelated ATs at once:** the JAWS/NVDA browse-mode virtual buffer is rebuilt; the refreshable braille line re-renders (and VoiceOver treats polite regions *assertively* in braille, destroying what was being read — 8 of 19 ASSETS '24 participants used displays); the magnifier lens loses its target; and buttons move out from under a head-pointer or dwell-click user. (https://adrianroselli.com/2026/01/live-region-support.html; ASSETS '24; https://arxiv.org/pdf/2503.16491 — visually impaired developers explicitly asking for "AI timeouts")

**8. Alternative text entry runs 3x–20x slower than typing:** scanning keyboards 1.67 wpm, cursor-selection 4.24 wpm, BCI 0.66 wpm, sustained real-world gaze typing ~8 wpm, with switch-scanning varying 0.15–12.94 wpm *between individuals*. At those rates a prompt is a multi-minute-to-half-hour composition, and a stray Enter or an idle timeout is total task failure. Voice does not rescue this population: severe dysarthria exceeded 51% WER across all eight commercial ASR systems and multimodal LLMs tested. (https://www.resna.org/sites/default/files/conference/2017/cac/Koester.html; https://pmc.ncbi.nlm.nih.gov/articles/PMC11530652/; https://arxiv.org/abs/2512.17474)

**9. Richer, more fluent AI output is *more believable* and therefore suppresses fact-checking** — and blind users face structurally lower verifiability, because checking a claim can require recruiting a sighted person. A more articulate accessibility layer without loss-reporting is a net harm. Relatedly, *shorter* is not safer: medium responses (~42–150 words) produced 54.2% error detection against 24.5% for very short. (ASSETS '24; https://arxiv.org/abs/2603.06878)

**10. The efficacy evidence for simplification is real but modest, and partly negative.** LLM simplification improves general-population comprehension by ~4 percentage points. The most rigorous Easy Read RCT found *no* significant improvement in comprehension or retention, with intrinsic language ability the stronger predictor. Automatically and manually simplified texts are not measurement-equivalent for readers with intellectual disabilities. LLMs carry a large measured paternalism bias about this population. Deaf organisations have campaigned for verbatim text on the grounds that any deletion denies equal access. (https://arxiv.org/abs/2505.01980; https://pmc.ncbi.nlm.nih.gov/articles/PMC12893875/; https://arxiv.org/abs/2402.13094; https://dcmp.org/learn/captioningkey/601)

**11. No W3C standard requires that a machine-generated or simplified text preserve the meaning of its source** — but ATAG 2.0 SC B.1.2.1 (W3C Recommendation, 2015) already specifies *preserve-or-warn-or-auto-check-or-prompt-to-check* after a transformation, which is structurally identical to rewrite-then-verify and is implemented by no AI product. (https://www.w3.org/TR/ATAG20/)

**12. Portable preference profiles fail on enforceability, not on design.** ISO/IEC 24751 has been an International Standard since 2008 with essentially no field implementations; 1EdTech AfA PNP never reached Final Release in 14 years and is not certified; the W3C TAG closed the Personalization Semantics review "unsatisfied" and WAI-Adapt was cut to one attribute, frozen since January 2023; GPII's preference servers are offline today. Meanwhile `prefers-reduced-motion` reached ~50% site usage, `prefers-color-scheme` 12%, `prefers-contrast` under 1%. Field count is negatively correlated with adoption. Do Not Track vs Global Privacy Control is the decisive natural experiment: adoption of a portable preference signal tracks legal enforceability. (https://github.com/w3ctag/design-reviews/issues/476; https://almanac.httparchive.org/en/2024/accessibility)

---

## 3. Correcting the premise

The commissioning observation was: *many ordinary websites offer vision-accessibility settings, but no AI chat product ships anything like a vision-accessibility layer.*

### Where it is wrong

**"No AI product ships vision accessibility" is false and would be corrected in the first thirty seconds of any serious conversation.**

- Anthropic's Claude Code ships a documented, multi-feature accessibility layer: screen reader mode, reduced motion, colorblind-friendly themes, magnifier-friendly cursor (https://code.claude.com/docs/en/accessibility).
- ChatGPT ships an Appearance/Contrast control that follows the OS accessibility contrast preference (https://help.openai.com/).
- Google publishes a free, ungated, NVDA-audited Accessibility Conformance Report for Gemini against WCAG 2.0/2.1/2.2 AA, Section 508 and EN 301 549 (https://www.google.com/accessibility/static/pdf/google-gemini-web-vpat.pdf).

**And the gap is closing under the project in real time.** During the research window alone: Anthropic shipped VS Code extension screen-reader support in v2.1.236 against an issue filed weeks earlier; LibreChat #8097 (collapsed reasoning blocks still in the a11y tree) closed COMPLETED; Open WebUI #17150 closed COMPLETED. Any thesis of the form "they don't have X" is building on ice.

**Second error: "vision settings panel" is the wrong shape.** Most of what a conventional website vision panel contains fails the redundancy test outright on the web, and that exact bundle — font size, contrast, colour inversion, stop animations, TTS behind a floating person-icon — is the condemned signature. Kubesch's 21 visually impaired participants "almost entirely ignored" the floating button, and none of the three overlays tested reached WCAG 2.1 AA.

**Third error: "layer" implies a thing operators embed.** Frontier chat UIs are closed products with no third-party runtime injection point (§7). Microsoft's Immersive Reader — MIT-licensed, feature-rich, backed by the largest accessibility organisation in the industry — sits at ~38k npm downloads/month against axe-core's 272M, because embedding it requires an Azure subscription, an Entra app registration and a token backend (https://learn.microsoft.com/en-us/azure/ai-services/immersive-reader/overview). Free code has never been the binding constraint.

### Where it is right, and sharper than it knows

- **No product ships a *content* layer.** No reading-level control, no simplification with loss-reporting, no output-length control, no announcement-verbosity control, no delivery pacing. This was not found in Gemini's 31 tested surfaces, in Anthropic's settings table, or across ~90 open accessibility issues in the two largest open-source UIs.
- **No W3C pattern exists for streaming conversational output.** No APG page, no ARIA-AT test plan, no WCAG technique beyond ARIA23's static-append example (https://www.w3.org/WAI/WCAG21/Techniques/aria/ARIA23). The Feed pattern is a browsing contract for infinitely-scrolling articles, not a conversation.
- **Verbosity control does not exist anywhere**, despite blind users typing roughly 10x less than they must listen to and inventing prompt-engineering workarounds (CHI '26: https://arxiv.org/abs/2602.16930).
- **Nobody has measured any of this with disabled users of AI chat.** No announcement-strategy comparison. No magnifier study of an LLM interface. No braille-under-streaming data. No first-hand dated audit of the four major products since early 2024.

### The defensible replacement claim

> Every major AI chat product now ships some presentation accessibility, and the screen-reader gap is closing. What none of them ships is a layer over the *content*: control over the pace at which an answer arrives, structure you can navigate, a way to read a conversation as a document, and an honest report of what a simplification lost. There is no W3C pattern for any of it, and no published study measuring what disabled users of these products actually want.

That claim survives every vendor fix, and it points at the right build.

---

## 4. Architecture

### Packaging

| Artifact | Licence | Contents |
|---|---|---|
| `clara-stream-spec` | CC0 | ~15-page normative behaviour contract. Every clause carries a WCAG 2.2 SC, an EN 301 549 clause-11 reference, and a NAUR REQ number where one exists — and explicitly marks where no standard exists and the clause is Clara's own reasoned position. |
| `@clara/conformance` | MIT OR Apache-2.0 | Executable test suite. Test-only devDependency; never in an adopter's runtime bundle. |
| `@clara/core` | MIT OR Apache-2.0 | Headless. Zero deps, zero DOM, zero network. Stream scheduler, announcement state machine, aural markdown transform, document-view builder, preference resolver, loss reporter. |
| `@clara/dom` | MIT OR Apache-2.0 | Light-DOM custom elements. |
| `@clara/patterns` | CC0 snippets in an Apache-2.0 package | 100–250-line framework-free implementations. README says: **paste this in; do not npm-install it.** |
| `clara` (Python) | existing | Stays as the document pipeline and proxy reference. |

**Licence:** dual `MIT OR Apache-2.0` (the AccessKit/Rust pattern). Apache-2.0's express patent grant is what corporate legal looks for; CNCF mandates it. **Not CC0 for code** — it expressly withholds patent rights, the FSF advises against it for software, and public-domain dedications trigger case-by-case legal escalation at exactly the companies whose adoption is the goal (https://www.apache.org/licenses/LICENSE-2.0). CC0 is correct for the spec and the copy-me snippets. DCO, not CLA.

### Integration surface

The host owns its DOM and calls in:

```ts
const a11y = createClaraStream({ mount: announcerEl, prefs });
a11y.turnStarted({ turnId, role: 'assistant' });
a11y.chunk(turnId, text);            // buffered; commit policy decides render
a11y.turnComplete(turnId, { words, headings, codeBlocks, tables, loss });
a11y.interrupted(turnId);
```

There is no API that takes a selector for host content. That single fact is what separates this from an overlay, and it is enforced by the type signature.

### Web technical decisions (all evidenced)

- **Light DOM only.** Shadow roots break every ARIA IDREF relationship across the boundary (`aria-labelledby`, `aria-describedby`, `aria-controls`, `aria-activedescendant`) and `<label for>`. Reference Target is a Chrome origin trial with **no WebKit signal** as of July 2026, so a shadow-root design strands VoiceOver users. Define with `customElements.define()` (React 19, Vue, Angular, Svelte, Preact, Lit and Solid all score 100% on https://custom-elements-everywhere.com/) but override the render root to `this`.
- **`ElementInternals` for default semantics** (Baseline March 2023) so host attributes override cleanly and nothing breaks if they are deleted. `internals.states` + `:state()` for styling hooks instead of colliding class names.
- **Native elements everywhere.** `<button>`, `<input>`, `<table>`, `<dialog>`. Windows forced-colors mode assigns system colours by native semantics and **ignores ARIA roles** — a `div role="button"` component set passes axe and silently loses Contrast Themes (https://developer.mozilla.org/en-US/docs/Web/CSS/@media/forced-colors). Never `forced-color-adjust: none`. Never encode meaning in `box-shadow`, `text-shadow` or `background-image`.
- **CSS politeness without encapsulation:** all rules inside `@layer clara`, every default selector wrapped in `:where()` for zero specificity, full theme as custom properties, `container-type: inline-size`. Sizes in `rem`/`ch`, never `px` — a `max-width` in px silently defeats text scaling.
- **Distribution:** npm ESM with no build step, plus a single vendorable IIFE file for hosts under strict CSP who will not add a third-party origin. No CDN requirement, no runtime network call, no account, no API key.

### The exact markup contract (this is the thing people get wrong)

```html
<!-- mounted ONCE at app root, at init, EMPTY -->
<div id="clara-announcer" class="clara-vh" aria-live="polite" aria-atomic="false"></div>

<!-- the transcript: NO live semantics of any kind -->
<ol class="clara-transcript">
  <li>
    <h2 id="turn-12" tabindex="-1" class="clara-vh">Assistant replied, 12:04</h2>
    <div class="clara-answer"><!-- markdown render, model's h2/h3 preserved --></div>
  </li>
</ol>
```

**Resolving a contradiction that appears in two of the three proposals:** `role="log"` carries implicit `aria-live="polite"`. Putting it on a *wrapper around* the transcript instead of on the `<ul>` fixes the orphaned-listitem bug (open-webui #29211) and does **nothing** about the announcement flood — a live-region ancestor of mutating content is a live region over mutating content. **Do not use `role="log"` at all.** Use a plain ordered list plus headings plus the separate announcer. The conformance suite asserts *no live semantics anywhere in the transcript subtree*, ancestor or descendant.

**"Exactly one live region" is narrowed too.** Every real host already has one — a toast system, a form-error announcer, a router announcement. w3c/aria#1689 establishes that simultaneous multi-region behaviour is *undefined*, not that a page may contain only one. The enforceable rule: **the layer owns exactly one and creates no second of its own**, and the suite warns (not fails) on host-owned regions with sequencing guidance.

Announcement write pattern (clear-then-set, because screen readers suppress identical repeats):

```js
el.textContent = '';
requestAnimationFrame(() => { el.textContent = msg; });
setTimeout(() => { el.textContent = ''; }, 3000);
```

`ariaNotify()` is feature-detected progressive enhancement only — Chrome 141+/Firefox 150+, NVDA and TalkBack confirmed, **WebKit unimplemented**, and 70.6% of mobile screen-reader users are on iOS. Anything it says must also exist as navigable on-page text.

### Platforms, honestly scoped

- **Web:** primary, fully supported.
- **Desktop/Electron:** same TypeScript runs; **separate test matrix required.** NVDA has open bugs against ChatGPT's Electron shell where auxiliary COM interfaces are missing (nvaccess/nvda#18669). Browser-verified does not imply desktop-verified.
- **Native mobile:** headless core plus thin announcement adapters only (`accessibilityLiveRegion`/`announceForAccessibility` on Android, `UIAccessibility.post(.announcement)` on iOS). **Say plainly there is no shared cross-platform live-region primitive** — React Native's is Android-only. Do not promise one component.
- **Agent harnesses / CLI:** event adapter binding to tool-start / tool-result / tool-failure / permission-request / turn-complete, emitting plain stdout lines rather than ANSI-only signalling. Ships as a Claude Code hook package (§7).

### What it explicitly does NOT do

- Does not touch host DOM, ARIA or focus.
- Does not detect assistive technology.
- Does not make, or enable, a conformance claim.
- Does not run a hosted profile server, ever. (ds.gpii.net, ul.gpii.net and unifiedlisting.org are offline today.)
- Does not transmit preferences by default.
- Does not ship a dyslexia font (OpenDyslexic showed no measured improvement and no participant preferred it: https://doi.org/10.1007/s11881-016-0127-1), a signing avatar (WFD/WASLI restrict avatars to pre-recorded static content, and early-acquiring Deaf signers rate synthesized avatars lowest: https://wfdeaf.org/resources/statement-on-use-of-signing-avatars/), a floating accessibility button, or auto-playing TTS.
- Does not assert `role="feed"`, `aria-busy`, `aria-atomic` or `aria-relevant` as load-bearing.
- Does not emit an affirmative "verified" badge (§8).

---

## 5. Module table

Ranked by (evidence strength × population breadth × non-redundancy) ÷ effort.

| # | Module | Who it helps | Evidence basis | Impact | Effort |
|---|---|---|---|---|---|
| 1 | **`doc-view`** — render an answer, or a whole thread, as a static navigable document: `<article>`, real headings, generated table of contents, anchors, no mutation, no live regions, printable, exportable, brailleable. Plus a persistent plain-language thread state summary. | Blind + braille (navigable, re-readable, zero mutation), low-vision/magnifier (a static document magnifies without moving under the lens — the streaming problem solved by removing the stream), cognitive/ID (COGA Objective 6: processes must not rely on memory), motor (one artifact, not a 100-turn scroll), fatigue (resume tomorrow). | The only *comparative interface-type* measurement in the base: chat produced 40% fewer main topics and double the error rate vs document for blind users (https://arxiv.org/html/2608.25382v1). COGA Objective 6 (https://www.w3.org/TR/coga-usable/). Changes no words → immune to the Deaf verbatim objection, the Easy Read RCT, and the paternalism critique. | **Very high** | **Small** |
| 2 | **`delivery`** — commit-policy scheduler: `complete` / `block` (paragraph, list-item, code-fence) / `sentence` (optional wpm cap) / `raw`; plus a fixed-position **"Stop updating"** control (freezes render, generation continues) distinct from "Stop generating"; plus `overflow-anchor` scroll anchoring, no auto-scroll, no focus move during generation, pinned action controls. | Every constituency at once: magnifier, browse-mode screen reader, braille, switch/gaze/head-pointer, attention/cognitive, vestibular. | Findings 6, 7 above. IUI '20, CHI '23, ASSETS '24 ("hide and seek… because sometimes the page scrolled"), Roselli 2026 braille, arXiv 2503.16491 "AI timeouts". Argue on **mechanism**, not on SC 2.2.2 (see §9). Clara's proxy already buffers the whole answer (`clara/proxy.py` docstring: "True token streaming is impossible… `stream: true` is emulated") — the apology is the feature. | **Very high** | Small |
| 3 | **`turns`** — single primed-empty announcer; per-turn heading with `tabindex="-1"`; zero live semantics in transcript; debounced (~500ms) "Generating"; structural completion summary ("Response ready. 340 words, 3 headings, 1 code block"); four-mode verbosity control **in the toolbar, not in settings**. | Screen-reader and braille users. Smaller population than 1–2, highest certainty. | Findings 1–4. SC 4.1.3 Status Messages is Level AA (https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html); Gemini's own ACR marks it not-supported across ~20 surfaces. BotFramework-WebChat #3236; TetraLogical 2024; WebAIM survey #10. | **Very high** | Medium |
| 4 | **`loss-report`** — surface the deterministic verifier as **losses only**, never a pass: "This date is in the original and not in the simplified version." Aggregated digest with drill-down, jump-to-changed-span keyboard command, and an **original↔simplified diff as the primary trust surface**. Explicit failure attribution (source / model / input); never "try a better prompt." | Everyone reading a transformed answer; asymmetric benefit for blind users (verifiability is structurally lower) and for people with ID (acquiescence + model sycophancy compound). | Finding 9 and 11. ATAG 2.0 B.1.2.1. Aggregate-not-enumerate: 13 of 15 BLV participants rejected raw lists as unmanageable via screen reader (https://arxiv.org/pdf/2507.15692). Never a numeric confidence score — blind users reject them on validity grounds (https://par.nsf.gov/servlets/purl/10557171). | High | Medium |
| 5 | **`composer`** — no session/idle/websocket timeout that can discard a draft; per-keystroke autosave with visible recovery; Enter-to-send as a **setting with a heuristic** (confirm when draft > N chars or > M minutes) — not a global default flip; no auto-rewrite of the user's text; ≥24×24 targets (44×44 primary); zero drag-only interactions; published keystrokes-per-task table. | Switch, scanning, gaze, head-pointer, trackball, CP, tremor, fatigue. | Finding 8. WCAG 2.2.1, 2.5.7, 2.5.8. CP typists deliberately trade speed for accuracy and reach control-comparable efficiency, so aggressive autocorrect fights a strategy built over years (https://doi.org/10.1145/3772318.3791184). **Argue on severity-of-failure (a lost 20-minute draft is total task failure), not on the CDC 12.2% mobility figure — that is self-reported difficulty walking, not the AT-using population.** | High | Small |
| 6 | **`@clara/conformance`** — trace capture (`.a11ytrace.json`: DOM snapshots + mutation records + AX-tree diffs + timing) plus ~30 zero-false-positive assertions, runnable live via Playwright or offline in trace mode against any product without credentials. | Maintainers; indirectly every user of every product that runs it. | Zero false positives is axe-core's central design rule and the reason Google and Microsoft built it in (https://github.com/dequelabs/axe-core). The GOV.UK evidence says large orgs reimplement — a suite survives a fork; a library does not. | High | Medium |
| 7 | **`aural`** — markdown → speech/braille-safe render: real `<table>` with `th scope`; code blocks as named `<figure>` with a summary, opt-in focusable region; spoken-safe inline code; emoji named or stripped per pref; nested-list depth expressed structurally; math as a generated speech string in `aria-label` + `aria-braillelabel` with LaTeX kept copyable. | Screen-reader and braille users doing technical work — where code, tables and math are most of the payload. | NVDA silently drops backticks, brackets, braces, dashes, ellipses, tildes; parentheses only in JAWS (https://www.elevenways.be/en/articles/screenreaders-special-characters). MathJax 4 abandoned hidden-MathML; the KaTeX iOS VoiceOver bug has been open since 2017 (https://docs.mathjax.org/en/latest/basic/accessibility.html). SC 1.4.10 declares code/tables/diagrams a reflow **exception** — "we're responsive" is false for AI output. | High | Large |
| 8 | **`human-help`** — a small, curated, locale-aware, machine-readable registry of real help routes, always reachable, **never generated**. | Cognitive/ID, low literacy, anyone in a benefits/legal/medical dead end. | Every model tested by CDT hallucinated, including **inventing disability rights organisations to refer users to** (https://cdt.org/insights/brief-generating-confusion-stress-testing-ai-chatbot-responses-on-voting-with-a-disability/). COGA's Feb 2026 voice module requires reachable human backup (https://www.w3.org/TR/2026/DNOTE-coga-voice-20260205/). Tiny module, named documented harm. | High | Small |
| 9 | **`lowvision`** — defaults and tokens, not a panel: measure 45–80ch, all sizing rem/em, line-height ≥1.5, never justified, two equal polarities plus a low-brightness variant and near-black (not #000) dark, 4.5:1 body / 3:1 non-text with an opt-in 7:1 theme; **reflow-exception treatment** (per-block scroll container with a visible keyboard-reachable scrollbar, soft-wrap toggle, per-block zoom, copy); a message-text-size control on desktop/Electron where OS scaling is inconsistent. Validate at 320px, 400%, **and 8x/16x lens**. | Low vision, magnifier, photophobia; via spacing also dyslexic and cognitively disabled readers. | SC 1.4.8 reads as a spec for this component. Gemini's own ACR reports a **1.4.12 Text Spacing failure** (content cut off when users apply their own spacing) and "Partially Supports" on nearly every vision criterion. WebAIM low-vision survey: 71.2% light-on-dark, 25.6% dark-on-light — dark mode is not "the accessible theme." | High | Medium |
| 10 | **`keys`** — modifier-chord commands (never bare letters; they collide with NVDA/JAWS browse-mode quick nav): prev/next turn, latest, composer, first/last, stop updating, **repeat last response**, read from start. Every command also a named button so Dragon/switch/dwell users can reach it. On-page help `<dialog>`. Focus moves once, on send, to the new turn heading. | Screen-reader, braille, keyboard-only, voice-control users. | ASSETS '24: no prompt-to-response shortcut anywhere; users abusing the "next graphic" key against avatars. W3C NAUR REQ 19a requires repeat-on-request and nothing ships it (https://www.w3.org/TR/naur/). SC 2.1.4 exists because single-character bindings collide. | Medium | Small |
| 11 | **`compose-assist`** — telegraphic/abbreviated prompt expansion with a **visible diff and one-action reject**; multi-turn consolidation that restates the assembled question for confirmation before it reaches the model; saved templates; the pictogram board as one front end. Max 2–3 ranked suggestions in fixed positions (0 = off, a preference). | AAC, switch/gaze, ID, DHH (44.1% report difficulty crafting prompts in English), aphasia, low literacy. | Gulf-of-envisioning work (https://arxiv.org/abs/2309.14459); LLMs degrade most on underspecified multi-turn conversation (+112% unreliability: https://arxiv.org/abs/2505.06120); AAC users report agency loss when AI phrasing substitutes for theirs (https://dl.acm.org/doi/full/10.1145/3544548.3581560). **Never report keystroke savings as time savings** — SpeakFaster's non-AAC arm saved 45–56 points of keystrokes with zero speed gain. | Medium | Medium |
| 12 | **`prefs`** — cut to four fields no platform expresses: `delivery`, `announce`, `reading.level`, `length`. Everything presentational read live from `prefers-reduced-motion` / `prefers-contrast` / `prefers-color-scheme` / `forced-colors`. Starter profile **derived** from those signals + `Accept-Language`, user confirms. Local-first; transmission is an explicit per-destination action. Crosswalk appendix to ISO/IEC 24751-2 and CSS media features. | Anyone using more than one AI product. Realistically: users of the handful of clients that implement it. | Finding 12. EN 301 549 clause 11.7 requires deferring to platform preferences. **Remove `format.short_answers`** (short output cut error detection to 24.5%) and **`format.avoid_tables`** (the fix is `th`/`scope` in a scroll container; suppression pushes models to ASCII art in code fences, which is worse). | Medium | Small |
| 13 | **`asr-repair`** — for the voice path Clara already ships: show the ASR hypothesis instead of demanding re-dictation, let the model propose disambiguations, accept/correct in one or two switch hits, carry a personal vocabulary + correction history in the profile. | Dysarthric and stuttering users, who Clara's current browser speech input **fails silently today**. | Personalisation is the only intervention with strong evidence (31% → 4.6% median WER: https://www.isca-archive.org/interspeech_2021/green21_interspeech.html); MetaICL shows ~10-utterance in-context personalisation is viable. Interspeech 2025's semantic score (88.44% best) exists because WER understates usable output. A 24–27% WER transcript is often semantically recoverable. | Medium | Medium |
| 14 | **`agent`** — lifecycle-event adapter with announcement rate limiting; permission requests prioritised over progress; everything announced also present in a navigable log. Ships as a **Claude Code hook package**. | Screen-reader/braille users of agentic tools — small population, high professional concentration, **documented expert already waiting**. | anthropics/claude-code#70425: a blind Lead Accessibility Architect built an entire accessibility layer on hooks, shell scripts and third-party TTS himself. Flag honestly: there is **no evidence base at all** for agent-harness announcement policy. Build instrumented; expect to be wrong. | Medium | Medium |
| 15 | **`safe-render`** — flash-threshold and motion checks on model-generated renderable output (SVG, canvas, HTML, video) before it is displayed; `prefers-reduced-motion` honoured on generated animation. | Photosensitive epilepsy; vestibular. | WCAG 2.3.1 is **Level A** and is the only criterion in this space with a documented seizure risk. AI products increasingly render generated artifacts inline and **no proposal, product or standard covers this**. | Medium | Small |
| 16 | **`acr-rows` + legal brief** — conservative draft ACR/VPAT rows mapped to WCAG 2.1/2.2 AA, EN 301 549 clauses 9 and 11, Revised 508 E205.4/E207.2; draft EAA Art 13(2)/Annex V statement; a "what this does not claim" section quoting the FTC's prohibited representation verbatim. Defaults to "Partially Supports"; never emits "Supports" without a backing assertion. | Nobody directly — it helps an accessibility engineer win a budget argument and a public buyer write a solicitation, which is how everything above reaches a user. | EAA Art 24(1) makes Annex I "mandatory accessibility requirements" under Art 42(1) of Directive 2014/24/EU. Section 508 + FAR 39.2 makes the ACR a de facto market gate. **Keep SC 2.2.2 out of this generator** (§9). | Medium | Small |

---

## 6. What to build first

The single most likely way this project fails is deferring contact with a disabled user until after months of unvalidated construction (§9). So user contact is week one, in parallel with code, and the first code milestone is days.

### Milestone 0 — days (ship this week)

**0a. Fix Clara's own UI and publish the write-up.** `web/index.html` currently puts `aria-live="polite"` on visible content containers (lines 247 and 270) and runs a second `role="alert"` region (line 267) on the same page — two of the exact pitfalls this brief tells others to avoid, plus a role NVDA sends to braille as the bare word "alert." Rebuild against §4's markup contract: one primed-empty announcer, zero live semantics on results, a heading per result block, focus to the new result heading. Record what it sounded like before and after in NVDA and VoiceOver. **Publishing that self-criticism is the cheapest credibility this project can buy**, and it is the strongest available anti-overlay signal.

**0b. Send the partner-organisation letter** (§10). Recruitment lead time is weeks; start it now.

**0c. Repo honesty pass.** Replace the falsifiable premise in README/ROADMAP/outreach with the §3 replacement claim. Add the verifier scope sentence (§8) to `clara/verify.py`'s docstring, the README and the proxy docs.

### Milestone 1 — week 2 (still days of work)

**`doc-view` v0.** Markdown → `<article>` with real headings, a generated `<nav aria-label="Contents"><ol>` anchor list, `@media print`, and an export. Wire it into the existing web UI and the proxy as a response format. This is the highest-ranked module in the table and it is a transform plus a template. Ship it before anything harder.

### Milestone 2 — weeks 3–5

**`delivery` + anchor**, in the headless core: four commit policies, the "Stop updating" control, `overflow-anchor` guarantees, no auto-scroll, no focus move during generation. Wire `complete` mode straight into the proxy's emulated-SSE path, where it costs nothing because the pipeline already buffers.

**`turns`**: announcer, headings, completion summary, verbosity control.

### Milestone 3 — formative sessions, before the spec is written

Run paper-prototype and think-aloud sessions with 6–10 disabled participants recruited through partner organisations, against **the four existing products plus Clara's own UI** — not against a Clara prototype. Include at least: two refreshable-braille users, two screen-magnifier users at real magnification, two switch or gaze users, two people with intellectual disability and a supporter. Measure comprehension and task time. **Let the sessions decide the defaults for delivery mode and announcement verbosity**, which every module above currently guesses.

### Milestone 4 — weeks 6–10

`loss-report` + diff surface; `composer`; `@clara/conformance` v1 with trace capture; `human-help` registry seeded for ru/en.

### Milestone 5 — quarter 2

`aural`; `lowvision`; `keys`; `prefs` cut to four fields; the Claude Code hook package; the pre-registered announcement-strategy study.

### Explicitly deferred

The TypeScript port of the verifier, the native mobile adapters, the ACR generator, the NAUR conformance table, and the APG pattern proposal. All valuable. None of them is why anyone will look at this project first, and all of them are cheaper once the formative sessions have run.

---

## 7. Adoption strategy

**The honest baseline:** "free MIT code from a solo project" is not the offer that produced axe-core. axe-core was open-sourced by a ~250-person, ~$50M-revenue accessibility firm and spread because Google put it inside Lighthouse. And free tooling saturation has not moved outcomes: 95.9% of the top million home pages had detectable WCAG failures in 2026, *worse* than 2025 (https://webaim.org/projects/million/). Downloads are a disproven proxy.

Ranked by leverage:

### 1. The buyer is not a lever. The buyer is the customer.

This is the single most important reframe, and all three input proposals missed it. Public universities, city and state service portals, school districts, health systems and federal agencies deploying AI assistants **build their own chat UIs on top of APIs**. They can compile a component in. They have budget. And they have hard, dated obligations:

- **Section 508 (29 U.S.C. 794d) + FAR 39.2** — binding on any US federal buyer *today*, with no scope debate about whether a chat product counts (https://www.section508.gov/sell/acr/).
- **DOJ ADA Title II web rule**, WCAG 2.1 AA, reaching contractor-provided tools and platforms — compliance **26 April 2027** (populations ≥50,000) and **26 April 2028** (smaller entities and special districts). **These dates moved on 20 April 2026**; anyone citing April 2026/2027 is working from stale material (https://www.federalregister.gov/documents/2026/04/20/2026-07663/extension-of-compliance-dates-for-nondiscrimination-on-the-basis-of-disability-accessibility-of-web).
- **EAA Art 24(1)** makes Annex I requirements mandatory accessibility requirements in EU public procurement under Directive 2014/24/EU Art 42(1).

**Highest-leverage single artifact in the whole plan:** a model accessibility clause and vendor questionnaire for AI assistants, written to be pasted into an RFP, with the conformance suite behind it. Give it away, ask nothing.

### 2. Be the evidence.

The largest gap in the entire base is that nobody has measured any of this with disabled users of AI chat. A small project can produce a pre-registered, published study for the cost of participant payments. It cannot produce adoption. A citable study gets into every vendor's internal design doc without anyone merging anything. Publish the protocol before running, publish the raw data, publish the result even when it contradicts Clara's defaults.

### 3. Upstream, where no adoption decision is required.

In order: **the Vercel AI SDK chatbot docs and starter template** (every new chat UI is scaffolded from it and its chatbot documentation contains no accessibility guidance at all — a fix propagates to thousands of products with nobody deciding anything); **Open WebUI and LibreChat** (~90 combined open accessibility issues, active contributors, and #29211 is a fix that can land tomorrow); **Gradio, Streamlit, Chainlit, assistant-ui** (where an enormous number of model demos and internal tools live, and accessibility is worst); then a **"Conversational Stream" pattern proposal to w3c/aria-practices** and a **test plan to w3c/aria-at**.

### 4. Claude Code hooks — the one open injection point in a frontier product.

The claim that frontier products have no third-party integration surface is false for exactly one of them. Claude Code has hooks, a plugin system, an accessibility docs page, a responsive issue tracker, and a blind Lead Accessibility Architect who already built a TTS layer on those hooks himself (#70425). **A Claude Code hook package is the fastest available route to a real disabled user using Clara's work.**

### 5. Operators last, and as collaborators.

Not through the product team. Through the accessibility team, with a reproducible test and a patch shape attached. And **not** by weaponising Google's VPAT. Opening with "your own document admits you fail 4.1.3" reads as naive to the professional who wrote it, punishes the only vendor that publishes freely while OpenAI's sits behind a gated portal and Anthropic's reportedly needs an NDA, and creates an incentive for Google to stop publishing. The correct use of that document is: *"Google's published ACR shows this defect class is real and vendor-acknowledged. Here is a test for it and a fix."*

### Spec vs component vs upstream — the verdict

**Spec + executable suite > upstream PRs > component.** The GOV.UK Design System is forked rather than adopted by departments under the same mandate (https://designnotes.blog.gov.uk/2019/02/14/how-the-gov-uk-design-system-can-work-alongside-other-government-design-resources/). Optimise for someone reimplementing Clara's scheduler in their own stack and passing the tests. A test-only devDependency clears third-party review at a fundamentally lower bar than shipped runtime code.

### Preconditions (fail review without these)

Dual licence; DCO; SBOM; OpenSSF Scorecard; signed releases; SECURITY.md; a governance file naming a **second maintainer** or a home in a disability-led organisation. 36% of enterprises name lack of technical support as a top OSS adoption barrier; 61% of unpaid maintainers work alone. No amount of correct ARIA routes around that gate.

### Twelve-month success criteria

Not downloads. One published study cited by someone who does not work on Clara; three upstream PRs merged into projects with real users; one public-sector RFP containing a Clara assertion; one disability organisation co-signing the design record. **Operator adoption of runtime code is explicitly not a twelve-month goal and must not be promised as one.**

---

## 8. How Clara's existing assets fit

**`clara/proxy.py` — reuse, reframe.** The docstring calls emulated streaming an honest cost: *"True token streaming is impossible (the pipeline needs the whole answer), so `stream: true` is emulated."* **That is not a limitation, it is module 2's `complete` delivery mode, already implemented.** Reframe it in the docs and expose it as a user-selectable delivery policy rather than an apology. Keep the two-call cost disclosure exactly as it is.

**`clara/verify.py` + `clara/facts.py` — reuse the mechanism, rewrite the claim.** This is the only genuinely novel asset (no W3C standard requires meaning preservation across a transformation) and it currently makes a claim it cannot support. State plainly, in the docstring, the README and the proxy docs:

> Clara's verifier checks that a **transformation preserved its input**. It requires a source text. In an ordinary chat turn where the model answers from its parameters, there is no source and there is nothing to check against. Checking a simplification against the model's own output proves the simplification is faithful to a possibly-hallucinated original. It does not check anything against the world.

Two consequences for the code:

1. **Never emit an affirmative pass.** `FaithfulnessReport.ok` is fine as an internal boolean; it must never render as "verified," "3 facts checked" or a green tick. Confidence indicators are read as endorsement by cognitively disabled users — a known security-indicator failure pattern — and a rewrite can preserve every number, date and negation while inverting the sense of a clause. **Surface losses only.** The diff is the trust surface.
2. **Do not ship per-claim negative hedging as a rule.** It rests on one 2017 single-shot image-caption study, in a different modality, against contradicting evidence in the same corpus (participants called hedges ambiguous; four of fifteen preferred no indicator; one judged a description reliable *because* it lacked hedges — on the image with the most errors). Report the loss; do not editorialise per claim.

Frame the whole mechanism as an implementation of **ATAG 2.0 SC B.1.2.1** — an existing 2015 W3C Recommendation that no AI product implements — rather than as an invention. Port to zero-dependency TypeScript **later**, with the golden corpus shared byte-for-byte and CI failing on any disagreement between implementations.

**`docs/accessibility-profile.md` + `clara/profile.py` — cut hard.** Fifteen fields → four (`delivery`, `announce`, `reading.level`, `length`). Remove `format.short_answers` and `format.avoid_tables` on the evidence (module 12). Move `symbols.set` to an extension namespace anchored on W3C AAC Symbols Registry BCI concept indices (https://www.w3.org/TR/aac-registry/) rather than free-text set names. Add a crosswalk appendix naming ISO/IEC 24751-2 and 1EdTech AfA PNP as prior art. Add an honest adoption note: *adoption of a portable preference signal has historically tracked legal enforceability, not spec quality; this is a proposal awaiting a hook, not infrastructure.* **Keep Rule 3 ("never fail silently") verbatim — it is the most defensible thing in the spec.** Derive a starter profile from `prefers-*` + `Accept-Language`; never ask anyone to hand-author JSON, which is precisely where GPII-style personalisation stalled.

On transport: the `a11y`-object-on-the-chat-completions-body idea has an engineering error — strict-schema servers reject unknown top-level params and Azure OpenAI does. Use the documented `extra_body` convention plus a header, and say in the spec that some servers will 400.

**`clara/board.py` + `clara/pictograms.py` — turn it around.** The board currently faces the input side. The aphasia design-probe evidence says the higher-value use of symbols is **verifying the answer**, not composing the question (https://arxiv.org/abs/2504.09435). Add an answer-side rendering of key entities and actions from the output so a reader can confirm meaning without re-reading dense text. Keep the input board as one front end for module 11, with the user's own words always primary and any expansion shown as a diff with one-action reject.

**`extension/` — split out.** Move to a separate repository under a different name. Position it as a user-agent tool the user installs for themselves, keep it strictly user-invoked, give it a stable documented script name and root CSS selector, honour a user opt-out that is never re-prompted, commit publicly to not obfuscating to evade blockers, and **offer the signature proactively to AccessiByeBye and the uBlock filter-list maintainers**. Never mention it in operator-facing or organisation-facing material. Ask disabled testers about it directly (§10) rather than assuming the distinction holds.

**`ACCESSIBILITY.md` — rewrite.** It currently documents `role="alert"` *plus* `aria-live="polite"` for status messages: two mechanisms, one of which NVDA sends to braille as the bare word "alert."

**`clara/easyread.py` — relabel.** Output is **"Easy Read draft — not yet validated."** Inclusion Europe standards require validation by people with intellectual disabilities; the LLM Easy Read study insists on professional review before deployment (https://www.frontiersin.org/journals/computer-science/articles/10.3389/fcomp.2024.1394705/full). Labelling unvalidated generated text as Easy Read is a standards violation and the fastest way to lose the endorsements the project needs.

---

## 9. Risks and how this fails

**The most likely failure, stated plainly.** Eighteen months from now: 15,000 lines of Apache-2.0 code implementing announcement and delivery defaults derived from first principles; a founding premise that decayed three times during the research window alone; no adopters, because enterprise third-party review fails on bus factor before anyone reads the code; and no data, because the user study was scheduled last. **A very good, very dead repository.** The mitigation is the ordering in §6, not a scope change.

**The near-miss variant, and it is nearly as likely.** The project succeeds at exactly one thing — a test suite plus a handful of merged upstream PRs — which is a genuinely good outcome and will be experienced as failure because the stated goal was "model operators embed it." Restate the goal now.

**Remediation velocity.** Vendors are fixing the AT floor faster than a solo project can get adopted. The spec and the suite survive this (they measure whether a fix is correct and stay useful after everything is fixed); the library may not. This is the main reason the spec, not the code, is the primary artifact, and the main reason the roadmap weights toward the content layer, which vendors have no incentive to build.

**SC 2.2.2 is the most legally aggressive claim available and the least supported.** Streaming text is arguably neither presented in parallel with other content nor non-essential, and a vendor will say their "Stop generating" button already discharges it. Clara's answer — that aborting the model is not the same as freezing the render — is a good usability argument dressed as a conformance finding. **Argue the AT mechanism; keep 2.2.2 out of the ACR generator.** Asserting a 2.2.2 failure against a named vendor in a generated conformance row is exactly the claim inflation this brief condemns in the overlay industry.

**Legal overclaim is self-inflicted and adoption-killing.** A standalone AI chat product is **not** in the EAA's closed Art 2(2) scope list — it is caught only via its e-commerce sign-up flow, OS bundling, or embedding in a covered service. The EAA's only numeric readability ceiling (CEFR B2, Annex I IV(e)(ii)) applies to **consumer banking alone**. AI Act Art 16(l) high-risk duties were pushed to December 2027 / August 2028 by Regulation (EU) 2026/1744, and Art 50(5)'s "applicable accessibility requirements" may be a null reference for a provider outside EAA scope. Every one of these is commonly misstated in vendor marketing.

**The verifier's scope limit is the project's largest honesty risk** and is addressed in §8. A blind user who cannot independently check a claim, reading "verified," will reasonably conclude the facts were checked against the world. False reassurance built on a deterministic mechanism is worse than false reassurance built on a probabilistic one, because it sounds like proof.

**Simplification is contested by the communities it targets.** Deaf organisations campaigned for verbatim text; the one study of DHH LLM use found demand for *upward* register control on the user's own writing, not downward simplification of the model's; the ID self-advocacy community's most frequent Easy Read complaint is paternalism; the strongest RCT found no comprehension benefit. This is why the flagship is the document view, which changes no words.

**The portable profile will very likely go nowhere.** Four consecutive failures of the same mechanism, and no law obliges any AI vendor to accept a user-supplied accessibility preference. Build it small, expect it to be honoured by nobody outside this project for years, and never let it become the headline.

**Host-integration feasibility is untested.** Most AI chat UIs are React apps with windowed, virtualized message lists that recycle DOM nodes on scroll; CSP and Trusted Types constrain injection; MV3 content scripts run in an isolated world where custom-element and `ElementInternals` behaviour is unverified. Test this against a production host before writing the renderers.

**Underserved groups this brief still does not fully solve, named honestly.** Deafblind users of a display with no speech at all (no ephemeral channel exists; module 1's persistence half-covers it by accident). Multiply disabled users, where Easy Read and blind-user verbosity needs pull in opposite directions and the preference object has **no conflict-resolution semantics** — `reading: easy_read` + `announce: complete` + braille is currently undefined. Older adults with multi-domain age-related impairment, the largest affected population, mentioned nowhere in the evidence base. Voice-control users under mutation, where Dragon's visible-target numbering recomputes on every DOM change across twelve identically named Copy buttons.

**Everything outside English is thinner than it looks.** COGA's "most common 1500 words" ships no authoritative list and has no cross-lingual equivalent. Reading-level norms, Easy Read validation practice, hedging framing, and disordered-speech ASR evidence are all English/US-derived. Project Euphonia's international expansion involved ~132 participants total across four non-English languages against ~3,000 English speakers. **For Clara's ru/es/de/fr locales the evidence base is close to empty**, and localisation is not a translation problem.

### The steelman this project must answer in its README, not assume

> *"This project assumes the correct response to inaccessible AI is to make AI more usable. Some of us think the correct response is that these systems should not be deployed into benefits offices, clinics and legal advice until they work — and that every accessibility layer built on top of an unreliable system extends its licence to operate. You are doing free compliance work for companies with more money than every disability organisation on earth combined. The reason they have not built this is not that they lack a component. It is that it is not a priority. Your free labour changes that arithmetic in exactly the wrong direction."*

The answers are real and must be argued rather than assumed: Clara's loss reporting is a **check on** the system, not a coat of paint on it; the layer's headline claim is what it cannot do; the buyer-first strategy targets deployments that are happening whether or not Clara exists; and the realistic alternative to a bad layer is not "no AI in the benefits office" but "AI in the benefits office with nothing." Put that paragraph, and the answer, in the README.

---

## 10. Open questions for the partner organisations

The project has an outreach package aimed at Russian disability organisations. Ask these, in a formative session with paper prototypes and the four existing products — **before** writing the spec. Pay participants.

**On the flagship (module 1).** Show a long AI answer as a chat transcript and as a document with a table of contents. Which do you get more out of? Which do you *prefer*? (Expect these to diverge — that divergence is the ASSETS '26 finding and it is the reason to measure comprehension, not satisfaction.) For a whole thread: is a running plain-language summary of what has been asked and decided useful, or more to read?

**On pacing (module 2).** With text arriving word by word versus paragraph by paragraph versus all at once when finished — which do you want as your default? Does removing the streaming progress signal make the wait feel broken? For magnifier users: at your actual magnification, what happens to your reading position right now in ChatGPT or a Russian-language assistant?

**On announcement (module 3).** What should the system say when an answer is finished? Nothing, "ready", or "ready, 340 words, 3 headings"? For braille users specifically: what does a streaming answer do to your display today, and would completion-only announcement help or would you lose track of whether anything is happening?

**On the verifier (module 4).** If Clara says "this date is in the original and not in the simple version" — is that useful, or is it one more thing to read? Would you rather see a diff? **And the critical one: if a system tells you it checked something, do you read that as "this is correct"?**

**On simplification, asked without leading.** Do you want AI answers simplified? Do people you work with? Or do you want the original with better structure? Has "we simplified it for you" ever been done to you badly? What would make an Easy Read draft from a machine acceptable — and who has to sign it off?

**On Russian specifically.** Is there an authoritative ясный язык / Easy Read standard and a validator community we should be working to, and what does it require? Does Russian have an accepted common-word frequency list a simplifier could target? What is the state of Russian Sign Language material in this space? Are there Russian-language disordered-speech resources at all? Which of the barriers in this brief are different in Russia because of the products people actually use?

**On the extension.** Show it. *A tool you install yourself that changes other people's websites — is that different from a tool a website owner installs to change the site for you? Does that distinction matter to you, or does it look the same from where you sit?* No community statement addresses this specific case; do not answer it for them.

**On the current Clara.** What is wrong with the reference UI, the pictogram board and the voice input as they stand today? Publish the answer, including the parts that are unflattering.

**On governance.** Who from your organisation would co-own this design record? What would you need in order to put your name on it, and what would make you withdraw it? Are there disabled developers who would take a maintainer seat — the bus factor is a hard gate at every organisation that could adopt this, and a co-maintainer from a disability-led organisation solves the credibility problem and the review problem at the same time.

**Finally, the uncomfortable one.** *Should this exist? Or does an accessibility layer on top of an unreliable system make it easier to deploy that system into places it does not belong?* If the answer comes back "do not build this for benefits and medical text until the underlying system is better," that is a finding, and the project should publish it.