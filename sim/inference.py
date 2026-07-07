"""Fit sim.kinetics.Params to the ground-truth dataset (17 real scans' metrics
+ 6 weighed mass rows) via least squares.

The XRD crystalline_fraction the engine reports is an INDEX, not a mass
fraction (handoff §6-7, Ruland & Smarsly) -- so this fit does NOT claim the
sim's graphitic mass fraction literally equals that index. It fits the sim's
predicted *ordering_q* (front B's ordering coordinate, which drives the same
peak-sharpening/position-shift the index responds to) to track the index's
RANKING across the sweep, while independently fitting the mass-balance
parameters (unaffected by the index caveat) against the real weighed masses.
Treat the resulting parameters as best-fit-to-available-evidence, not as
validated absolute kinetics -- exactly the "grounded vs predictive" split the
handoff draws between fronts A/B and C/D.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np
from scipy.optimize import least_squares

import sim  # noqa: F401
from sim.kinetics import Params, Recipe
from sim.massbalance import run_mass_balance

# Parameters fit on a log10 scale (span decades) vs linear scale.
LOG_FIELDS = ("k0_graph", "K_fe", "h3_gain", "h3_uhalf", "p_poison", "k0_trap", "alpha_H2")
BOUNDS = {
    "k0_graph": (1.0, 1e4), "K_fe": (0.02, 0.6), "h3_gain": (0.1, 10.0),
    "h3_uhalf": (0.002, 0.2), "p_poison": (10.0, 1e4), "k0_trap": (1.0, 1e4),
    "alpha_H2": (1.0, 20.0),
}


def _recipe_from_row(row: dict) -> Recipe | None:
    try:
        return Recipe(pc_mass=float(row["carbon_ratio"]), fe_mass=float(row["fe_ratio"]),
                      caco3_mass=float(row["caco3_ratio"]),
                      temperature_C=float(row["temperature_C"]), time_h=float(row["time_h"]),
                      grade=row.get("carbon_type") or "GPC")
    except (TypeError, ValueError, KeyError):
        return None


def _pack(x0: dict) -> tuple[np.ndarray, list[str]]:
    names = list(x0)
    vec = np.array([np.log10(x0[n]) if n in LOG_FIELDS else x0[n] for n in names])
    return vec, names


def _unpack(vec: np.ndarray, names: list[str]) -> dict:
    return {n: (10 ** v if n in LOG_FIELDS else v) for n, v in zip(names, vec)}


def fit(metrics_rows: list[dict], mass_rows: list[dict],
        base_params: Params | None = None, verbose: bool = True) -> dict:
    """least_squares fit of graphitization-rate + H1/H3 parameters against the
    17-scan crystallinity-index ranking and the 6-row weighed masses."""
    base = base_params or Params()
    x0 = {n: getattr(base, n) for n in LOG_FIELDS}
    vec0, names = _pack(x0)
    lo = np.array([np.log10(BOUNDS[n][0]) if n in LOG_FIELDS else BOUNDS[n][0] for n in names])
    hi = np.array([np.log10(BOUNDS[n][1]) if n in LOG_FIELDS else BOUNDS[n][1] for n in names])

    clean_metrics = [r for r in metrics_rows if r.get("error") in (None, "")
                     and _recipe_from_row(r) is not None]

    def residuals(vec: np.ndarray) -> np.ndarray:
        params = replace(base, **_unpack(vec, names))
        res = []
        for row in clean_metrics:
            recipe = _recipe_from_row(row)
            mb = run_mass_balance(recipe, params)
            target = float(row["crystalline_fraction"])
            res.append(mb["carbon"]["ordering_q"] - target)
        for row in mass_rows:
            if row.get("error") or not row.get("matched_scan"):
                continue
            recipe = _recipe_from_row({
                "carbon_ratio": 2.0,  # xlsx samples are all 2g PC charges
                "fe_ratio": _fe_from_sample(row["sample"]),
                "caco3_ratio": _caco3_from_sample(row["sample"]),
                "temperature_C": _temp_from_sample(row["sample"]),
                "time_h": _time_from_sample(row["sample"]),
            })
            if recipe is None:
                continue
            mb = run_mass_balance(recipe, params)
            m = row["masses"]
            res.append((mb["post_furnace"] - m["post_furnace"]) / m["pellet"])
            if m.get("post_acid") is not None:
                res.append((mb["post_acid"] - m["post_acid"]) / m["pellet"])
        return np.array(res) if res else np.zeros(1)

    result = least_squares(residuals, vec0, bounds=(lo, hi), method="trf",
                           diff_step=1e-2, max_nfev=200)
    fitted = _unpack(result.x, names)
    fitted_params = replace(base, **fitted)
    rmse = float(np.sqrt(np.mean(result.fun ** 2))) if result.fun.size else float("nan")
    if verbose:
        print(f"fit status: {result.message}  RMSE={rmse:.4f}  n_residuals={result.fun.size}")
        for n in names:
            print(f"  {n:12s} {x0[n]:10.4g} -> {fitted[n]:10.4g}")
    return {"params": fitted_params, "fitted_values": fitted, "rmse": rmse,
           "success": bool(result.success), "n_residuals": int(result.fun.size)}


# --- tiny filename-token helpers (avoid re-importing run_parser for the xlsx
# sample-name rows, which already went through run_parser once upstream in
# analysis.ground_truth; these mirror its regex for the 4 numeric tokens) ---
from run_parser import parse_run_filename  # noqa: E402


def _fe_from_sample(name):
    return parse_run_filename(name).get("fe_ratio")


def _caco3_from_sample(name):
    return parse_run_filename(name).get("caco3_ratio")


def _temp_from_sample(name):
    return parse_run_filename(name).get("temperature_C")


def _time_from_sample(name):
    return parse_run_filename(name).get("time_h")
