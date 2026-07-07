"""Front B: phase masses -> a synthetic (002)-region XRD pattern.

This is what makes "what does (002) intensity mean" testable: render a
pattern from *known* phase fractions, then run it through the same engine
code (fit_netl / decompose / norm_002_area) used on the real DATA/*.xy scans.
If the recovered metrics track the known composition, the forward model (and
the engine's inversion of it) is trustworthy; if not, the closed loop finds it.

Physical picture (handoff §5, §6, §11):
  - graphitic phase   -> sharp pseudo-Voigt at d = 3.354 A (2theta ~ 26.5 deg)
  - turbostratic phase -> broader pseudo-Voigt at d = 3.440 A (2theta ~ 26.0 deg)
  - amorphous phase   -> very broad diffuse halo, no resolved peak
  - ``ordering_q`` (0..1, from sim.kinetics) sharpens the graphitic peak
    (Scherrer: width ~ 1/Lc) and pulls its center from the turbostratic
    position toward 3.354 A as the lattice locks in.

Per Ruland & Smarsly (handoff §6), amorphous and crystalline carbon do NOT
scatter equally per gram -- SCATTERING_POWER below assigns each phase its own
mass-normalized scattering power rather than assuming equal efficiency.
"""
from __future__ import annotations

import numpy as np

import sim  # noqa: F401
from xrd_analyzer import DEFAULT_WAVELENGTH, D_GRAPHITE, D_TURBOSTRATIC, pseudo_voigt

TWO_THETA_RANGE = (5.0, 90.0)
STEP = 0.01  # fine enough to resolve narrow, well-ordered graphitic peaks (FWHM can be ~0.1 deg)

# mass-normalized scattering power per phase, graphitic = 1.0 reference.
# Amorphous carbon scatters coherently far less efficiently per gram (most of
# its signal is diffuse/incoherent background) -- this is the Ruland & Smarsly
# caveat made explicit and adjustable.
SCATTERING_POWER = {"amorphous": 0.35, "turbostratic": 0.85, "graphitic": 1.0}

_D_GR_2THETA = 2 * np.degrees(np.arcsin(DEFAULT_WAVELENGTH / (2 * D_GRAPHITE)))
_D_TURB_2THETA = 2 * np.degrees(np.arcsin(DEFAULT_WAVELENGTH / (2 * D_TURBOSTRATIC)))


def _lc_to_fwhm_deg(lc_angstrom: float, two_theta_deg: float, K: float = 0.9) -> float:
    """Invert Scherrer: Lc = K*lambda/(beta*cos(theta)) -> beta (deg 2theta)."""
    theta = np.radians(two_theta_deg / 2.0)
    beta_rad = K * DEFAULT_WAVELENGTH / (max(lc_angstrom, 1.0) * np.cos(theta))
    return float(np.degrees(beta_rad))


def render_pattern(*, amorphous: float, turbostratic: float, graphitic: float,
                   ordering_q: float = 1.0, scale: float = 300.0,
                   packing_jitter: float = 0.08, noise: float = 0.01,
                   seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Build a synthetic 5-90 deg pattern from carbon phase MASS fractions
    (amorphous+turbostratic+graphitic should sum to ~1). ``scale`` and
    ``packing_jitter`` model the auto-scaling / packing-density variation the
    handoff warns raw intensity is NOT immune to (§6) -- norm_002_area must
    divide these back out for the closed loop to recover the known fractions.
    """
    total = amorphous + turbostratic + graphitic
    if total <= 0:
        raise ValueError("phase fractions must sum to a positive total")
    amorphous, turbostratic, graphitic = (v / total for v in (amorphous, turbostratic, graphitic))

    rng = np.random.default_rng(seed)
    x = np.arange(TWO_THETA_RANGE[0], TWO_THETA_RANGE[1], STEP)

    # ordering_q sharpens Lc (crystallite height) and pulls the graphitic
    # center from the turbostratic position toward the ideal 3.354 A position.
    lc = 30.0 + 550.0 * np.clip(ordering_q, 0.0, 1.0)          # Angstrom
    xc_gr = _D_TURB_2THETA + (_D_GR_2THETA - _D_TURB_2THETA) * np.clip(ordering_q, 0.0, 1.0)
    w_gr = max(_lc_to_fwhm_deg(lc, xc_gr), 0.06)

    amp_scale = scale * (1.0 + packing_jitter * rng.standard_normal())
    y = np.full_like(x, 0.05)  # small detector floor / air scatter

    # amorphous halo: broad, centered under the (002) region -- its own
    # scattering power sets how much signal per gram it contributes to the
    # total-scatter denominator (Ruland & Smarsly: not necessarily much less
    # than crystalline, since the halo is broad but not weak).
    y += amp_scale * amorphous * SCATTERING_POWER["amorphous"] * \
        pseudo_voigt(x, 1.0, 23.5, 8.0, 0.15)
    # turbostratic broad (002)
    y += amp_scale * turbostratic * SCATTERING_POWER["turbostratic"] * \
        pseudo_voigt(x, 1.0, _D_TURB_2THETA, 0.9, 1.0)
    # graphitic sharp (002), position/width tied to ordering_q
    y += amp_scale * graphitic * SCATTERING_POWER["graphitic"] * \
        pseudo_voigt(x, 1.0, xc_gr, w_gr, 0.55)
    # higher-angle graphite lines (small relative weight -- they exist in real
    # patterns but should not dominate the 10-90 normalizer)
    for A, xc, w in ((0.02, 42.4, 0.4), (0.025, 44.6, 0.4), (0.015, 54.7, 0.5)):
        y += amp_scale * graphitic * SCATTERING_POWER["graphitic"] * pseudo_voigt(x, A, xc, w, 0.5)

    # Detector noise is scaled off amp_scale (a fixed, composition-independent
    # reference), NOT y.max(): a narrow, well-ordered graphitic peak can be
    # very tall, and scaling noise by that height (then clipping negatives at
    # zero) injects a large one-sided bias into the broad baseline that grows
    # with ordering/graphitic content -- exactly the kind of composition-
    # dependent artifact norm_002_area is supposed to be immune to.
    y = y + noise * amp_scale * rng.standard_normal(x.size)
    return x, np.clip(y, 0.0, None)


def render_from_massbalance(mb: dict, **kwargs) -> tuple[np.ndarray, np.ndarray]:
    """Convenience: render straight from a sim.massbalance.run_mass_balance() result."""
    f = mb["carbon"]["phase_fractions"]
    q = mb["carbon"]["ordering_q"]
    return render_pattern(amorphous=f["amorphous"], turbostratic=f["turbostratic"],
                          graphitic=f["graphitic"], ordering_q=q, **kwargs)
