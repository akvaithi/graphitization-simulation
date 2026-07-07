"""Feedstock composition by petroleum-coke grade.

Reuses the engine's per-grade (carbon, sulfur) mass fractions so the sim and
the spreadsheet-ported yield chemistry agree on the feed. The remainder
(1 - C - S) is treated as releasable volatiles + moisture; real cokes also
carry a small ash fraction (V/Ni) that survives the furnace — lumping it into
volatiles slightly overstates furnace loss, which the devolatilization
efficiency parameter absorbs. Replace with measured proximate/ultimate
analysis when available (handoff section 10, item 8).
"""
from __future__ import annotations

import sim  # noqa: F401  (sys.path bootstrap)
from yield_calc import DEFAULT_COMPOSITION, _FALLBACK_COMPOSITION


def composition(grade: str | None) -> tuple[float, float]:
    """(c_wt, s_wt) mass fractions for a PC grade token like 'GPC'."""
    return DEFAULT_COMPOSITION.get((grade or "").upper(), _FALLBACK_COMPOSITION)
