# Accessibility

Clara is an accessibility tool, so it has to dogfood accessibility. This is an
honest statement of where the interfaces stand — what conforms, what was tested,
and what does not yet.

## Target and scope

- **Target:** [WCAG 2.2](https://www.w3.org/TR/WCAG22/) **Level AA**.
- **Conforming:** the reference UI (`web/index.html`, served by `api/main.py` or
  `web/serve.py`) and the **exported documents** (`clara/export.py`).
- **Not yet audited to this level:** the Next.js app in `web-next/` (it mirrors
  the reference UI and is a later evolution).

## What conforms today (reference UI)

Verified by manual audit against the WCAG 2.2 AA success criteria, the browser
accessibility tree, and keyboard testing:

- **1.3.1 Info and Relationships** — semantic landmarks (`main`, header, footer),
  real form `label`s (or `aria-label`) on every control, `role="tablist"`/`tab`/
  `tabpanel` with `aria-selected`, `aria-controls`, and `aria-labelledby`.
- **1.3.2 / 3.1.2 Language of Parts** — the source and simplified panels get a
  `lang` attribute matching the chosen content language, so a screen reader
  pronounces simplified Russian/Spanish/German/French correctly even though the
  page chrome is English.
- **1.4.3 Contrast (Minimum)** — measured: body text 15.3:1, muted hints 5.6:1,
  primary buttons (white on teal) 4.99:1, accent text on background 4.66:1,
  selected tab 4.99:1. All ≥ 4.5:1. Dark theme mirrors these.
- **1.4.10 Reflow / 1.4.4 Resize** — relative units and a single-column mobile
  breakpoint; no horizontal scroll at 320px.
- **2.1.1 Keyboard** — every control is reachable and operable by keyboard. Tabs
  implement the [ARIA tabs pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/):
  roving `tabindex`, Arrow/Home/End navigation.
- **2.3.3 Animation from Interactions** — programmatic scrolling respects
  `prefers-reduced-motion`.
- **2.4.7 Focus Visible** — a visible `:focus-visible` outline on all controls.
- **4.1.2 Name, Role, Value** — icon buttons (e.g. a pictogram) carry an
  `aria-label`; status messages use `role="alert"` and `aria-live="polite"`.
- **Images** — every pictogram has `alt` text (its keyword); decorative "no
  picture" placeholders are not announced as images.

## Exported documents

`clara/export.py` produces semantic HTML with a correct `lang`, a single `<h1>`,
real paragraphs / `h2`-`h3` / `ul`-`ol`, and `alt` text on every Easy Read
picture. Printing it yields a tagged PDF; WeasyPrint output targets **PDF/UA-1**.

## Known limitations (honest)

- **The chrome is English only.** Localizing the UI strings (ru/es/de/fr) is
  tracked in the roadmap (Phase 4) — ironic for an accessibility tool, and not
  yet done.
- **No automated axe-core / CI gate yet.** This audit is manual (expert review +
  accessibility tree + keyboard). An automated pass in CI is future work.
- **The Next.js app is not yet audited** to AA.
- **No screen-reader user testing.** The audit is technical; it is not a
  substitute for testing with people who use assistive technology — see below.

## This is not the same as validation with readers

Technical WCAG conformance is necessary but **not sufficient** for Easy Read. The
Easy Read standard (Inclusion Europe) requires that simplified content be
validated by people with intellectual disabilities. That is a separate,
human process — see [`docs/validation-protocol.md`](docs/validation-protocol.md).
Clara stays **assistive, not authoritative** until then, and after.

## How to re-check

1. Run the UI: `python web/serve.py` (or `uvicorn api.main:app`).
2. Keyboard: Tab through every control; use Arrow/Home/End on the tabs.
3. Screen reader: verify control names and that foreign-language panels are
   announced in the right language.
4. Contrast: browser devtools or any WCAG contrast checker on the tokens in
   `web/index.html`.
