"""Reaction kinetics over the furnace schedule (fronts A + D).

One ODE state (grams, see sim.state) integrated through ramp + hold. Every
process is Arrhenius; the three CaCO3 hypotheses from the handoff (section 9)
enter as explicit, independently switchable terms:

- H1 sulfur trapping   : CaO + S -> CaS + 1/2 O2, removing the sulfur that
                         otherwise poisons the Fe catalyst.
- H2 Boudouard etching : calcination CO2 gasifies carbon (C + CO2 -> 2 CO)
                         with selectivity alpha = k_amorphous / k_graphitic;
                         alpha = 1 reproduces the spreadsheet's blind 1:1 debit.
- H3 catalyst dispersion: CaO improves Fe-carbon contact, multiplying the
                         graphitization rate.

The CO2 released by calcination sits in a transient in-pellet pool that either
reacts (Boudouard) or escapes with the sweep gas, so Boudouard *efficiency* is
emergent (temperature- and contact-dependent), not assumed.

Default parameters are hand-tuned to the published anchors (Fe plateau ~50 wt%,
graphitization onset region, S gone by ~1500 C thermally) and are refined
against the ground-truth dataset by sim.inference.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np
from scipy.integrate import solve_ivp

from sim.state import (FIELDS, IDX, M_C, M_CaCO3, M_CaO, M_CaS, M_CO, M_CO2,
                       M_S, Recipe, carbon_mass, initial_state)

R_GAS = 8.314  # J/mol/K
M_O = M_CaS + 0.0  # placeholder to keep linters quiet; real O mass below
M_O = M_CaO + M_S - M_CaS  # 15.999 per mol trapped: the O2 leaving in H1


@dataclass
class Params:
    """Kinetic parameters. k0 in 1/min (or 1/(g*min) for bimolecular), Ea in J/mol."""
    # devolatilization (VOL -> gas)
    k0_dev: float = 1.7e3
    Ea_dev: float = 60e3
    # calcination (CaCO3 -> CaO + CO2), bulk onset ~700-850 C
    k0_cal: float = 3e7
    Ea_cal: float = 180e3
    # CO2 escape from the pellet (pool -> sweep gas)
    k_esc: float = 0.5
    # Boudouard (C + CO2 -> 2 CO), first order in pool CO2
    k0_boud: float = 1e5
    Ea_boud: float = 150e3
    alpha_H2: float = 8.0        # amorphous/graphitic selectivity (H2 knob; 1 = blind)
    # graphitization (C_am -> C_turb -> C_gr), Fe-catalyzed
    k0_graph: float = 70.0
    Ea_graph: float = 100e3
    K_fe: float = 0.18           # Langmuir half-saturation in Fe mass fraction (plateau ~50 wt%)
    gamma_turb: float = 0.7      # (turb->gr rate) / (am->turb rate)
    q_gain: float = 1.0          # ordering-coordinate rate multiplier
    # H3 dispersion: rate multiplier 1 + h3_gain * u/(u + u_half), u = CaO wt frac of solids
    h3_gain: float = 2.0
    h3_uhalf: float = 0.02
    # sulfur: thermal release (slow below ~1400 C) and H1 trapping by CaO
    k0_sgas: float = 4.6e5
    Ea_sgas: float = 250e3
    k0_trap: float = 100.0       # 1/(g CaO * min); fast once CaO exists and T > onset
    Ea_trap: float = 80e3
    # Fe poisoning by free sulfur: rate *= 1 / (1 + p_poison * S/Fe). Strong by
    # default: with GPC (4.5 wt% S) the CaO from 0.25 g CaCO3 is substoichiometric
    # to sulfur, so free S survives and kills ordering — the observed threshold.
    p_poison: float = 800.0
    # furnace
    ramp_C_per_min: float = 10.0
    T0_C: float = 25.0
    # acid wash removal efficiencies
    eta_wash_fe: float = 0.97
    eta_wash_ca: float = 0.97
    # hypothesis switches (True = mechanism active)
    H1: bool = True
    H2: bool = True   # False -> alpha = 1 (etching happens but is not selective)
    H3: bool = True

    def with_hypotheses(self, h1: bool, h2: bool, h3: bool) -> "Params":
        return replace(self, H1=h1, H2=h2, H3=h3)


def _arrh(k0: float, Ea: float, T_K: float) -> float:
    return k0 * np.exp(-Ea / (R_GAS * T_K))


def temperature_K(t_min: float, recipe: Recipe, p: Params) -> float:
    """Furnace schedule: linear ramp then isothermal hold (cool-down neglected —
    rates are frozen within minutes of leaving the hold temperature)."""
    T_hold = recipe.temperature_C
    t_ramp = (T_hold - p.T0_C) / p.ramp_C_per_min
    T_C = p.T0_C + p.ramp_C_per_min * min(t_min, t_ramp)
    return T_C + 273.15


def rhs(t: float, y: np.ndarray, recipe: Recipe, p: Params) -> np.ndarray:
    T = temperature_K(t, recipe, p)
    d = np.zeros_like(y)
    g = lambda name: max(y[IDX[name]], 0.0)  # noqa: E731

    C_am, C_turb, C_gr = g("C_am"), g("C_turb"), g("C_gr")
    C_tot = C_am + C_turb + C_gr
    solids = C_tot + g("S") + g("VOL") + g("CaCO3") + g("CaO") + g("CaS") + g("Fe")

    # --- devolatilization ---------------------------------------------------
    r_dev = _arrh(p.k0_dev, p.Ea_dev, T) * g("VOL")
    d[IDX["VOL"]] -= r_dev
    d[IDX["VOL_out"]] += r_dev

    # --- calcination ----------------------------------------------------------
    r_cal = _arrh(p.k0_cal, p.Ea_cal, T) * g("CaCO3")
    d[IDX["CaCO3"]] -= r_cal
    d[IDX["CaO"]] += r_cal * (M_CaO / M_CaCO3)
    d[IDX["CO2_pool"]] += r_cal * (M_CO2 / M_CaCO3)

    # --- CO2 pool: escape vs Boudouard ---------------------------------------
    pool = g("CO2_pool")
    r_esc = p.k_esc * pool
    alpha = p.alpha_H2 if p.H2 else 1.0
    # per-phase reactivity weights (mass-based)
    w_am, w_turb, w_gr = alpha * C_am, np.sqrt(alpha) * C_turb, C_gr
    w_sum = w_am + w_turb + w_gr
    r_boud = _arrh(p.k0_boud, p.Ea_boud, T) * pool * (w_sum / C_tot if C_tot > 0 else 0.0)
    d[IDX["CO2_pool"]] -= r_esc + r_boud
    d[IDX["CO2_out"]] += r_esc
    # C + CO2 -> 2 CO : r_boud grams CO2 consume (M_C/M_CO2) grams C
    c_etch = r_boud * (M_C / M_CO2)
    if w_sum > 0:
        d[IDX["C_am"]] -= c_etch * (w_am / w_sum)
        d[IDX["C_turb"]] -= c_etch * (w_turb / w_sum)
        d[IDX["C_gr"]] -= c_etch * (w_gr / w_sum)
    d[IDX["CO_out"]] += r_boud + c_etch

    # --- graphitization (dissolution-reprecipitation at the Fe interface) ----
    fe_frac = g("Fe") / solids if solids > 0 else 0.0
    f_fe = fe_frac / (p.K_fe + fe_frac) if fe_frac > 0 else 0.0
    disp = 1.0
    if p.H3 and solids > 0:
        u = g("CaO") / solids
        disp += p.h3_gain * u / (u + p.h3_uhalf)
    poison = 1.0 / (1.0 + p.p_poison * (g("S") / g("Fe"))) if g("Fe") > 0 else 0.0
    k_g = _arrh(p.k0_graph, p.Ea_graph, T) * f_fe * disp * poison
    r_am = k_g * C_am
    r_tg = p.gamma_turb * k_g * C_turb
    d[IDX["C_am"]] -= r_am
    d[IDX["C_turb"]] += r_am - r_tg
    d[IDX["C_gr"]] += r_tg
    # ordering coordinate of the graphitic phase (drives peak position / Lc)
    d[IDX["Q"]] = p.q_gain * k_g * (1.0 - min(y[IDX["Q"]], 1.0))

    # --- sulfur ---------------------------------------------------------------
    r_sgas = _arrh(p.k0_sgas, p.Ea_sgas, T) * g("S")
    d[IDX["S"]] -= r_sgas
    d[IDX["S_out"]] += r_sgas
    if p.H1:
        r_trap = _arrh(p.k0_trap, p.Ea_trap, T) * g("S") * g("CaO")
        d[IDX["S"]] -= r_trap
        d[IDX["CaO"]] -= r_trap * (M_CaO / M_S)
        d[IDX["CaS"]] += r_trap * (M_CaS / M_S)
        d[IDX["O_out"]] += r_trap * (M_O / M_S)

    return d


def simulate(recipe: Recipe, p: Params, c_wt: float, s_wt: float,
             n_eval: int = 200) -> dict:
    """Integrate the pellet through ramp + hold. Returns the trajectory and the
    final state; downstream modules (massbalance, xrd_forward, tga) read from
    this dict rather than re-integrating."""
    y0 = initial_state(recipe, c_wt, s_wt)
    t_ramp = (recipe.temperature_C - p.T0_C) / p.ramp_C_per_min
    t_end = t_ramp + recipe.time_h * 60.0
    t_eval = np.linspace(0.0, t_end, n_eval)
    sol = solve_ivp(rhs, (0.0, t_end), y0, args=(recipe, p), method="LSODA",
                    t_eval=t_eval, rtol=1e-8, atol=1e-10)
    if not sol.success:
        raise RuntimeError(f"ODE integration failed: {sol.message}")
    yf = np.clip(sol.y[:, -1], 0.0, None)
    yf[IDX["Q"]] = min(sol.y[IDX["Q"], -1], 1.0)
    return {
        "recipe": recipe, "params": p, "c_wt": c_wt, "s_wt": s_wt,
        "t_min": sol.t, "traj": sol.y, "y0": y0, "y_final": yf,
        "T_K": np.array([temperature_K(t, recipe, p) for t in sol.t]),
    }


def phase_fractions(y: np.ndarray) -> dict:
    """Mass fractions of the three carbon phases (of surviving carbon)."""
    c = carbon_mass(y)
    if c <= 0:
        return {"amorphous": 0.0, "turbostratic": 0.0, "graphitic": 0.0}
    return {"amorphous": y[IDX["C_am"]] / c,
            "turbostratic": y[IDX["C_turb"]] / c,
            "graphitic": y[IDX["C_gr"]] / c}
