"""Pytest bootstrap: the analyzer engine lives under engine/ (ported from
akvaithi/xrd-graphitization-analyzer) and uses flat imports (`import
xrd_analyzer`, `from _shared import ...`), so both directories must be on
sys.path before any test module imports them."""
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(_ROOT, "engine"), os.path.join(_ROOT, "engine", "research"), _ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)
