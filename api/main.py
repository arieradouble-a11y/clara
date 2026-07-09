"""Optional HTTP API (production-ish). Install extras first:

    pip install -e ".[api]"
    uvicorn api.main:app --reload

Endpoints:
    GET  /            reference UI (web/index.html)
    POST /simplify    {"text": "...", "level": "plain"}          (uses an LLM provider)
    POST /verify      {"source": "...", "output": "..."}         (no LLM, offline)
    GET  /health

For a zero-dependency dev server, see web/serve.py instead.
"""
from __future__ import annotations

import base64
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from clara.auth import (
    AuthStore,
    RateLimitedError,
    auth_enabled,
    bearer_token,
    can_approve,
    is_admin,
)
from clara.board import board
from clara.easyread import ask, easy_read
from clara.export import document_html, document_pdf
from clara.i18n import ui_strings
from clara.ingest import from_url, ingest_bytes
from clara.llm import get_check_provider, get_provider
from clara.pictograms import get_symbol_provider
from clara.pipeline import simplify_structured, simplify_text
from clara.proxy import completion_response, models_response, proxy_chat, stream_events
from clara.readability import analyze
from clara.review import ReviewStore
from clara.semantic import semantic_check
from clara.serialize import (
    easyread_dict,
    faithfulness_dict,
    readability_dict,
    result_dict,
    semantic_dict,
    structured_dict,
)
from clara.structure import block_dict, block_from_dict
from clara.verify import verify

app = FastAPI(title="Clara", description="Verified plain-language rewriting.")

_INDEX = Path(__file__).resolve().parent.parent / "web" / "index.html"
_reviews = ReviewStore()
_auth = AuthStore()


def current_user(authorization: str | None = Header(default=None)) -> dict | None:
    """Resolve the caller. When auth is off, returns None (endpoints run
    anonymously). When on, a valid bearer token is required or it's a 401."""
    if not auth_enabled():
        return None
    user = _auth.user_for_token(bearer_token(authorization))
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


class SimplifyRequest(BaseModel):
    text: str
    level: str = "plain"
    grade: int | None = None
    lang: str = "en"
    provider: str | None = None


class StructuredSimplifyRequest(BaseModel):
    blocks: list[dict]            # from /ingest — headings, list items, paragraphs
    level: str = "plain"
    grade: int | None = None
    lang: str = "en"
    provider: str | None = None


class VerifyRequest(BaseModel):
    source: str
    output: str
    lang: str = "en"


class EasyReadRequest(BaseModel):
    text: str
    lang: str = "en"
    provider: str | None = None
    symbols: str | None = None         # symbol set: "arasaac" | "mulberry"


class SymbolSearchRequest(BaseModel):
    keyword: str
    lang: str = "en"
    symbols: str | None = None
    limit: int = 12


class AskRequest(BaseModel):
    text: str                          # the composed (possibly telegraphic) question
    lang: str = "en"
    provider: str | None = None
    symbols: str | None = None


class SemanticRequest(BaseModel):
    source: str
    output: str
    lang: str = "en"
    provider: str | None = None        # falls back to CLARA_CHECK_PROVIDER / default


class ExportRequest(BaseModel):
    format: str = "html"          # "html" | "pdf"
    kind: str = "text"            # "text" | "easyread" | "structured"
    title: str = "Plain-language document"
    lang: str = "en"
    text: str | None = None
    lines: list[dict] | None = None
    blocks: list[dict] | None = None   # for kind="structured"
    footer: str | None = None
    embed_images: bool = False    # inline pictograms as data URIs (offline)


class IngestRequest(BaseModel):
    url: str | None = None
    filename: str | None = None
    content_b64: str | None = None
    ocr: str = "auto"             # scanned-PDF OCR: "auto" | "force" | "off"


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    if _INDEX.exists():
        return _INDEX.read_text(encoding="utf-8")
    return "<h1>Clara</h1><p>Reference UI not found. See web/index.html.</p>"


@app.post("/simplify")
def simplify_endpoint(req: SimplifyRequest) -> dict:
    provider = get_provider(req.provider) if req.provider else None
    res = simplify_text(req.text, level=req.level, grade=req.grade, lang=req.lang, provider=provider)
    return result_dict(res)


@app.post("/simplify_structured")
def simplify_structured_endpoint(req: StructuredSimplifyRequest) -> dict:
    provider = get_provider(req.provider) if req.provider else None
    blocks = [block_from_dict(b) for b in req.blocks]
    res = simplify_structured(blocks, level=req.level, grade=req.grade, lang=req.lang, provider=provider)
    return structured_dict(res)


