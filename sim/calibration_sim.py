"""Front B calibration: use sim.xrd_forward as the "physical mixture" stand-in
called for in the handoff (section 6/8) -- scan blends of pure amorphous PC and
pure crystalline graphite at known wt%, regress norm_002_area vs wt%, and check
the fit recovers held-out blends. This validates the forward model + the
engine's calibration machinery together, before any real standards are scanned.

Also provides ``invert_scan``: apply a fitted calibration to a REAL DATA/*.xy
scan to get an estimated absolute crystalline-graphite wt%, and combine it with
sim.massbalance's carbon mass yield to get the corrected crystalline-graphite
yield the project is chasing (handoff section 4, "the number the whole effort
is really chasing").
"""
from __future__ import annotations

import numpy as np

import sim  # noqa: F401
from calibration import apply_calibration, fit_calibration, norm_002_area
from sim.xrd_forward import render_pattern
from xrd_analyzer import XRDPattern


def _blend_pattern(graphite_wt_pct: float, *, seed: int = 0, noise: float = 0.01):
    """Physical-mixture stand-in: pure PC (100% amorphous) blended with pure
    synthetic graphite (100% graphitic, fully ordered) at a known mass
    fraction -- exactly the handoff's recommended primary calibration route,
    generated with the forward model instead of a real scan."""
    f = graphite_wt_pct / 100.0
    return render_pattern(amorphous=1 - f, turbostratic=0.0, graphitic=f,
                          ordering_q=1.0, seed=seed, noise=noise)


def build_calibration(train_wt_pct=(0, 20, 40, 60, 80, 100)) -> dict:
    mvals = [norm_002_area(*_blend_pattern(w, seed=i)) for i, w in enumerate(train_wt_pct)]
    cal = fit_calibration(mvals, list(train_wt_pct))
    cal.update({"metric": "norm_002_area", "source": "sim.xrd_forward blends"})
    return cal


def selftest(verbose: bool = True) -> dict:
    """Mirrors engine/research/calibration.selftest but drives the sim's own
    forward model, so it validates the sim's rendering + engine's calibration
    machinery jointly against held-out known blends."""
    train_w = [0, 20, 40, 60, 80, 100]
    test_w = [10, 50, 90]
    cal = build_calibration(train_w)
    errs, rows = [], []
    for j, w in enumerate(test_w):
        x, y = _blend_pattern(w, seed=100 + j)
        pred = apply_calibration(cal, norm_002_area(x, y))
        err = abs(pred["crystalline_graphite_wt_pct"] - w)
        errs.append(err)
        rows.append((w, pred["crystalline_graphite_wt_pct"], err))
    mae = float(np.mean(errs))
    result = {"calibration": cal, "test_mae_wt_pct": round(mae, 2),
              "passed": bool(mae < 5.0)}
    if verbose:
        print(f"sim calibration: degree={cal['degree']} R2={cal['r2']:.4f}")
        for known, pred, err in rows:
            print(f"  known {known:5.1f} -> predicted {pred:6.2f}  (err {err:4.2f})")
        print(f"held-out MAE = {mae:.2f} wt%  -> {'PASS' if result['passed'] else 'FAIL'}")
    return result


def invert_scan(xy_path: str, cal: dict | None = None) -> dict:
    """Apply a (sim-built, or supplied) calibration to a real scan and return
    the estimated absolute crystalline-graphite wt%."""
    cal = cal or build_calibration()
    p = XRDPattern.from_file(xy_path)
    metric = norm_002_area(p.two_theta, p.intensity)
    return apply_calibration(cal, metric)
