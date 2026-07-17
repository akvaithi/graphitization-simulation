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
sim/         the simulation (state, schedule, kinetics ODE, mass balance, xrd
             forward, calibration, tga, hypotheses, inference, __main__ CLI).
SOURCES.md   every mechanism/assumption -> a citation (for defending to a PI).
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

### Furnace schedule (`sim/schedule.py`, used by `sim/kinetics.py: simulate`)
Two reactor modes, both full multi-segment programs (piecewise-linear T(t)):
- **Tube furnace** (`reactor="tube"`, default) — reproduces the group's real
  C01..T10 controller program: RT → **preheat holds** at 300/800/1200 °C (20 min
  each, only those below the peak) → ramp to the process peak → **process hold**
  (`time_h`) → **programmed cooling** (5 °C/min to 500 °C) → **natural cooling**.
  The 1400 °C / 2 h example is reproduced exactly. The preheat holds matter:
  calcination and sulfur trapping begin during the 800 °C hold, not only at peak.
- **Rotary kiln** (`reactor="kiln"`) — the scale-up reactor. **It DOES have an
  isothermal hold**: fast heated entry → isothermal hold at peak (the hot-zone
  traverse, the bulk of the residence) → fast cool exit (Kintek kiln-zone refs).
  Hard limits: peak ≤ 1300 °C, residence ≤ 2 h. With the hold, a 1300 °C/2 h kiln
  pass graphitizes well (~90% at lab cross-section) — the kiln is viable; the
  scale penalty comes from cross-section, not the reactor. *(An earlier version
  wrongly modeled the kiln as a hold-free triangle; corrected per lab feedback.)*
- **Kiln geometry is counter-current** (from the lab's kiln notes), and two
  consequences are modeled:
  1. **O₂ is not uniform.** Coke feeds in at the raised top end and travels down
     to the **burner (natural gas + air) at the bottom/discharge end**; the flue
     gas flows counter-current back up and exhausts at the top, its O₂ consumed
     on the way. So **more O₂ at the bottom than the top** — and the bottom is
     *also* the hot zone, so the charge meets the most oxygen exactly when it is
     hottest (worst case for burn-off). `schedule.TemperatureProgram.o2_scale_at`
     scales O₂ with the normalized gas temperature (a proxy for axial position);
     the tube furnace is uniform (`scale = 1`).
  2. **Fines cannot be fed.** The counter-current gas elutriates fine particles
     out the exhaust, so kiln feed **must be agglomerated** (pellet / extrudate /
     impregnated). `kinetics.feed_warnings` flags `reactor="kiln"` +
     `binding="dry_mix"`. This is an operational constraint (a flag), not a rate
     term — and it is an independent reason the **extruder** route is the scale-up
     path, on top of the cross-section/heat-transfer argument.

### Material thermal lag (`sim/kinetics.py`, the heat-transfer model)
The **gas** follows the program above; the **material** lags it by a lumped-
capacitance time constant and the chemistry sees the *material* temperature:
`dT_mat/dt = (T_gas − T_mat)/τ`, `τ = tau_lin·L + tau_quad·L²`, L = cross-sectional
dimension (mm). Carbon's finite conductivity (raw coke ~2–4 W/m·K) means a thin
lab puck (L≈2.5 mm, τ≈0.6 min) tracks the gas, but a thick cross-section lags and
never reaches peak. This is the real scale-up lever — and why the **extruder**
(fixed small cross-section, length scales with throughput) carries no thermal
penalty while a **bigger puck** (L grows as mass^⅓) does. `Recipe.geometry`
("puck"/"extrudate") + `pc_mass` set L via `char_dim_mm()`, or override directly.

### Atmosphere (argon by default; optional O₂ for scale-up)
- The lab furnace runs under argon → default `o2_frac = 0`, i.e. **no combustion**:
  carbon leaves only via **Boudouard** (`C + CO₂ → 2 CO`) and volatiles.
- **`o2_frac > 0` turns on an O₂-combustion term** (`C + O₂ → CO₂`, amorphous-
  selective) for exploring a non-inert / imperfectly-sealed atmosphere at scale
  (real calcining kilns are "oxygen-deficient," not inert). Only the carbon mass
  is booked (to `C_burn_out`) since the O₂ is external, so the closed-ledger mass
  balance still holds. This is a **predictive knob** (no O₂ data) — a slider in
  the dashboard. It is separate from **`sim/tga.py`** (Front C), which burns the
  *washed product* in air to split amorphous vs graphitic — a measurement, not the
  furnace.
- Gas leaves via a transient in-pellet **CO₂ pool** (reacts via Boudouard or
  escapes at `k_esc`), so Boudouard *efficiency* is emergent. Argon flow is
  subsumed into `k_esc`.

### Scale-up model — two independent levers
1. **Fe–carbon contact** (`contact_factor`, `BINDING_CONTACT`): the catalytic step
   is a dissolution–reprecipitation at the Fe–carbon interface, so binding sets a
   rate multiplier — `pellet` 1.0, `wet_impregnation` 1.6 (finest dispersion),
   `extrusion` 0.9, `dry_mix` 0.45. Throughput/charge mass does **not** enter here.
2. **Heat transfer** (thermal lag above): size enters only through the
   cross-section, so scaling by extrusion (constant cross-section) has no penalty.
- Both are **hypothesis-level** (no scale-up data), adjustable, sourced in
  SOURCES.md §5–6, and leave the tube-furnace fit untouched (lab defaults give
  contact=1, τ≈0.6 min).

### Hypotheses: H1 confirmed, H3 the focus, H2 negligible
- **H1** (sulfur trapping) confirmed — see above.
- **H3** (calcium) is the discrimination **focus**: calcium reduces Fe particle
  size / prevents sintering, wets the Fe (CaO–FeₓOy layer), and co-catalyzes via a
  CaC₂ carbide route above ~1200 °C — together lowering the graphitization onset
  (the group's ~350 °C shift). Modeled as a saturating rate multiplier `disp` in
  the CaO fraction. Sources in SOURCES.md §2b.
- **H2** (Boudouard) has **negligible** impact (toggling it barely moves results;
  `alpha_H2` rails in the fit) — de-emphasized in the dashboard, kept as a toggle.

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
  the ~7 wt% sulfur in GPC poisons the Fe catalyst at these low temperatures, and
  CaO from CaCO₃ is what neutralizes it. There is a **sharp threshold at the ~1:1
  S:CaCO₃ point** (sub-stoichiometric CaCO₃ fails; at/above ~1:1 it works) — the
  stoichiometric fingerprint of a trapping sink. The fitted `p_poison` and
  `k0_trap` both climb to reflect this. *(Specific run values live in the private
  DATA/ and outputs/, never in committed files.)*
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
- **Sources over math when explaining.** The PI weighs citations heavily, so
  documentation and the dashboard justify claims from the literature (SOURCES.md),
  not from the equations. Keep this: when adding a mechanism, add its citation to
  SOURCES.md and reference it, rather than only writing the rate law.
- Roadmap: the **scale-up front** (rotary kiln, larger charges, pressureless
  binding methods, O₂) is now in the model as a *predictive* layer awaiting data;
  more scale-up specifics are forthcoming. The kiln's hold-free profile predicts a
  large graphitization penalty that better Fe–carbon contact (wet impregnation)
  and higher Fe partly recover — the main scale-up lever to validate at the bench.
