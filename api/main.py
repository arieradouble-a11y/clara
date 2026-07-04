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

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from clara.easyread import easy_read
from clara.llm import get_provider
from clara.pipeline import simplify_text
from clara.readability import analyze
from clara.semantic import semantic_check
from clara.serialize import (
    easyread_dict,
    faithfulness_dict,
    readability_dict,
    result_dict,
    semantic_dict,
)
from clara.verify import verify

app = FastAPI(title="Clara", description="Verified plain-language rewriting.")

_INDEX = Path(__file__).resolve().parent.parent / "web" / "index.html"


class SimplifyRequest(BaseModel):
    text: str
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


class SemanticRequest(BaseModel):
    source: str
    output: str
    lang: str = "en"
    provider: str | None = None


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
    return easyread_dict(easy_read(req.text, provider=provider, lang=req.lang))


@app.post("/semantic")
def semantic_endpoint(req: SemanticRequest) -> dict:
    provider = get_provider(req.provider) if req.provider else None
    return semantic_dict(semantic_check(req.source, req.output, provider=provider, lang=req.lang))


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
