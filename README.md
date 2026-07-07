# Catalytic Graphitization Simulation

A simulation of Fe-catalyzed, CaCO3-assisted graphitization of petroleum coke,
addressing the four fronts laid out for this effort:

- **A — Mass balance**: where every gram of C/S/Fe/Ca goes, pellet -> furnace -> acid wash.
- **B — XRD forward model + calibration**: what (002) peak *intensity* means, closing the
  loop between simulated phase masses and the same engine code used on real scans.
- **C — TGA/DTG prediction**: differential-oxidation curves separating amorphous from
  graphitic carbon by an independent, diffraction-free route (predictive; no TGA data yet).
- **D — Mechanism discrimination**: ablating the three competing CaCO3 hypotheses
  (H1 sulfur trapping, H2 Boudouard etching, H3 catalyst dispersion).

The central problem this project addresses: XRD Degree of Graphitization (DG%) is
computed from peak *position* only and is blind to how much amorphous carbon
survives. A sample can read DG ~ 97% while a large mass fraction is still
disordered. This simulation is built to close that gap.

## Layout

```
engine/       ported analyzer (github.com/akvaithi/xrd-graphitization-analyzer):
              validated DG%/Scherrer engine, amorphous crystallinity index,
              mixture/internal-standard calibration, spreadsheet-ported yield chemistry
sim/          the simulation itself
  state.py         pellet mass-vector (grams) + mass-conservation check
  feedstock.py     PC grade -> (C, S) composition
  kinetics.py      ODE kinetics over the furnace schedule (devolatilization,
                   calcination, Boudouard, graphitization, sulfur trapping);
                   H1/H2/H3 are explicit switchable terms
  massbalance.py   pellet -> post-furnace -> post-acid ledger (front A)
  xrd_forward.py   phase masses -> synthetic (002) pattern (front B)
  calibration_sim.py  closed-loop mixture calibration + real-scan inversion
  hypotheses.py    H1/H2/H3 ablation, threshold scan, ReaxFF-handoff export (front D)
  tga.py           predicted TGA/DTG burn-off curves (front C)
  inference.py     least-squares fit of kinetics to the ground-truth dataset
  __main__.py      `python -m sim <subcommand>` CLI
analysis/ground_truth.py  runs the engine on every real scan + joins the weighed
              masses; the target dataset every front fits against
tests/        pytest suite (ported engine tests + new sim tests)
```

`DATA/` (the real XRD scans and the weighed-mass spreadsheet) and
`SIMULATION_HANDOFF.md` are gitignored — confidential, pending patent. Nothing
in the committed code hardcodes a real run's mass or composition.

## Setup

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Running

```
.venv/bin/python -m pytest tests/ -q          # engine + sim test suite

.venv/bin/python -m sim ground-truth          # metrics for every DATA/*.xy scan + xlsx masses
.venv/bin/python -m sim fit                    # fit kinetics to the ground-truth dataset
.venv/bin/python -m sim sweep                  # run the fitted model across the real recipe grid
.venv/bin/python -m sim ablate --fe 4 --caco3 1.0 --temperature 1200 --time 5
.venv/bin/python -m sim report                  # everything above, in order
```

All generated numbers land in `outputs/` (gitignored, since they are derived
from the confidential DATA/).

## Design notes

- **Closed loop**: `sim/xrd_forward.py` renders a synthetic pattern from
  simulated phase masses, then the *same* engine code (`fit_netl`,
  `crystallinity_index`, `norm_002_area`) that analyzes the real scans is run
  on it. This is what makes front B falsifiable against all 17 real scans, not
  just the 6 mass-balance rows — and is how `sim/calibration_sim.py` validates
  that a normalized XRD metric actually recovers a known composition
  (held-out MAE < 5 wt%, matching the engine's own `--selftest` bar) before
  trusting it on real data.
- **yield_calc reconciliation**: `sim/massbalance.py`'s chemistry generalizes
  the spreadsheet-ported `engine/research/yield_calc.py` (which assumes
  instantaneous calcination, non-selective Boudouard etching, complete sulfur
  trapping, and "remaining C -> graphite"). Setting `alpha_H2=1` (H2 off)
  reproduces that spreadsheet's blind 1:1 carbon debit.
- **Index vs. weight fraction**: the engine's `crystalline_fraction` is a
  model-dependent XRD index (Ruland & Smarsly), not literally a mass
  fraction. `sim/inference.py` fits the simulation's *ordering coordinate* to
  track that index's ranking across the sweep, and keeps the mass-balance fit
  (against real weighed masses) independent of that caveat.
- **Front D is staged, not MD**: `sim/hypotheses.py` ablates H1/H2/H3 in the
  kinetic model and exports a JSON handoff (`export_reaxff_handoff`) of
  fitted interface conditions and phase composition for an atomistic
  follow-up in the sibling ReaxFF repo — no molecular dynamics runs here.
