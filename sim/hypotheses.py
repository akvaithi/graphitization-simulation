"""Front D: discriminate H1 (sulfur trapping) / H2 (Boudouard etching) /
H3 (catalyst dispersion) by ablation and, where mass/XRD ground truth exists,
by fitting each of the 8 on/off combinations and ranking by residual + AIC.

This does not run molecular dynamics. It stages the problem for the sibling
ReaxFF repo (handoff §1 front D) by (a) showing which mechanisms are needed to
reproduce the qualitative anchors -- CaCO3 loading threshold, onset shift, Fe
saturation, the H2 quality-vs-yield tradeoff -- and (b) exporting the
best-fit phase composition + interface conditions as a JSON handoff for an
atomistic follow-up.
"""
from __future__ import annotations

import itertools
import json

import numpy as np

import sim  # noqa: F401
from sim.kinetics import Params, Recipe
from sim.massbalance import run_mass_balance

HYPOTHESES = ("H1", "H2", "H3")


def run_ablation(recipe: Recipe, base_params: Params | None = None) -> list[dict]:
    """Run all 8 H1/H2/H3 on/off combinations for one recipe."""
    base = base_params or Params()
    rows = []
    for h1, h2, h3 in itertools.product([False, True], repeat=3):
        p = base.with_hypotheses(h1, h2, h3)
        mb = run_mass_balance(recipe, p)
        fracs = mb["carbon"]["phase_fractions"]
        rows.append({
            "H1": h1, "H2": h2, "H3": h3,
            "graphitic_frac": fracs["graphitic"],
            "amorphous_frac": fracs["amorphous"],
            "ordering_q": mb["carbon"]["ordering_q"],
            "carbon_yield": mb["yield"]["carbon_yield"],
            "sulfur_remaining_g": mb["solids"]["S"],
            "post_furnace": mb["post_furnace"],
        })
    return rows


def quality_yield_tradeoff(temperature_C: float = 1200, time_h: float = 5,
                           fe_mass: float = 4.0, pc_mass: float = 2.0,
                           caco3_range=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.5, 2.0)) -> list[dict]:
    """H2's signature: more CaCO3 -> more selective etching -> higher ordering
    but lower carbon yield. Sweeps CaCO3 with H2 on vs off (alpha_H2=1) to make
    the tradeoff explicit, as the handoff (§9) asks."""
    rows = []
    for caco3 in caco3_range:
        recipe = Recipe(pc_mass, fe_mass, caco3, temperature_C, time_h)
        for h2 in (False, True):
            p = Params().with_hypotheses(True, h2, True)
            mb = run_mass_balance(recipe, p)
            rows.append({"caco3_mass": caco3, "H2": h2,
                        "graphitic_frac": mb["carbon"]["phase_fractions"]["graphitic"],
                        "carbon_yield": mb["yield"]["carbon_yield"]})
    return rows


def h2_carbon_yield_test(params: Params | None = None,
                         temperature_C: float = 1200, time_h: float = 5,
                         fe_mass: float = 4.0, pc_mass: float = 2.0,
                         caco3_range=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.5)) -> dict:
    """The decisive H2 test the requester asked for: does carbon yield DROP as
    CaCO3 rises (H2 real: Boudouard gasifies carbon) or stay FLAT (against H2)?

    Returns the model's carbon-yield-vs-CaCO3 curves with H2 ON vs OFF, so the
    signature is explicit, plus the slope (yield per gram CaCO3) under H2 ON.
    Overlay measured points via ``attach_measured``. Boudouard carbon loss and its
    preference for reactive/amorphous carbon are established (Guo *Fuel* 2021;
    the reverse-Boudouard reactivity literature) — the open question is only
    *how much* it operates here, which the yield slope quantifies.
    """
    p = params or Params()
    on, off = [], []
    for caco3 in caco3_range:
        recipe = Recipe(pc_mass, fe_mass, caco3, temperature_C, time_h)
        mb_on = run_mass_balance(recipe, p.with_hypotheses(p.H1, True, p.H3))
        mb_off = run_mass_balance(recipe, p.with_hypotheses(p.H1, False, p.H3))
        on.append({"caco3_mass": caco3, "carbon_yield": mb_on["yield"]["carbon_yield"]})
        off.append({"caco3_mass": caco3, "carbon_yield": mb_off["yield"]["carbon_yield"]})
    xs = [r["caco3_mass"] for r in on]
    ys = [r["carbon_yield"] for r in on]
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denom = sum((x - mean_x) ** 2 for x in xs) or 1.0
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denom
    return {"h2_on": on, "h2_off": off,
            "yield_slope_per_g_caco3_h2on": slope,
            "interpretation": ("negative slope => H2 (Boudouard) is costing carbon; "
                               "flat (~0) => the yield data does not support H2 here"),
            "conditions": {"fe_mass": fe_mass, "temperature_C": temperature_C,
                           "time_h": time_h, "pc_mass": pc_mass}}


