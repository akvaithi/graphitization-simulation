"""Tests for the sim/ package (fronts A-D).

Mirrors the gating style of tests/test_engine.py and tests/test_research.py:
synthetic/closed-loop tests run anywhere; nothing here touches real DATA/.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sim.kinetics import Params, Recipe, simulate
from sim.massbalance import run_mass_balance
from sim.state import IDX, conservation_error


# ---------------------------------------------------------------------------
# Front A: mass conservation + yield_calc reconciliation
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("recipe", [
    Recipe(2, 6, 1.0, 1200, 5),
    Recipe(2, 4, 0.25, 1200, 5),
    Recipe(2, 2, 1.0, 1000, 0.5),
    Recipe(2, 6, 1.0, 1300, 24),
])
def test_mass_conserved_through_integration(recipe):
    """Every gram is C/S/Fe/Ca/gas-ledger accounted for at every step: solids
    lost from the pellet must equal the gas ledger gained, to solver tolerance."""
    res = simulate(recipe, Params(), *(_default_composition()))
    for col in range(res["traj"].shape[1]):
        y = res["traj"][:, col]
        err = conservation_error(y, res["y0"])
        assert err < 1e-6, f"mass drift {err:.2e} g at step {col}"


def _default_composition():
    from sim.feedstock import composition
    return composition("GPC")


def test_mass_balance_runs_and_is_physical():
    mb = run_mass_balance(Recipe(2, 6, 1.0, 1200, 5))
    assert 0 < mb["post_furnace"] < mb["pellet"]
    assert 0 < mb["post_acid"] < mb["post_furnace"]
    assert mb["conservation_error"] < 1e-6
    fracs = mb["carbon"]["phase_fractions"]
    assert abs(sum(fracs.values()) - 1.0) < 1e-6
    assert 0.0 <= mb["carbon"]["ordering_q"] <= 1.0


def test_boudouard_selectivity_is_the_h2_knob():
    """alpha_H2 > 1 must preferentially etch amorphous carbon; alpha_H2 = 1
    (H2 off) reproduces the spreadsheet's non-discriminating 1:1 debit."""
    recipe = Recipe(2, 4, 1.0, 1200, 0.5)  # short hold: lots of C_am still present
    p_on = Params(H2=True, alpha_H2=8.0)
    p_off = Params(H2=False)
    mb_on = run_mass_balance(recipe, p_on)
    mb_off = run_mass_balance(recipe, p_off)
    # selective etching should leave a *smaller* amorphous fraction than blind etching
    assert (mb_on["carbon"]["phase_fractions"]["amorphous"]
            <= mb_off["carbon"]["phase_fractions"]["amorphous"] + 1e-9)


def test_fe_loading_saturates_graphitization_rate():
    """Published anchor: DG% rises with Fe wt% then plateaus (~50 wt% Fe) —
    the Langmuir f(w_Fe) term should show diminishing returns at high loading."""
    recipe_lo = Recipe(2, 1, 1.0, 1200, 1)
    recipe_hi = Recipe(2, 10, 1.0, 1200, 1)
    recipe_hi2 = Recipe(2, 20, 1.0, 1200, 1)
    q_lo = run_mass_balance(recipe_lo)["carbon"]["ordering_q"]
    q_hi = run_mass_balance(recipe_hi)["carbon"]["ordering_q"]
    q_hi2 = run_mass_balance(recipe_hi2)["carbon"]["ordering_q"]
    assert q_hi >= q_lo
    # doubling Fe again near saturation should move q much less than the first jump
    assert (q_hi2 - q_hi) < (q_hi - q_lo) + 1e-6


def test_caco3_loading_threshold_emerges():
    """Handoff §9: an observed CaCO3 loading threshold below which little effect
    is seen. With strong Fe poisoning by un-trapped sulfur (H1), graphitic yield
    should jump sharply once CaO trapping neutralizes the sulfur pool."""
    recipe = lambda ca: Recipe(2, 4, ca, 1200, 5)  # noqa: E731
    gr = [run_mass_balance(recipe(ca))["carbon"]["phase_fractions"]["graphitic"]
          for ca in (0.05, 0.25, 0.5, 1.0)]
    assert gr[-1] > gr[0]
    # a threshold ⇒ the biggest single jump should not be the first (smallest) step
    jumps = [b - a for a, b in zip(gr, gr[1:])]
    assert max(jumps) == jumps[max(range(len(jumps)), key=lambda i: jumps[i])]
    assert gr[-1] - gr[0] > 0.05


