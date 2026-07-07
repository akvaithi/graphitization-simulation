# CLAUDE.md — working notes for this repo

Orientation and ground truth for anyone (human or agent) working on the
catalytic-graphitization simulation. Read this before changing the model or the
data pipeline.

## What this project is

A simulation of **Fe-catalyzed, CaCO₃-assisted graphitization of green
petroleum coke (GPC)** into battery-grade graphite at ≤1300 °C. It reconciles a
mechanistic model against 17 real XRD scans + 6 weighed mass-balance rows, and
addresses four fronts: (A) mass balance, (B) XRD forward-model/calibration,
(C) predicted TGA/DTG, (D) CaCO₃ mechanism discrimination (H1/H2/H3). The full
scientific brief is `SIMULATION_HANDOFF.md` (confidential, gitignored).

## Layout & how to run

```
engine/      ported analyzer (github.com/akvaithi/xrd-graphitization-analyzer):
             DG% engine, crystallinity index, calibration, yield chemistry.
             Flat imports — `import xrd_analyzer`, `from _shared import ...`.
sim/         the simulation (state, kinetics ODE, mass balance, xrd forward,
             calibration, tga, hypotheses, inference, __main__ CLI).
analysis/    ground_truth.py — runs the engine on all real scans + joins masses.
dashboard/   build.py + template.html -> a self-contained interactive HTML page.
tests/       pytest suite (engine + research + sim).
outputs/     generated artifacts (gitignored — derived from confidential DATA/).
```

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests/ -q          # 33 pass, 6 skip (no gold/Swift data)
.venv/bin/python -m sim ground-truth          # engine metrics for every DATA/*.xy
.venv/bin/python -m sim fit                    # re-fit kinetics -> outputs/fitted_params.json
.venv/bin/python -m sim sweep                  # fitted model across the recipe grid
.venv/bin/python -m sim ablate --caco3 0.5     # H1/H2/H3 ablation for one recipe
.venv/bin/python dashboard/build.py            # regenerate the dashboard HTML
```

Import bootstrap: the engine uses **flat imports**, so `conftest.py` (tests),
`sim/__init__.py` (sim), and `analysis/ground_truth.py` each put `engine/` and
`engine/research/` on `sys.path`. Don't convert the engine to package imports —
it must stay numerically identical to the upstream analyzer + its Swift parity.

## The physical model — assumptions to know before trusting a number

### Furnace schedule (`sim/kinetics.py: temperature_K`, `simulate`)
- **A ramp IS modeled.** The pellet heats from `T0_C = 25 °C` at
  `ramp_C_per_min = 10 °C/min` up to the recipe setpoint, **then** holds
  isothermally. The dwell clock (`time_h`) starts *after* the ramp finishes, so
  a 1200 °C / 5 h run integrates ~117 min of ramp + 300 min of hold.
- **Simplifications, on purpose:** (1) the ramp is a single linear rate, not the
  tube furnace's actual multi-segment controller profile; (2) **cool-down is not
  modeled** — rates are effectively frozen at the end of the hold (ordering does
  not un-happen on cooling, and it's kinetically frozen within minutes of leaving
  temperature, so this is a safe omission for the final state, though it means the
  model can't speak to quench-rate effects); (3) no thermal-gradient / pellet-core
  vs surface distinction — the pellet is treated as isothermal at each instant.
- To fit a real controller profile, replace `temperature_K` with a piecewise
  schedule; nothing else in `rhs` assumes linearity.

### Atmosphere (inert / argon) — **implicit, by omission of O₂**
- The furnace runs under argon. In the model this is encoded as **the absence of
  any combustion term**: in `rhs`, carbon can only leave the solid via the
  **Boudouard reaction** (`C + CO₂ → 2 CO`) and volatiles via devolatilization.
  There is **no O₂ / no burning** anywhere in the furnace kinetics. If you ever
  model an air leak or an oxidizing sweep, add an O₂-driven `C + O₂ → CO₂` term.
- The one place oxidation appears is **`sim/tga.py` (Front C)** — but that is a
  *separate, predicted* TGA measurement (burning the washed product in air to
  split amorphous vs graphitic by oxidation temperature), NOT the furnace step.
- Gas leaves the pellet through a transient in-pellet **CO₂ pool** that either
  reacts (Boudouard) or escapes with the sweep gas (`k_esc`), so Boudouard
  *efficiency* is emergent, not assumed. Argon flow rate is not a parameter;
  it is subsumed into `k_esc`.

### Feedstock composition — GPC, sulfur stoichiometry
- All runs use **Green Petroleum Coke (GPC)**, measured **~7 wt% S** (very high —
  this is fuel/green-grade, not low-sulfur needle coke).
- `DEFAULT_COMPOSITION["GPC"]` in `engine/research/yield_calc.py` is set to
  **(0.88 C, 0.065 S)**. We use 6.5 wt% (not 7) deliberately: the group
  calculated **0.4063 g CaCO₃ to be the 1:1 molar match to the sulfur in a 2 g PC
  charge**, and 0.4063 g CaCO₃ traps exactly 6.5 wt% S. Using 6.5% makes the
  model's H1 sulfur-trapping threshold land on the experimental 1:1 point (the
  0.4063 g runs), which is the physically meaningful anchor. The carbon fraction
  (0.88) is a placeholder — replace with measured fixed carbon when available.
- **Why this matters:** the sulfur load *sets the H1 threshold*. Doubling it from
  the old 4.5% default moved the threshold from ~0.28 g to ~0.41 g CaCO₃.

### Reaction network (`sim/kinetics.py: rhs`)
Every process is Arrhenius `k(T) = A·exp(−Ea/RT)` over the schedule above:
devolatilization → calcination (CaCO₃→CaO+CO₂) → Boudouard etch (H2 selectivity
`alpha_H2`, =1 reproduces the spreadsheet's blind debit) → Fe-catalyzed
graphitization (Langmuir `f(w_Fe)` saturation → ~50 wt% Fe plateau; ordering
coordinate `Q` drives peak position/Lc) → sulfur (thermal desorption ∥ H1
trapping CaO+S→CaS) → algebraic acid wash. **Mass is conserved by construction**
(tests pin drift < 1e-6 g); the state vector is grams in named slots + a gas
ledger.

## Confirmed vs. open science (as of this dataset)

- **H1 (sulfur trapping) is confirmed.** Runs **without CaCO₃ do not graphitize** —
  the 7 wt% sulfur in GPC poisons the Fe catalyst at these low temperatures, and
  CaO from CaCO₃ is what neutralizes it. The **sharp threshold at the 1:1 S:CaCO₃
  point** (the 0.2031 g run fails: DG −18.5%, crystallinity 0.25; the 0.4063 g
  run works) is the stoichiometric fingerprint of a trapping sink. The fitted
  `p_poison` and `k0_trap` both climb to reflect this.
- **H2 (Boudouard etching) and H3 (dispersion) are NOT identified.** In the fit,
  `alpha_H2` and `h3_gain` rail to their bounds — the classic sign the XRD-only
  data doesn't constrain them (all three hypotheses push XRD ordering the same
  direction). Discriminating them needs observables they *disagree* on: product
  sulfur + CaS (H1), carbon-yield-vs-CaCO₃ + evolved CO (H2), Fe dispersion by
  SEM (H3). Two cheap decisive experiments: **swap CaCO₃ for pre-calcined CaO**
  (kills H2 if it still works) and **vary feed sulfur** (kills H1's benefit at
  low S). See `SIMULATION_HANDOFF.md §9`.
- **DG% is position-only and unreliable at the top** without an internal-standard
  2θ correction (a raw scan read an impossible 106.8%). `analysis/ground_truth.py:
  internal_standard_dg` now applies the engine's residual-Fe/Fe₃C internal
  standard, correcting that scan to 93.3% (matches bench). DG% ≈ 1.4% per 0.01°,
  so this correction is essential.

## Data & confidentiality

- `DATA/` (17 `.xy` scans + `Yield Data Measurements.xlsx`) and
  `SIMULATION_HANDOFF.md` are **confidential (pending patent 63/704,517)** and
  **gitignored**. Never commit them, never hardcode a real run's mass or
  composition into committed code. Example recipes in code/tests use generic
  round numbers (1.0 / 0.5 / 0.25 g), not the real loadings.
- `outputs/` and the generated dashboard HTML contain run-derived numbers — also
  gitignored. The dashboard is safe to share *within the lab* (it's their data).
- Filenames encode the recipe (`2GPC_4Fe_0.5CaCO3_1200C_5H`), parsed by
  `engine/run_parser.py`. **Unlabeled form = puck** (only `powder` is marked);
  `ground_truth.py` fills this in.

## Conventions

- Fit parameters live in `sim/kinetics.py: Params`; the fitted values are in
  `outputs/fitted_params.json` (regenerate via `python -m sim fit`). The dashboard
  and CLI load fitted values and fall back to `Params()` defaults.
- The dashboard's JS kinetics is a **line-for-line port** of `sim/kinetics.py`
  using fixed-step RK4 (`dt = 0.05 min`), verified numerically identical to the
  Python LSODA reference across the T/CaCO₃ grid. If you change `rhs`, update the
  JS port in `dashboard/template.html` and re-verify.
- Roadmap: **scale-up studies** are the next front (details forthcoming) — expect
  new inputs for larger charges / pellet sizes / bed effects.
