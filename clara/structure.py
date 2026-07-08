"""A lightweight structural model so headings and lists survive the pipeline.

A real document is not a flat wall of paragraphs — an official notice leans on
headings (to let the eye rest and to signal "this section is about X") and on
lists (steps to take, conditions that apply). Flattening those to paragraphs
throws away exactly the scaffolding that makes a hard document navigable, which
is the opposite of what a plain-language tool should do.

`Block` is the smallest thing we can preserve: a heading, a paragraph, or one
list item. Ingest emits blocks; simplify rewrites each block's text but keeps its
type; export renders them back to semantic HTML (h2/h3, ul/ol). The flat-text
path still works — `blocks_to_text` collapses blocks to the blank-line-separated
paragraphs the readability and faithfulness layers already expect.
"""
from __future__ import annotations

from dataclasses import dataclass

HEADING = "heading"
PARAGRAPH = "paragraph"
LIST_ITEM = "list_item"


@dataclass
class Block:
    type: str                 # HEADING | PARAGRAPH | LIST_ITEM
    text: str
    level: int = 0            # source heading level 1-6 (0 for non-headings)
    ordered: bool = False     # LIST_ITEM: numbered (ol) vs bulleted (ul)


def blocks_to_text(blocks: list[Block]) -> str:
    """Flatten blocks to plain text (blank-line-separated), for the readability
    and faithfulness layers, which reason over flat text, not structure."""
    return "\n\n".join(b.text.strip() for b in blocks if b.text.strip())


def block_dict(b: Block) -> dict:
    return {"type": b.type, "text": b.text, "level": b.level, "ordered": b.ordered}


def block_from_dict(d: dict) -> Block:
    return Block(
        type=str(d.get("type", PARAGRAPH)),
        text=str(d.get("text", "")),
        level=int(d.get("level", 0) or 0),
        ordered=bool(d.get("ordered", False)),
    )
