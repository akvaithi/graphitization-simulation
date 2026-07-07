"""Simulation of Fe-catalyzed, CaCO3-assisted graphitization of petroleum coke.

Package bootstrap: the ported analyzer under engine/ uses flat imports
(`import xrd_analyzer`, `from _shared import ...`), so put both engine dirs on
sys.path once, here, before any sim module imports them.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for _p in (ROOT / "engine", ROOT / "engine" / "research"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