@app.post("/verify")
def verify_endpoint(req: VerifyRequest) -> dict:
    return {
        "faithfulness": faithfulness_dict(verify(req.source, req.output, lang=req.lang)),
        "source_readability": readability_dict(analyze(req.source, req.lang)),
        "output_readability": readability_dict(analyze(req.output, req.lang)),
    }


@app.post("/easyread")
def easyread_endpoint(req: EasyReadRequest) -> dict:
    provider = get_provider(req.provider) if req.provider else None
    return easyread_dict(easy_read(req.text, provider=provider, lang=req.lang, symbols=req.symbols))


@app.get("/board")
def board_endpoint(lang: str = "en", symbols: str | None = None) -> dict:
    """The AAC-style symbol board for composing a question by tapping pictures."""
    return board(lang=lang, symbols=symbols)


@app.post("/ask")
def ask_endpoint(req: AskRequest) -> dict:
    """Answer a board-composed question; the answer comes back as Easy Read
    lines with pictograms, plus the faithfulness report."""
    provider = get_provider(req.provider) if req.provider else None
    res = ask(req.text, provider=provider, lang=req.lang, symbols=req.symbols)
    d = easyread_dict(res)
    d["question"] = req.text
    return d


@app.post("/pictograms/search")
def pictogram_search_endpoint(req: SymbolSearchRequest) -> dict:
    """Alternative symbols for a keyword, so a reviewer can pick a better picture."""
    provider = get_symbol_provider(req.symbols)
    hits = provider.search(req.keyword, lang=req.lang, limit=req.limit)
    return {
        "provider": provider.name,
        "results": [{"id": s.id, "keyword": s.label, "image_url": s.image_url} for s in hits],
    }


@app.post("/semantic")
def semantic_endpoint(req: SemanticRequest) -> dict:
    # The check runs on an independent grader by default (CLARA_CHECK_PROVIDER),
    # so a model never grades its own rewrite; an explicit provider overrides it.
    provider = get_check_provider(req.provider)
    return semantic_dict(semantic_check(req.source, req.output, provider=provider, lang=req.lang))


@app.post("/ingest")
def ingest_endpoint(req: IngestRequest):
    try:
        if req.url:
            res = from_url(req.url)
        elif req.content_b64 is not None:
            res = ingest_bytes(req.filename or "file.txt", base64.b64decode(req.content_b64), ocr=req.ocr)
        else:
            return JSONResponse({"error": "Provide a url or a file."}, status_code=400)
    except RuntimeError as e:
        return JSONResponse({"error": str(e)}, status_code=501)
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=400)
    return {"text": res.text, "title": res.title, "kind": res.kind,
            "ocr_applied": res.ocr_applied, "blocks": [block_dict(b) for b in res.blocks]}


