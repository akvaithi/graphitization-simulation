"""Temperature programs — the furnace/kiln thermal history the pellet actually sees.

Two reactor modes, matching the two pieces of equipment in this project:

- ``tube_furnace_program`` — the lab tube furnace. A real multi-segment program
  with **preheat holds** (e.g. 300/800/1200 C, 20 min each), a **process hold**
  at the peak, then **programmed cooling** (5 C/min to ~500 C) and **natural
  cooling** to room temperature. Modeled from the group's actual controller
  program (C01..T10). The preheat holds matter: calcination (CaCO3 -> CaO+CO2,
  onset ~700-850 C) and sulfur trapping begin during the 800 C hold, not only at
  the peak.

- ``rotary_kiln_program`` — the scale-up reactor. A continuous rotary kiln
  DOES create an isothermal hold: material is carried through a heated entry
  zone, held at peak while it traverses the hot zone, then cooled through an exit
  zone (Kintek kiln-zone refs; SOURCES.md sec.5). Modeled as fast entry ramp ->
  isothermal hold (the bulk of the residence time) -> fast exit cool, with hard
  limits of ~1300 C and ~2 h. How fast the *material itself* heats and cools
  within this gas profile is a separate question answered by its thermal time
  constant (sim.kinetics): carbon's finite conductivity (raw coke k ~ 2-4 W/m.K)
  means a thin cross-section tracks the gas in under a minute while a thick one
  lags — which is why the extruder scale-up route (fixed small cross-section)
  matters. Earlier versions modeled the kiln as a hold-free triangle; that was
  wrong (there IS a hold), corrected per lab feedback.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

T_ROOM_C = 25.0
DEFAULT_RAMP_C_PER_MIN = 5.0                 # group's programmed ramp/cool rate
DEFAULT_PREHEATS = ((300.0, 20.0), (800.0, 20.0), (1200.0, 20.0))  # (T_C, hold_min)
DEFAULT_COOL_TO_C = 500.0                     # programmed cooling floor, then natural


@dataclass
class TemperatureProgram:
    """Piecewise-linear T(t): breakpoints in minutes / deg C. Beyond the last
    breakpoint the temperature holds at the final value (rates are frozen)."""
    t_min: np.ndarray            # breakpoint times (min), ascending, starts at 0
    T_C: np.ndarray              # temperature at each breakpoint (deg C)
    label: str = ""

    @property
    def total_min(self) -> float:
        return float(self.t_min[-1])

    def T_C_at(self, t: float) -> float:
        return float(np.interp(t, self.t_min, self.T_C,
                               left=self.T_C[0], right=self.T_C[-1]))

    def T_K_at(self, t: float) -> float:
        return self.T_C_at(t) + 273.15


def _segments_to_program(t0: float, T0: float, segments: list[tuple[float, float]],
                         label: str) -> TemperatureProgram:
    """segments = [(duration_min, T_end_C), ...] appended after (t0, T0)."""
    ts, Ts = [t0], [T0]
    for dur, T_end in segments:
        ts.append(ts[-1] + dur)
        Ts.append(T_end)
    return TemperatureProgram(np.asarray(ts, float), np.asarray(Ts, float), label)


def tube_furnace_program(peak_C: float, hold_h: float, *,
                         ramp_C_per_min: float = DEFAULT_RAMP_C_PER_MIN,
                         preheats: tuple = DEFAULT_PREHEATS,
                         first_ramp_min: float = 40.0,
                         cool_to_C: float = DEFAULT_COOL_TO_C,
                         natural_cool_min: float = 90.0,
                         T0_C: float = T_ROOM_C) -> TemperatureProgram:
    """Multi-segment lab program: RT -> [preheat holds below peak] -> peak hold ->
    programmed cool -> natural cool. Reproduces the group's C01..T10 program; the
    example (peak 1400 C, hold 2 h) yields the 300/800/1200 preheats + 5 C/min
    ramps + 1400->500 programmed cool given in the handoff.
    """
    segs: list[tuple[float, float]] = []
    prev_T = T0_C
    # first ramp is slower (accounts for cold start); rest at ramp_C_per_min
    active_preheats = [(T, h) for (T, h) in preheats if T < peak_C - 1e-6]
    first = True
    for T_ph, hold_min in active_preheats:
        dur = first_ramp_min if first else abs(T_ph - prev_T) / ramp_C_per_min
        segs.append((dur, T_ph))          # ramp up to preheat
        segs.append((hold_min, T_ph))     # preheat hold
        prev_T = T_ph
        first = False
    # ramp to the process peak
    dur = first_ramp_min if first else abs(peak_C - prev_T) / ramp_C_per_min
    segs.append((dur, peak_C))
    # process hold
    segs.append((hold_h * 60.0, peak_C))
    # programmed cooling to cool_to_C, then natural cooling to room T
    segs.append((abs(peak_C - cool_to_C) / ramp_C_per_min, cool_to_C))
    segs.append((natural_cool_min, T0_C))
    return _segments_to_program(0.0, T0_C, segs,
                                f"tube: peak {peak_C:.0f}C, hold {hold_h:.2g}h")


def rotary_kiln_program(peak_C: float, residence_h: float, *,
                        entry_min: float = 12.0, exit_min: float = 12.0,
                        T0_C: float = T_ROOM_C) -> TemperatureProgram:
    """Continuous rotary kiln gas/wall profile: a short heated **entry** ramp ->
    an **isothermal hold** at peak (the hot-zone traverse) -> a short **exit**
    cool. The material is carried through the kiln's temperature zones, so it
    reaches peak, is held for most of the residence time, then cooled (the hold
    exists; Kintek kiln-zone refs, SOURCES.md sec.5). How fast the *material*
    itself heats/cools within this gas profile is set separately by its thermal
    time constant (sim.kinetics thermal lag): carbon's finite conductivity means
    a thick cross-section lags the gas while a thin one tracks it closely.

    ``entry_min`` / ``exit_min`` are the heated/cooled zone traverse times; the
    isothermal hold fills the rest of the residence time.
    """
    residence_min = residence_h * 60.0
    hold = max(0.0, residence_min - entry_min - exit_min)
    return _segments_to_program(0.0, T0_C,
                                [(min(entry_min, residence_min), peak_C),
                                 (hold, peak_C),
                                 (exit_min if hold > 0 else 0.0, T0_C)],
                                f"kiln: peak {peak_C:.0f}C, residence {residence_h:.2g}h")


def program_for(reactor: str, peak_C: float, time_h: float, **kw) -> TemperatureProgram:
    """Dispatch on reactor type. ``time_h`` is the process hold (tube) or the
    total residence time (kiln)."""
    if reactor == "kiln":
        return rotary_kiln_program(peak_C, time_h, **kw)
    return tube_furnace_program(peak_C, time_h, **kw)
