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

The thermal history comes from sim.schedule (multi-segment tube-furnace program
with preheat holds, or the hold-free rotary-kiln triangle), and an O2-combustion
term + a binding-method contact factor drive the scale-up front. Default
parameters are anchored to the published behaviour (Fe plateau ~50 wt%, sulfur
threshold, S removal) and refined against the ground-truth dataset by
sim.inference. Sources for each mechanism are in SOURCES.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np
from scipy.integrate import solve_ivp

from sim import schedule
from sim.state import (FIELDS, IDX, M_C, M_CaCO3, M_CaO, M_CaS, M_CO, M_CO2,
                       M_S, Recipe, carbon_mass, initial_state)

R_GAS = 8.314  # J/mol/K
M_O2 = 31.998
M_O = M_CaO + M_S - M_CaS  # 15.999 per mol trapped: the O2 leaving in H1

# --- scale-up part 1: Fe-carbon interfacial contact by binding method ---------
# Multiplies the graphitization rate. The catalytic step is a dissolution-
# reprecipitation at the Fe-carbon interface (Banavath 2026; Oya carbide route
# 1983), so how intimately Fe touches the carbon is a direct rate lever. Values
# are hypothesis-level (no scale-up data yet) and adjustable:
#   pellet           7-ton pressed, intimate contact -- the published baseline.
#   wet_impregnation Fe deposited from solution -> finest, most homogeneous
#                    dispersion (Frankenstein 2023; biochar Fe-impregnation 2021).
#   extrusion        shaped with mixing but far lower pressure than pelletizing
#                    (FEECO; Zhang solvent-free anode 2022).
#   dry_mix          loose powder, pressureless -- poorest contact.
BINDING_CONTACT = {"pellet": 1.0, "wet_impregnation": 1.6, "extrusion": 0.9, "dry_mix": 0.45}


def contact_factor(recipe: Recipe, p: "Params") -> float:
    """Fe-carbon contact multiplier from the binding method (throughput/charge
    mass is NOT penalized here -- size enters through the thermal lag below,
    because scaling up via extrusion keeps the cross-section, and thus heat
    transfer, unchanged)."""
    return BINDING_CONTACT.get(recipe.binding, 1.0)


# --- scale-up part 2: heat transfer set by the cross-sectional dimension -------
# Carbon's thermal conductivity is finite (raw coke ~2-4 W/m.K, rising with
# graphitization; Springer pet-coke thermo-physical 2016), so a formed body heats
# and cools on a thermal time constant set by its *cross-section*, not its total
# mass. A lumped-capacitance material temperature lags the gas:
#     dT_mat/dt = (T_gas - T_mat) / tau,   tau = tau_lin*L + tau_quad*L^2  (L in mm)
# The linear term is surface convection (rho*cp*(V/A)/h) and the quadratic term is
# internal conduction (L^2/alpha); both grow with the cross-section. This is why a
# thin lab puck (L~2.5 mm, tau < 1 min) tracks the furnace but a thick bed lags,
# and why an EXTRUDER -- constant small cross-section, length scales with
# throughput -- carries no thermal penalty at scale. (SOURCES.md sec.5-6.)
_LAB_PUCK_CHAR_MM = 2.5   # V/A of the pressed ~13 mm-die 2 g-PC lab pellet
_REF_MASS_G = 2.0


def char_dim_mm(recipe: Recipe) -> float:
    """Characteristic cross-sectional dimension (mm) that sets the thermal lag."""
    if recipe.char_dim_mm is not None:
        return float(recipe.char_dim_mm)
    if recipe.geometry == "extrudate":
        return _LAB_PUCK_CHAR_MM        # fixed die cross-section; length scales instead
    # puck: cross-section grows isometrically with the charge (L ~ mass^(1/3))
    return _LAB_PUCK_CHAR_MM * (max(recipe.pc_mass, 1e-6) / _REF_MASS_G) ** (1.0 / 3.0)


def thermal_tau_min(L_mm: float, p: "Params") -> float:
    """Lumped-capacitance thermal time constant (min) for cross-section L (mm)."""
    return p.tau_lin * L_mm + p.tau_quad * L_mm * L_mm


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
    # default: with high-sulfur GPC (~6.5 wt% S) the CaO from a sub-1:1 CaCO3 dose
    # is substoichiometric to sulfur, so free S survives and kills ordering — the
    # observed threshold (Sharma sulfur-poisoning; Majumder CaO trapping).
    p_poison: float = 800.0
    # oxygen combustion (C + O2 -> CO2): default o2_frac=0 -> fully inert argon.
    # Raise o2_frac to explore an imperfectly-sealed / non-inert atmosphere (scale-
    # up). Amorphous carbon oxidizes preferentially (o2_alpha), like Boudouard.
    o2_frac: float = 0.0         # mole fraction O2 in the sweep gas (0 = pure Ar)
    k0_o2: float = 1.5e5
    Ea_o2: float = 165e3
    o2_alpha: float = 6.0        # amorphous/graphitic O2-burn selectivity
    # scale-up thermal lag: tau(min) = tau_lin*L + tau_quad*L^2, L = cross-section (mm)
    # (surface convection + internal conduction; SOURCES.md sec.5-6)
    tau_lin: float = 0.22
    tau_quad: float = 0.010
    # furnace schedule (see sim.schedule; ramp/preheats live there)
    T0_C: float = schedule.T_ROOM_C
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