@app.post("/export")
def export_endpoint(req: ExportRequest):
    doc = document_html(title=req.title, lang=req.lang, kind=req.kind,
                        text=req.text, lines=req.lines, blocks=req.blocks, footer=req.footer,
                        embed_images=req.embed_images)
    if req.format == "pdf":
        try:
            pdf = document_pdf(doc)
        except RuntimeError as e:
            return JSONResponse({"error": str(e)}, status_code=501)
        return Response(pdf, media_type="application/pdf",
                        headers={"Content-Disposition": 'attachment; filename="clara.pdf"'})
    return Response(doc, media_type="text/html; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="clara.html"'})


class Credentials(BaseModel):
    username: str
    password: str


@app.get("/auth/status")
def auth_status(authorization: str | None = Header(default=None)) -> dict:
    user = _auth.user_for_token(bearer_token(authorization)) if auth_enabled() else None
    return {"enabled": auth_enabled(), "users": _auth.count_users(), "user": user}


@app.post("/auth/register")
def auth_register(req: Credentials):
    if not auth_enabled():
        return JSONResponse({"error": "Authentication is not enabled."}, status_code=400)
    if _auth.count_users() > 0:
        return JSONResponse({"error": "Registration is closed. Ask an admin to add your account."},
                            status_code=403)
    try:
        _auth.create_user(req.username, req.password)  # first user bootstraps admin
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    return _auth.login(req.username, req.password)


@app.post("/auth/login")
def auth_login(req: Credentials):
    if not auth_enabled():
        return JSONResponse({"error": "Authentication is not enabled."}, status_code=400)
    try:
        result = _auth.login(req.username, req.password)
    except RateLimitedError as e:
        return JSONResponse({"error": str(e)}, status_code=429,
                            headers={"Retry-After": str(e.retry_after)})
    return result or JSONResponse({"error": "Invalid username or password."}, status_code=401)


@app.post("/auth/users")
def auth_users(user: dict | None = Depends(current_user)):
    """List users so an admin can assign a validator. Admin-only when auth is on."""
    if auth_enabled() and not is_admin(user):
        return JSONResponse({"error": "Admin only."}, status_code=403)
    return {"users": _auth.list_users()}


@app.post("/auth/logout")
def auth_logout(authorization: str | None = Header(default=None)) -> dict:
    _auth.logout(bearer_token(authorization))
    return {"ok": True}


@app.post("/reviews/create")
def reviews_create(payload: dict, user: dict | None = Depends(current_user)):
    try:
        return _reviews.create_review(
            title=payload.get("title", "Untitled"), source=payload.get("source", ""),
            output=payload.get("output", ""), lang=payload.get("lang", "en"),
            level=payload.get("level", "plain"), kind=payload.get("kind", "text"),
            meta=payload.get("meta"), faithful=payload.get("faithful"),
            status=payload.get("status", "in_review"),
            created_by=user["id"] if user else None,
            created_by_name=user["username"] if user else payload.get("created_by_name"))
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.post("/reviews/list")
def reviews_list(payload: dict, user: dict | None = Depends(current_user)):
    return {"reviews": _reviews.list_reviews(status=payload.get("status"))}


@app.post("/reviews/get")
def reviews_get(payload: dict, user: dict | None = Depends(current_user)):
    return _reviews.get_review(payload.get("id")) or JSONResponse({"error": "not found"}, status_code=404)


@app.post("/reviews/comment")
def reviews_comment(payload: dict, user: dict | None = Depends(current_user)):
    author = user["username"] if user else payload.get("author")
    r = _reviews.add_comment(payload.get("id"), author, payload.get("body", ""))
    return r or JSONResponse({"error": "not found"}, status_code=404)


_APPROVAL_STATUSES = {"approved", "rejected"}


@app.post("/reviews/status")
def reviews_status(payload: dict, user: dict | None = Depends(current_user)):
    status = payload.get("status")
    current = _reviews.get_review(payload.get("id"))
    if not current:
        return JSONResponse({"error": "not found"}, status_code=404)
    # Approve/reject is a sign-off: only an admin or the assigned validator.
    if status in _APPROVAL_STATUSES and not can_approve(user, current.get("assignee_id")):
        return JSONResponse({"error": "Only an admin or the assigned validator can approve or reject."},
                            status_code=403)
    try:
        r = _reviews.set_status(payload.get("id"), status)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    return r or JSONResponse({"error": "not found"}, status_code=404)


@app.post("/reviews/assign")
def reviews_assign(payload: dict, user: dict | None = Depends(current_user)):
    """Assign a validator to a review. Admin-only when auth is on."""
    if auth_enabled() and not is_admin(user):
        return JSONResponse({"error": "Only an admin can assign reviews."}, status_code=403)
    r = _reviews.assign_review(payload.get("id"), payload.get("assignee_id"),
                               payload.get("assignee_name"))
    return r or JSONResponse({"error": "not found"}, status_code=404)


@app.post("/reviews/revision")
def reviews_revision(payload: dict, user: dict | None = Depends(current_user)):
    r = _reviews.add_revision(payload.get("id"), payload.get("output", ""),
                              note=payload.get("note"), faithful=payload.get("faithful"))
    return r or JSONResponse({"error": "not found"}, status_code=404)


# --- OpenAI-compatible accessibility proxy (clara-proxy) -----------------------
# Any OpenAI-compatible chat client can point its base URL at /v1: the upstream
# answer is simplified to the chosen reading level and fact-checked before the
# person sees it. See clara/proxy.py for the design and the honest costs.

@app.post("/v1/chat/completions")
def openai_chat_completions(payload: dict):
    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        return JSONResponse({"error": {"message": "'messages' must be a non-empty list.",
                                       "type": "invalid_request_error"}}, status_code=400)
    mt, temp = payload.get("max_tokens"), payload.get("temperature")
    model = str(payload.get("model") or "")
    try:
        res = proxy_chat(
            messages,
            model=model,
            options=payload.get("clara") or {},
            max_tokens=2000 if mt is None else int(mt),
            temperature=0.2 if temp is None else float(temp),
        )
    except (TypeError, ValueError) as e:
        return JSONResponse({"error": {"message": str(e), "type": "invalid_request_error"}}, status_code=400)
    except RuntimeError as e:
        # e.g. a broken CLARA_PROFILE file — fail loudly, never silently drop
        # someone's accessibility settings.
        return JSONResponse({"error": {"message": str(e), "type": "server_error"}}, status_code=500)
    except Exception as e:
        return JSONResponse({"error": {"message": f"Upstream provider failed: {e}",
                                       "type": "upstream_error"}}, status_code=502)
    if payload.get("stream"):
        return StreamingResponse(stream_events(res, model), media_type="text/event-stream")
    return completion_response(res, model)


@app.get("/v1/models")
def openai_models() -> dict:
    return models_response()


@app.get("/i18n")
def i18n() -> dict:
    return ui_strings()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
