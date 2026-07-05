# Clara — Next.js app

A full Next.js (App Router + TypeScript) frontend for Clara. The zero-dependency
reference UI in `../web/` stays; this is the richer application.

## Architecture

The engine is Python (FastAPI, `../api/main.py`). The browser talks only to Next;
a route handler at `app/api/clara/[...path]/route.ts` proxies to the Python
backend (`CLARA_API`, default `http://127.0.0.1:8000`) — so there is no CORS to
configure and the engine stays where it is.

```
browser → Next route handler (/api/clara/*) → Clara FastAPI (CLARA_API)
```

## Run

Two processes: the Python API and the Next app.

```bash
# 1) the engine
cd ..
pip install -e ".[api]"
uvicorn api.main:app --port 8000

# 2) the app
cd web-next
npm install
npm run dev            # http://localhost:3000
# CLARA_API=http://127.0.0.1:8000 is the default; override if the API is elsewhere
```

## What's here

- **Simplify** (`app/page.tsx`) — text → Plain Language / Easy Read (with ARASAAC
  pictograms) / target-grade, in 5 languages. Import from a URL or a file
  (PDF/DOCX/HTML/text). Readability, the deterministic faithfulness card, an
  opt-in AI semantic check, accessible HTML / tagged-PDF export, and "Save to
  review".
- **Check a rewrite** (`app/check/page.tsx`) — paste an original and any rewrite;
  get the faithfulness report (no model needed).
- **Reviews** (`app/reviews/page.tsx`) — list and triage: open a review, comment,
  change status, save a revision.
- `components/ResultPanel.tsx` — the shared result view + actions reused by
  Simplify, Check, and Easy Read; `lib/` — typed API client and shared types.