def rhs(t: float, y: np.ndarray, program: "schedule.TemperatureProgram",
        p: Params, contact: float = 1.0, tau: float = 0.01) -> np.ndarray:
    d = np.zeros_like(y)
    # material temperature lags the gas by the lumped-capacitance time constant;
    # the chemistry sees the MATERIAL temperature, not the gas program directly.
    T_gas_C = program.T_C_at(t)
    T_mat_C = y[IDX["T_mat"]]
    d[IDX["T_mat"]] = (T_gas_C - T_mat_C) / max(tau, 1e-6)
    T = T_mat_C + 273.15
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
    # H3: calcium boosts the graphitization rate. Calcium (a) reduces Fe particle
    # size and prevents sintering (CaO confinement effect), (b) WETS the Fe surface
    # forming a CaO-FexOy layer that spreads the catalyst, and (c) is itself a
    # graphitization catalyst via a CaC2 carbide route above ~1200 C -- together a
    # dispersion + co-catalysis enhancement (Nature Sci.Rep. 2023/2022; TOF-SIMS
    # wetting 2022; SOURCES.md sec.H3). Saturating in the CaO fraction (an optimum
    # loading exists; excess Ca over-graphitizes). This is the load-bearing CaCO3
    # effect; H2 (Boudouard) is negligible in the fit.
    disp = 1.0
    if p.H3 and solids > 0:
        u = g("CaO") / solids
        disp += p.h3_gain * u / (u + p.h3_uhalf)
    poison = 1.0 / (1.0 + p.p_poison * (g("S") / g("Fe"))) if g("Fe") > 0 else 0.0
    k_g = _arrh(p.k0_graph, p.Ea_graph, T) * f_fe * disp * poison * contact
    r_am = k_g * C_am
    r_tg = p.gamma_turb * k_g * C_turb
    d[IDX["C_am"]] -= r_am
    d[IDX["C_turb"]] += r_am - r_tg
    d[IDX["C_gr"]] += r_tg
    # ordering coordinate of the graphitic phase (drives peak position / Lc)
    d[IDX["Q"]] = p.q_gain * k_g * (1.0 - min(y[IDX["Q"]], 1.0))

    # --- oxygen combustion (only if the atmosphere is not fully inert) --------
    # C + O2 -> CO2. O2 is externally supplied (flowing gas), so first-order in
    # the reactive carbon and proportional to the O2 fraction; amorphous carbon
    # burns preferentially (o2_alpha), the same reactivity ordering TGA burn-off
    # exploits (Lu 2001). Only the carbon mass is booked (the O2 is external), so
    # the closed-ledger mass balance is preserved.
    if p.o2_frac > 0.0 and C_tot > 0.0:
        wo_am, wo_turb, wo_gr = p.o2_alpha * C_am, np.sqrt(p.o2_alpha) * C_turb, C_gr
        wo_sum = wo_am + wo_turb + wo_gr
        r_burn = _arrh(p.k0_o2, p.Ea_o2, T) * p.o2_frac * wo_sum
        if wo_sum > 0:
            d[IDX["C_am"]] -= r_burn * (wo_am / wo_sum)
            d[IDX["C_turb"]] -= r_burn * (wo_turb / wo_sum)
            d[IDX["C_gr"]] -= r_burn * (wo_gr / wo_sum)
        d[IDX["C_burn_out"]] += r_burn

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
             n_eval: int = 240) -> dict:
    """Integrate the pellet through the full reactor program (sim.schedule) —
    ramp, preheat holds, process hold, and cooling for the tube furnace, or the
    hold-free ramp/cool triangle for the rotary kiln. Returns the trajectory and
    the final state; downstream modules read from this dict rather than
    re-integrating."""
    prog = schedule.program_for(recipe.reactor, recipe.temperature_C, recipe.time_h)
    contact = contact_factor(recipe, p)
    L = char_dim_mm(recipe)
    tau = thermal_tau_min(L, p)
    y0 = initial_state(recipe, c_wt, s_wt)
    t_end = prog.total_min
    t_eval = np.linspace(0.0, t_end, n_eval)
    sol = solve_ivp(rhs, (0.0, t_end), y0, args=(prog, p, contact, tau), method="LSODA",
                    t_eval=t_eval, rtol=1e-8, atol=1e-10, max_step=5.0)
    if not sol.success:
        raise RuntimeError(f"ODE integration failed: {sol.message}")
    yf = np.clip(sol.y[:, -1], 0.0, None)
    yf[IDX["Q"]] = min(sol.y[IDX["Q"], -1], 1.0)
    return {
        "recipe": recipe, "params": p, "c_wt": c_wt, "s_wt": s_wt,
        "program": prog, "contact": contact, "char_dim_mm": L, "thermal_tau_min": tau,
        "t_min": sol.t, "traj": sol.y, "y0": y0, "y_final": yf,
        "T_gas_C": np.array([prog.T_C_at(t) for t in sol.t]),
        "T_mat_C": sol.y[IDX["T_mat"]],
    }


def phase_fractions(y: np.ndarray) -> dict:
    """Mass fractions of the three carbon phases (of surviving carbon)."""
    c = carbon_mass(y)
    if c <= 0:
        return {"amorphous": 0.0, "turbostratic": 0.0, "graphitic": 0.0}
    return {"amorphous": y[IDX["C_am"]] / c,
            "turbostratic": y[IDX["C_turb"]] / c,
            "graphitic": y[IDX["C_gr"]] / c}
