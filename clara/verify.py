"""Faithfulness verification — the heart of Clara.

Any model can shorten text. The value here is proving the shortened text did
not silently drop a deadline, flip a negation, or invent a number. This module
compares the deterministic fact inventory of the source against the output and
reports drift. Numbers and dates are hard signals; negation/obligation/condition
deltas are review warnings for a human to confirm.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .facts import inventory


@dataclass
class FaithfulnessReport:
    dropped_quantities: list[str] = field(default_factory=list)
    invented_quantities: list[str] = field(default_factory=list)
    dropped_dates: list[str] = field(default_factory=list)
    invented_dates: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when no hard facts were dropped or invented. Warnings do not
        flip this — they ask a human to look, they don't condemn the output."""
        return not (
            self.dropped_quantities
            or self.invented_quantities
            or self.dropped_dates
            or self.invented_dates
        )


def _diff(src: Counter, out: Counter) -> tuple[list[str], list[str]]:
    dropped = sorted((src - out).elements())
    invented = sorted((out - src).elements())
    return dropped, invented


def verify(source: str, output: str) -> FaithfulnessReport:
    s, o = inventory(source), inventory(output)
    dq, iq = _diff(s["quantities"], o["quantities"])
    dd, idt = _diff(s["dates"], o["dates"])

    warnings: list[str] = []
    if s["negation"] and o["negation"] < s["negation"]:
        warnings.append(
            f"Negation may be lost: source has {s['negation']} negation word(s), "
            f"simplified has {o['negation']}. Verify the meaning was not inverted."
        )
    if s["obligation"] and o["obligation"] < s["obligation"]:
        warnings.append(
            f"Obligation may be weakened: source has {s['obligation']} obligation "
            f"word(s) (must/shall/required), simplified has {o['obligation']}."
        )
    if s["condition"] and o["condition"] < s["condition"]:
        warnings.append(
            f"A condition may be dropped: source has {s['condition']} condition "
            f"word(s) (if/unless/except), simplified has {o['condition']}."
        )

    return FaithfulnessReport(dq, iq, dd, idt, warnings)