def attach_measured_yields(mass_rows: list[dict]) -> list[dict]:
    """Turn ground-truth mass rows into measured carbon-recovery points for the
    H2 plot: carbon recovered / feed carbon vs CaCO3 loading. The 6 rows do not
    cleanly isolate CaCO3 (Fe/time vary too), so these are context for the model
    curve, not a controlled sweep — flagged per point with its Fe/time."""
    from run_parser import parse_run_filename
    from yield_calc import masses_from_name
    out = []
    for r in mass_rows:
        if r.get("error") or not r.get("result"):
            continue
        res = r["result"]
        chem = res["chemistry"]
        yld = res["yield"]
        pr = parse_run_filename(r["sample"])
        m = masses_from_name(r["sample"], res["inputs"]["pellet"])
        feed_c = chem.get("actual_C")
        surv_c = yld.get("measured_C_after_furnace")
        if not feed_c or surv_c is None:
            continue
        out.append({"caco3_mass": (m or {}).get("caco3_mass"),
                    "carbon_recovery": surv_c / feed_c,
                    "fe": pr.get("fe_ratio"), "time_h": pr.get("time_h"),
                    "sample": r["sample"]})
    return out


def caco3_threshold_scan(fe_mass: float = 4.0, temperature_C: float = 1200,
                         time_h: float = 5, pc_mass: float = 2.0,
                         caco3_range=None) -> list[dict]:
    """Emergent-threshold check (handoff §9): scan CaCO3 finely and look for a
    loading below which graphitization barely proceeds (poisoned by
    un-trapped sulfur) and above which it jumps -- the qualitative signature
    the group observed."""
    caco3_range = caco3_range or np.linspace(0.0, 1.0, 21)
    rows = []
    for ca in caco3_range:
        mb = run_mass_balance(Recipe(pc_mass, fe_mass, float(ca), temperature_C, time_h))
        rows.append({"caco3_mass": float(ca),
                    "graphitic_frac": mb["carbon"]["phase_fractions"]["graphitic"],
                    "ordering_q": mb["carbon"]["ordering_q"]})
    return rows


def rank_hypotheses(ablation_rows: list[dict], target_graphitic_frac: float) -> list[dict]:
    """Rank the 8 ablations by |predicted - target| graphitic fraction --
    a stand-in for AIC-style ranking once real per-run targets exist (from
    analysis.ground_truth's crystalline_fraction, calibrated to wt% via
    sim.calibration_sim)."""
    ranked = sorted(ablation_rows,
                    key=lambda r: abs(r["graphitic_frac"] - target_graphitic_frac))
    for i, r in enumerate(ranked):
        r["rank"] = i + 1
        r["abs_error"] = abs(r["graphitic_frac"] - target_graphitic_frac)
    return ranked


def export_reaxff_handoff(recipe: Recipe, params: Params, out_path: str) -> dict:
    """Package the fitted state for a ReaxFF follow-up in the sibling repo:
    interface conditions (T, Fe wt%, CaO wt%, S wt%) and the resulting phase
    composition, so an MD study can be seeded at physically motivated points
    (e.g. the CaCO3-threshold boundary) instead of an arbitrary grid."""
    mb = run_mass_balance(recipe, params)
    solids = mb["solids"]
    total_solid = sum(solids.values())
    payload = {
        "recipe": {"pc_mass": recipe.pc_mass, "fe_mass": recipe.fe_mass,
                  "caco3_mass": recipe.caco3_mass,
                  "temperature_C": recipe.temperature_C, "time_h": recipe.time_h},
        "interface_wt_fractions": {k: v / total_solid for k, v in solids.items()},
        "phase_fractions": mb["carbon"]["phase_fractions"],
        "ordering_q": mb["carbon"]["ordering_q"],
        "hypotheses_active": {"H1": params.H1, "H2": params.H2, "H3": params.H3},
        "note": "Kinetic-model handoff for atomistic follow-up (no MD run here); "
                "see sibling ReaxFF repo referenced in SIMULATION_HANDOFF.md.",
    }
    with open(out_path, "w") as fh:
        json.dump(payload, fh, indent=2)
    return payload
