"""Generate the interactive dashboard as a single self-contained HTML file.

Reads the corrected ground-truth metrics (internal-standard DG + puck labels),
the closed-loop calibration, and the fitted kinetic parameters, and substitutes
them into ``dashboard/template.html`` -> ``dashboard/dist/index.html``.

The output embeds real run compositions, so it is gitignored and Docker bakes it
at image-build time. Run:  python dashboard/build.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
for _p in (_ROOT, _ROOT / "engine", _ROOT / "engine" / "research"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from analysis.ground_truth import build_ground_truth  # noqa: E402
from calibration import apply_calibration, norm_002_area  # noqa: E402
from sim import feedstock  # noqa: E402
from sim.calibration_sim import _blend_pattern, build_calibration  # noqa: E402

TEMPLATE = Path(__file__).resolve().parent / "template.html"
DIST = Path(__file__).resolve().parent / "dist"
FITTED_PARAMS = _ROOT / "outputs" / "fitted_params.json"


def metrics_payload() -> list[dict]:
    """The per-scan fields the dashboard's charts consume (corrected DG, puck
    labels applied upstream in build_ground_truth)."""
    gt = build_ground_truth()
    out = []
    for r in gt["metrics"]:
        out.append({
            "display_name": r.get("display_name"),
            "form": r.get("form"),
            "temperature_C": r.get("temperature_C"),
            "time_h": r.get("time_h"),
            "fe_ratio": r.get("fe_ratio"),
            "caco3_ratio": r.get("caco3_ratio"),
            "DG_percent": r.get("DG_percent"),          # internal-standard corrected
            "DG_percent_raw": r.get("DG_percent_raw"),
            "istd_applied": r.get("istd_applied", False),
            "crystalline_fraction": r.get("crystalline_fraction"),
            "error": r.get("error"),
        })
    return out


def calibration_payload() -> dict:
    """Closed-loop mixture calibration: train points + held-out predictions."""
    train_w = [0, 20, 40, 60, 80, 100]
    test_w = [10, 50, 90]
    cal = build_calibration(train_w)
    train = [{"known": w, "metric": norm_002_area(*_blend_pattern(w, seed=i))}
             for i, w in enumerate(train_w)]
    test = []
    for j, w in enumerate(test_w):
        x, y = _blend_pattern(w, seed=100 + j)
        pred = apply_calibration(cal, norm_002_area(x, y))
        test.append({"known": w, "predicted": round(pred["crystalline_graphite_wt_pct"], 2)})
    return {"train": train, "test": test, "r2": round(cal["r2"], 4), "degree": cal["degree"]}


def main() -> Path:
    fitted = json.loads(FITTED_PARAMS.read_text())["fitted_values"] if FITTED_PARAMS.exists() else {}
    rmse = json.loads(FITTED_PARAMS.read_text()).get("rmse") if FITTED_PARAMS.exists() else None
    html = TEMPLATE.read_text()
    c_wt, s_wt = feedstock.composition("GPC")
    html = html.replace("__GT_METRICS__", json.dumps(metrics_payload()))
    html = html.replace("__CAL_DATA__", json.dumps(calibration_payload()))
    html = html.replace("__FITTED_PARAMS__", json.dumps(fitted))
    html = html.replace("__C_WT__", repr(float(c_wt)))
    html = html.replace("__S_WT__", repr(float(s_wt)))
    if rmse is not None:
        html = html.replace("fmt(0.0813,3)", "fmt(%.6f,3)" % rmse)
    DIST.mkdir(exist_ok=True)
    out = DIST / "index.html"
    out.write_text(html)
    left = [t for t in ("__GT_METRICS__", "__CAL_DATA__", "__FITTED_PARAMS__",
                        "__C_WT__", "__S_WT__") if t in html]
    assert not left, f"unfilled placeholders: {left}"
    print(f"wrote {out}  ({len(html):,} bytes)")
    return out


if __name__ == "__main__":
    main()
