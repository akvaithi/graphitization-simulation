"""Pellet state: every gram of C / S / Fe / Ca, solid or gone as gas.

The state is a flat vector of masses (grams) so the kinetics can hand it to
scipy's ODE solvers directly. Mass is conserved *by construction*: every
reaction moves grams between named slots (solids <-> gas ledger), and
``conservation_error`` measures the numerical drift, which tests pin to ~1e-9.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# molar masses (g/mol) — must match engine/research/yield_calc.py
M_C, M_Fe, M_CaCO3, M_CaO, M_S, M_CaS = 12.011, 55.845, 100.086, 56.077, 32.06, 72.138
M_CO2, M_CO = 44.009, 28.01

# state-vector slots. Solids first, then the in-pellet CO2 pool, then the gas
# ledger (cumulative mass that has left the pellet).
FIELDS = (
    # -- solids (in the pellet) --
    "C_am",      # amorphous carbon
    "C_turb",    # turbostratic carbon
    "C_gr",      # graphitic carbon
    "S",         # organic sulfur still bound in the coke
    "VOL",       # volatiles + moisture (+ ash lumped, see feedstock)
    "CaCO3",
    "CaO",
    "CaS",
    "Fe",        # catalyst (not consumed; solid throughout)
    "Q",         # ordering coordinate of the graphitic phase, 0..1 (NOT a mass)
    # -- transient --
    "CO2_pool",  # CO2 released by calcination, still inside the pellet
    # -- gas ledger (cumulative, left the pellet) --
    "CO2_out",   # calcination CO2 that escaped unreacted
    "CO_out",    # Boudouard product CO
    "S_out",     # sulfur left as gaseous species
    "VOL_out",   # devolatilized mass
    "O_out",     # oxygen released by CaO + S -> CaS + 1/2 O2 (keeps the ledger closed;
                 # yield_calc books the same reaction without conserving the O)
)
IDX = {name: i for i, name in enumerate(FIELDS)}
_MASS_FIELDS = tuple(f for f in FIELDS if f != "Q")


@dataclass
class Recipe:
    """One experimental run. Masses in grams, temperature in deg C, time in h."""
    pc_mass: float
    fe_mass: float
    caco3_mass: float
    temperature_C: float
    time_h: float
    grade: str = "GPC"

    @property
    def pellet_mass(self) -> float:
        return self.pc_mass + self.fe_mass + self.caco3_mass


def initial_state(recipe: Recipe, c_wt: float, s_wt: float) -> np.ndarray:
    """Pellet at room temperature: all coke carbon starts amorphous (the
    handoff's 'largely amorphous/turbostratic' feed is modeled as amorphous;
    any native turbostratic content is absorbed into the fitted kinetics)."""
    y = np.zeros(len(FIELDS))
    y[IDX["C_am"]] = recipe.pc_mass * c_wt
    y[IDX["S"]] = recipe.pc_mass * s_wt
    y[IDX["VOL"]] = recipe.pc_mass * max(0.0, 1.0 - c_wt - s_wt)
    y[IDX["CaCO3"]] = recipe.caco3_mass
    y[IDX["Fe"]] = recipe.fe_mass
    return y


def solid_mass(y: np.ndarray) -> float:
    """Mass sitting in the boat right now (pellet + any in-pellet CO2 excluded:
    the pool is gas-phase and leaves on weighing)."""
    return float(sum(y[IDX[f]] for f in
                     ("C_am", "C_turb", "C_gr", "S", "VOL", "CaCO3", "CaO", "CaS", "Fe")))


def carbon_mass(y: np.ndarray) -> float:
    return float(y[IDX["C_am"]] + y[IDX["C_turb"]] + y[IDX["C_gr"]])


def conservation_error(y: np.ndarray, y0: np.ndarray) -> float:
    """|total mass now - total mass at t=0|, counting the gas ledger."""
    tot = lambda v: sum(v[IDX[f]] for f in _MASS_FIELDS)  # noqa: E731
    return abs(float(tot(y) - tot(y0)))
