# We shipped the anti-patterns we were about to tell others to avoid

*2026-09-05 — a write-up of the first fix from the
[accessibility layer design brief](a11y-layer-design-brief.md).*

Before proposing a behaviour contract for how AI interfaces should announce
streaming answers to screen readers, we audited our own. Clara's reference UI
violated three of the rules the brief tells everyone else to keep. This is what
was wrong, why it is wrong, and what we changed.

We are publishing this because a project that intends to tell model operators
how to do accessibility has no standing until it has audited itself in public.

## What was wrong

### 1. Live semantics on the content itself

```html
<!-- before -->
<section id="results" class="hidden" aria-live="polite"> … </section>
<div id="ask-result" class="hidden" aria-live="polite"></div>
```

Both containers held the *whole* result — metrics, source panel, output panel,
faithfulness card — and got `aria-live` directly on the content.

Live-region change events are queued **one per mutation**, and the only
coalescing behaviour ARIA specifies is for `aria-atomic="true"`. A container
that is re-rendered in pieces therefore produces an unbounded, un-deduplicated
queue of announcements. You cannot engineer out of it with `aria-busy`,
`aria-atomic` or `aria-relevant`: support is inconsistent, and `aria-busy` is
read through by everything except JAWS.

The correct shape is to **decouple announcement from content**: a separate,
visually-hidden region outside the result, receiving a short summary.

### 2. A second live region on the same page

```html
<!-- before -->
<div id="error" class="error hidden" role="alert"></div>
```

`role="alert"` carries an implicit `aria-live="assertive"`. So the page ran two
live regions at once. The ARIA specification is **silent** on what happens when
two live regions update simultaneously ([w3c/aria#1689](https://github.com/w3c/aria/issues/1689),
still open), and in practice only one is spoken — non-deterministically. On a
refreshable braille display, VoiceOver treats polite regions assertively, so
this also destroys the line the reader was on.

### 3. The regions were not empty at mount

Both regions were created with `class="hidden"` (`display: none`) and populated
at the moment they were revealed. A live region must be **in the accessibility
tree and empty** before content lands in it. A region that appears together with
its text announces nothing at all — the most common silent failure in this area,
and one that looks perfectly correct in code review.

## What we changed

A single announcer, mounted once at the document root, empty:

```html
<div id="clara-announcer" class="clara-vh" aria-live="polite" aria-atomic="false"></div>
```

- `aria-live` removed from `#results` and `#ask-result`; `role="alert"` removed
  from the error box. Results and errors are now plain content. **The page has
  exactly one live region.**
- `.clara-vh` is clipped, not `display: none` — a `display: none` live region is
  not in the accessibility tree at all.
- Every result gets a real `<h2>` with `tabindex="-1"`, and focus moves there
  once when the result arrives. Headings are how ~72% of screen-reader users
  navigate a page; landmarks are the primary method for 3.7%. The single most
  common complaint from blind users of AI chat products is that there is no way
  to get to the answer.
- On completion the announcer says what arrived — "Ready. 41 words." /
  "Ответ готов. Строк: 3." — because WCAG 2.2 SC 4.1.3 (Status Messages, Level
  AA) requires it, and because "nothing tells you when generation finished" is a
  documented complaint.
- The "working" announcement is **debounced by 500 ms**, so a fast answer says
  nothing at all rather than "working…" immediately followed by "ready".
- Errors are announced through the same single region, so removing
  `role="alert"` did not make them silent.

The announcer writes with clear-then-set, because screen readers suppress an
identical repeat:

```js
el.textContent = "";
setTimeout(() => { el.textContent = msg; … }, 60);
```

## Two bugs the fix itself introduced, caught in the browser

Worth recording, because both are easy to ship and invisible in review.

**`requestAnimationFrame` silently swallowed every announcement.** The first
version used `requestAnimationFrame` for the clear-then-set step. `rAF` does not
run in a hidden or throttled tab, so the announcement never happened at all —
verified in a browser where `document.hidden === true` and no frame fired within
500 ms. Announcements must not depend on a paint. It now uses a timer.

**Adding a fourth tab broke reflow.** The tab bar was `width: max-content` with
no wrapping. With four tabs it forced horizontal scrolling at 320 px — a WCAG
1.4.10 failure we introduced ourselves when we added the Ask tab. It now wraps;
verified at 320 px with no horizontal scroll.

## What we have NOT verified

Honesty matters more here than a clean report:

- **No screen reader has been run against this.** The changes are verified
  structurally — one live region, empty at mount, announcement text observed
  changing in the DOM, focus landing on the heading, no horizontal scroll at
  320 px. That is not the same as knowing what NVDA, JAWS or VoiceOver actually
  say, and it is certainly not the same as asking a blind person whether it
  helps.
- **No braille display has been tested**, which is where the two-live-region bug
  did its worst damage.
- **The announcement wording and the debounce interval are guesses.** They are
  reasoned from published findings, not measured. Whether a completion summary
  should say the word count at all, and whether 500 ms is right, are questions
  for the formative sessions described in §10 of the brief.

If you use a screen reader and any of this is wrong, please open an issue. That
is the fastest way to make it correct.

## The same fix, in the Next app

`web-next` had the same three problems: `aria-live` on two result sections and
four `role="alert"` error boxes. It now has one `AnnouncerProvider` mounted at
the app root with a `useAnnounce()` hook; result sections and error boxes are
plain content.

## Files

- [`web/index.html`](../../web/index.html) — announcer, result headings, focus.
- [`web-next/components/Announcer.tsx`](../../web-next/components/Announcer.tsx) — the React equivalent.
- [`ACCESSIBILITY.md`](../../ACCESSIBILITY.md) — updated conformance statement.
