"""Temperature programs — the furnace/kiln thermal history the pellet actually sees.

Two reactor modes, matching the two pieces of equipment in this project:

- ``tube_furnace_program`` — the lab tube furnace. A real multi-segment program
  with **preheat holds** (e.g. 300/800/1200 C, 20 min each), a **process hold**
  at the peak, then **programmed cooling** (5 C/min to ~500 C) and **natural
  cooling** to room temperature. Modeled from the group's actual controller
  program (C01..T10). The preheat holds matter: calcination (CaCO3 -> CaO+CO2,
  onset ~700-850 C) and sulfur trapping begin during the 800 C hold, not only at
  the peak.

- ``rotary_kiln_program`` — the scale-up reactor. Continuous rotary kiln with a
  hard limit of ~1300 C and ~2 h, and crucially **no isothermal hold**: material
  enters at room temperature, is carried up to the peak, and is cooled essentially
  immediately (true residence time, not time-on-stream). Modeled as a triangular
  ramp-up / ramp-down over the residence time. Because there is no long hold, the
  integrated time-at-temperature is far smaller than the tube furnace's — the
  central scale-up challenge this simulation is meant to expose.

Rotary-kiln residence times for carbon/coke are short — commonly ~10-45 min, up
to ~30 min typical (Sunkara et al., *Powder Technol.* 2009; petroleum-coke
calcining practice) — which is why the 2 h kiln limit is generous but the missing
hold still bites. Calcined-coke practice runs 1150-1350 C in an oxygen-deficient
(not fully inert) atmosphere (industry calcining references) — see SOURCES.md.
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
                        heat_frac: float = 0.5,
                        T0_C: float = T_ROOM_C) -> TemperatureProgram:
    """Continuous rotary kiln: RT -> peak -> RT over the residence time, with NO
    isothermal hold ("true residence time", not time-on-stream). Triangular
    profile; ``heat_frac`` is the fraction of residence spent heating (0.5 =
    symmetric). This is the scale-up reactor — its missing hold is why the same
    peak temperature graphitizes far less than in the tube furnace.
    """
    residence_min = residence_h * 60.0
    up = max(heat_frac, 0.05) * residence_min
    down = residence_min - up
    return _segments_to_program(0.0, T0_C,
                                [(up, peak_C), (down, T0_C)],
                                f"kiln: peak {peak_C:.0f}C, residence {residence_h:.2g}h")


def program_for(reactor: str, peak_C: float, time_h: float, **kw) -> TemperatureProgram:
    """Dispatch on reactor type. ``time_h`` is the process hold (tube) or the
    total residence time (kiln)."""
    if reactor == "kiln":
        return rotary_kiln_program(peak_C, time_h, **kw)
    return tube_furnace_program(peak_C, time_h, **kw)
