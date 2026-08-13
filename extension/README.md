# Clara browser extension

Select text on **any** page — including ChatGPT, Claude, or Gemini web UIs —
right-click → **Simplify with Clara** → an accessible overlay shows the
plain-language version with read-aloud and the faithfulness verdict. Vendor
chat UIs don't let you change their backend, so Clara sits **on top** instead.
The toolbar popup also simplifies pasted text.

UI languages: English and Russian (follows the browser). Reading level and
content language are set in the extension options.

> **Status: v0.1, not yet published to a web store and not yet tested across
> browsers** — load it unpacked (below) and file issues. The overlay is built
> accessible-first: `role="dialog"`, keyboard close (Escape), large text, high
> contrast, read-aloud via the browser's speech synthesis.

## Privacy

The selected text is sent **only** to the Clara server configured in the
options — by default `http://localhost:8000`, i.e. your own machine; nothing
leaves it. The public demo (`https://clara-demo.onrender.com`) can be used to
try the plumbing, but it runs the offline mock provider and **returns text
unchanged** (no model key).

## Install (developer mode)

1. Run a Clara server locally: `pip install "clara-plain[api]"` then
   `uvicorn api.main:app` (or `python web/serve.py` from a checkout) — with a
   real provider, e.g. `CLARA_PROVIDER=anthropic ANTHROPIC_API_KEY=…`.
2. Chrome / Edge / any Chromium browser: `chrome://extensions` → enable
   **Developer mode** → **Load unpacked** → choose this `extension/` folder.
3. Select text on a page → right-click → **Simplify with Clara**.

## Files

- `manifest.json` — MV3; permissions are on-demand (`activeTab` + `scripting`),
  no persistent content scripts on every page.
- `background.js` — context menu, the call to Clara, and the injected overlay.
- `popup.html/js` — simplify pasted text from the toolbar.
- `options.html/js` — server URL (custom origins request permission on save),
  language, reading level.
- `_locales/en`, `_locales/ru` — extension UI strings.
