"""Clara — turn complex text into verified plain language.

Public API:
    from clara import simplify_text
    result = simplify_text("Long legal paragraph...", level="plain")
    print(result.simplified)
    print(result.faithfulness.ok)
"""
from .easyread import EasyReadResult, easy_read
from .facts import inventory
from .pipeline import SimplifyResult, simplify_text
from .readability import Readability, analyze
from .verify import FaithfulnessReport, verify

__version__ = "0.1.0"

__all__ = [
    "simplify_text",
    "SimplifyResult",
    "easy_read",
    "EasyReadResult",
    "analyze",
    "Readability",
    "verify",
    "FaithfulnessReport",
    "inventory",
    "__version__",
]
