"""Optional HTTP API. Install extras first:  pip install -e ".[api]"

Run:  uvicorn api.main:app --reload
POST /simplify  {"text": "...", "level": "plain"}
"""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from clara.pipeline import simplify_text

app = FastAPI(title="Clara", description="Verified plain-language rewriting.")


class SimplifyRequest(BaseModel):
    text: str
    level: str = "plain"
    grade: int | None = None


@app.post("/simplify")
def simplify_endpoint(req: SimplifyRequest) -> dict:
    res = simplify_text(req.text, level=req.level, grade=req.grade)
    fr = res.faithfulness
    return {
        "level": res.level,
        "simplified": res.simplified,
        "source_readability": vars(res.source_readability),
        "output_readability": vars(res.output_readability),
        "faithfulness": {
            "ok": fr.ok,
            "dropped_quantities": fr.dropped_quantities,
            "invented_quantities": fr.invented_quantities,
            "dropped_dates": fr.dropped_dates,
            "invented_dates": fr.invented_dates,
            "warnings": fr.warnings,
        },
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
