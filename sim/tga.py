"""Front C: predicted TGA / DTG oxidation curves (no TGA data exists yet --
this front is purely predictive, per the handoff, to be validated later).

Model: each carbon phase burns in air with its own Arrhenius reactivity window
(handoff §8, item 4): amorphous ~400-550 C, turbostratic intermediate,
graphitic ~600-800 C. A first-order burn-off per phase, integrated over a
constant-heating-rate ramp, gives a mass-loss curve whose derivative (DTG) is
the standard TGA deconvolution the biochar/coal community uses to separate
disordered from ordered carbon by an independent, diffraction-free route.
"""
from __future__ import annotations

import numpy as np

R_GAS = 8.314  # J/mol/K

# (k0 [1/min], Ea [J/mol]) chosen so peak burn temperature at 10 C/min lands
# in each phase's literature window (handoff section 8, item 4).
BURN_KINETICS = {
    "amorphous": (1.0e7, 120e3),      # peak ~450-500 C
    "turbostratic": (1.0e8, 155e3),   # peak ~550-600 C
    "graphitic": (1.0e9, 195e3),      # peak ~650-750 C
}


def predict_dtg(*, amorphous: float, turbostratic: float, graphitic: float,
                heating_rate_C_per_min: float = 10.0,
                T_start_C: float = 200.0, T_end_C: float = 900.0,
                n: int = 700) -> dict:
    """Return {"T_C", "mass_frac_remaining", "dtg"} for a linear-ramp TGA burn
    of a carbon sample with the given phase mass fractions (need not be
    pre-normalized -- they are normalized here)."""
    total = amorphous + turbostratic + graphitic
    if total <= 0:
        raise ValueError("phase fractions must sum to a positive total")
    fracs = {"amorphous": amorphous / total, "turbostratic": turbostratic / total,
            "graphitic": graphitic / total}

    T_C = np.linspace(T_start_C, T_end_C, n)
    T_K = T_C + 273.15
    dt_min = (T_C[1] - T_C[0]) / heating_rate_C_per_min

    remaining = {phase: 1.0 for phase in fracs}
    mass_frac_remaining = np.zeros(n)
    dtg = np.zeros(n)
    mass_frac_remaining[0] = 1.0
    for i in range(1, n):
        total_rate = 0.0
        for phase, (k0, Ea) in BURN_KINETICS.items():
            k = k0 * np.exp(-Ea / (R_GAS * T_K[i]))
            d_remaining = k * remaining[phase] * dt_min
            d_remaining = min(d_remaining, remaining[phase])
            remaining[phase] -= d_remaining
            total_rate += fracs[phase] * d_remaining / dt_min
        mass_frac_remaining[i] = sum(fracs[p] * remaining[p] for p in fracs)
        dtg[i] = total_rate  # mass fraction lost per minute (positive = burning)

    return {"T_C": T_C, "mass_frac_remaining": mass_frac_remaining, "dtg": dtg,
           "heating_rate_C_per_min": heating_rate_C_per_min, "phase_fractions": fracs}


def predict_from_massbalance(mb: dict, **kwargs) -> dict:
    f = mb["carbon"]["phase_fractions"]
    return predict_dtg(amorphous=f["amorphous"], turbostratic=f["turbostratic"],
                       graphitic=f["graphitic"], **kwargs)


def burn_rate_calibration_curve(ordering_q_values=None) -> list[dict]:
    """The handoff's 'burn-rate calibration curve' idea (section 8, item 4):
    DTG peak temperature as a function of ordering state. Approximates the
    ordering-state -> phase-fraction map with a simple two-phase (amorphous ->
    graphitic) conversion at the given q, matching sim.kinetics' Q coordinate."""
    ordering_q_values = ordering_q_values if ordering_q_values is not None else np.linspace(0, 1, 11)
    rows = []
    for q in ordering_q_values:
        curve = predict_dtg(amorphous=1 - q, turbostratic=0.0, graphitic=q)
        T_peak = float(curve["T_C"][int(np.argmax(curve["dtg"]))])
        rows.append({"ordering_q": float(q), "dtg_peak_T_C": T_peak})
    return rows