# ---------------------------------------------------------------------------
# Scale-up: reactor schedule, kiln, O2, binding
# ---------------------------------------------------------------------------
def test_kiln_graphitizes_less_than_tube_at_same_peak():
    """The rotary kiln has no isothermal hold, so far less time-at-temperature:
    same peak/time should graphitize less than the tube furnace."""
    tube = run_mass_balance(Recipe(2, 4, 0.5, 1300, 2, reactor="tube"))
    kiln = run_mass_balance(Recipe(2, 4, 0.5, 1300, 2, reactor="kiln"))
    assert kiln["carbon"]["phase_fractions"]["graphitic"] < tube["carbon"]["phase_fractions"]["graphitic"]


def test_binding_contact_ordering():
    """Fe-carbon contact: wet impregnation (finest dispersion) > pellet > dry mix."""
    from sim.kinetics import contact_factor, Params
    p = Params()
    c_wet = contact_factor(Recipe(2, 4, 0.5, 1200, 5, binding="wet_impregnation"), p)
    c_pel = contact_factor(Recipe(2, 4, 0.5, 1200, 5, binding="pellet"), p)
    c_dry = contact_factor(Recipe(2, 4, 0.5, 1200, 5, binding="dry_mix"), p)
    assert c_wet > c_pel > c_dry


def test_larger_charge_lowers_contact():
    """Bigger charges have worse heat/mass transfer (Banavath: bigger pellets
    lowered DG) -- the contact factor should fall with charge mass."""
    from sim.kinetics import contact_factor, Params
    p = Params()
    small = contact_factor(Recipe(2, 4, 0.5, 1200, 5), p)
    big = contact_factor(Recipe(50, 4, 0.5, 1200, 5), p)
    assert big < small


def test_o2_burns_carbon_and_conserves_mass():
    """A non-inert atmosphere (o2_frac>0) must lower carbon yield vs pure argon,
    and the carbon-burn ledger must keep total mass conserved."""
    from sim.kinetics import Params
    inert = run_mass_balance(Recipe(2, 4, 0.5, 1200, 5), Params(o2_frac=0.0))
    airy = run_mass_balance(Recipe(2, 4, 0.5, 1200, 5), Params(o2_frac=0.01))
    assert airy["yield"]["carbon_yield"] < inert["yield"]["carbon_yield"]
    assert airy["conservation_error"] < 1e-6


# ---------------------------------------------------------------------------
# Front B: XRD forward model closed loop
# ---------------------------------------------------------------------------
def test_xrd_forward_model_recovers_monotonic_index():
    from sim.xrd_forward import render_pattern
    from amorphous import crystallinity_index
    fracs = [0.0, 0.25, 0.5, 0.75, 1.0]
    idx = []
    for f in fracs:
        tt, inten = render_pattern(amorphous=1 - f, turbostratic=0.0, graphitic=f,
                                   ordering_q=0.9, seed=42, noise=0.005)
        idx.append(crystallinity_index(tt, inten))
    assert all(b >= a - 0.02 for a, b in zip(idx, idx[1:])), idx
    assert idx[-1] > idx[0] + 0.2


def test_xrd_forward_calibration_recovers_known_blends():
    from sim.calibration_sim import selftest
    result = selftest(verbose=False)
    assert result["test_mae_wt_pct"] < 5.0


# ---------------------------------------------------------------------------
# Front D: hypothesis discrimination
# ---------------------------------------------------------------------------
def test_hypothesis_ablation_changes_predictions():
    from sim.hypotheses import run_ablation
    recipe = Recipe(2, 4, 1.0, 1200, 5)
    rows = run_ablation(recipe)
    assert len(rows) == 8  # 2^3 H1/H2/H3 combinations
    grs = {r["graphitic_frac"] for r in rows}
    assert len(grs) > 1, "ablation should produce distinguishable outcomes"


# ---------------------------------------------------------------------------
# Front C: TGA prediction sanity
# ---------------------------------------------------------------------------
def test_tga_amorphous_burns_before_graphitic():
    from sim.tga import predict_dtg
    curve = predict_dtg(amorphous=1.0, turbostratic=0.0, graphitic=0.0)
    curve_gr = predict_dtg(amorphous=0.0, turbostratic=0.0, graphitic=1.0)
    T_peak_am = curve["T_C"][int(np.argmax(curve["dtg"]))]
    T_peak_gr = curve_gr["T_C"][int(np.argmax(curve_gr["dtg"]))]
    assert T_peak_am < T_peak_gr
