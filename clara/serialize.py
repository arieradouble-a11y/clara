"""JSON serialization helpers shared by the CLI, the API, and the dev server —
one place so the wire format never drifts between them."""
from __future__ import annotations

from .easyread import EasyReadLine, EasyReadResult
from .pipeline import SimplifyResult, StructuredResult
from .readability import Readability
from .semantic import SemanticReport
from .structure import block_dict
from .verify import FaithfulnessReport


def readability_dict(r: Readability) -> dict:
    return {
        "words": r.words,
        "sentences": r.sentences,
        "flesch_reading_ease": r.flesch_reading_ease,
        "flesch_kincaid_grade": r.flesch_kincaid_grade,
    }


def faithfulness_dict(fr: FaithfulnessReport) -> dict:
    return {
        "ok": fr.ok,
        "dropped_quantities": fr.dropped_quantities,
        "invented_quantities": fr.invented_quantities,
        "dropped_dates": fr.dropped_dates,
        "invented_dates": fr.invented_dates,
        "dropped_identifiers": fr.dropped_identifiers,
        "invented_identifiers": fr.invented_identifiers,
        "warnings": fr.warnings,
    }


def result_dict(res: SimplifyResult) -> dict:
    return {
        "level": res.level,
        "original": res.original,
        "simplified": res.simplified,
        "source_readability": readability_dict(res.source_readability),
        "output_readability": readability_dict(res.output_readability),
        "faithfulness": faithfulness_dict(res.faithfulness),
    }


def structured_dict(res: StructuredResult) -> dict:
    return {
        "level": res.level,
        "original": res.original,
        "blocks": [block_dict(b) for b in res.blocks],
        "source_readability": readability_dict(res.source_readability),
        "output_readability": readability_dict(res.output_readability),
        "faithfulness": faithfulness_dict(res.faithfulness),
    }


def easyread_line_dict(line: EasyReadLine) -> dict:
    return {
        "text": line.text,
        "keyword": line.keyword,
        "pictogram_id": line.pictogram_id,
        "image_url": line.image_url,
        "symbol_source": line.symbol_source,
    }


def easyread_dict(res: EasyReadResult) -> dict:
    return {
        "original": res.original,
        "lines": [easyread_line_dict(ln) for ln in res.lines],
        "source_readability": readability_dict(res.source_readability),
        "output_readability": readability_dict(res.output_readability),
        "faithfulness": faithfulness_dict(res.faithfulness),
        "symbol_source": res.symbol_source,
    }


def semantic_dict(rep: SemanticReport) -> dict:
    return {
        "available": rep.available,
        "faithful": rep.faithful,
        "issues": [{"type": i.type, "detail": i.detail} for i in rep.issues],
    }
