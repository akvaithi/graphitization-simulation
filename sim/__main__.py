"""CLI: python -m sim <subcommand>

Subcommands:
  ground-truth   run the engine on all DATA/*.xy scans + join xlsx masses (front A/B data)
  fit            fit kinetic parameters to the ground-truth dataset (fronts A/D)
  sweep          run the fitted (or default) model across the real recipe grid
  ablate         H1/H2/H3 ablation for one recipe (front D)
  report         run everything and write outputs/ (gitignored)
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

import sim  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "outputs"


def cmd_ground_truth(args):
    from analysis.ground_truth import main as gt_main
    gt_main(OUT_DIR)


def cmd_fit(args):
    from analysis.ground_truth import build_ground_truth
    from sim.inference import fit
    gt = build_ground_truth()
    result = fit(gt["metrics"], gt["yields"])
    OUT_DIR.mkdir(exist_ok=True)
    payload = {"fitted_values": result["fitted_values"], "rmse": result["rmse"],
              "success": result["success"], "n_residuals": result["n_residuals"]}
    (OUT_DIR / "fitted_params.json").write_text(json.dumps(payload, indent=2))
    print(f"wrote {OUT_DIR/'fitted_params.json'}")


def _load_fitted_params():
    from dataclasses import replace
    from sim.kinetics import Params
    path = OUT_DIR / "fitted_params.json"
    if not path.exists():
        print("no fitted_params.json found; run `python -m sim fit` first. Using defaults.",
              file=sys.stderr)
        return Params()
    fitted = json.loads(path.read_text())["fitted_values"]
    return replace(Params(), **fitted)


def cmd_sweep(args):
    from sim.kinetics import Recipe
    from sim.massbalance import run_mass_balance
    params = _load_fitted_params()
    recipes = [
        Recipe(2, 6, 1.0, 1000, 5), Recipe(2, 6, 1.0, 1100, 5),
        Recipe(2, 6, 1.0, 1200, 5), Recipe(2, 6, 1.0, 1300, 5),
        Recipe(2, 4, 0.25, 1200, 5), Recipe(2, 4, 0.5, 1200, 5),
        Recipe(2, 4, 0.75, 1200, 5), Recipe(2, 4, 1.0, 1200, 5),
        Recipe(2, 2, 1.0, 1200, 5), Recipe(2, 3, 1.0, 1200, 5),
        Recipe(2, 6, 1.0, 1200, 0.5), Recipe(2, 6, 1.0, 1200, 1),
    ]
    print(f"{'Fe':>4} {'CaCO3':>7} {'T':>5} {'t':>5} | {'am':>5} {'turb':>5} {'gr':>5} "
         f"{'q':>5} | {'Cyield':>7}")
    for r in recipes:
        mb = run_mass_balance(r, params)
        f = mb["carbon"]["phase_fractions"]
        print(f"{r.fe_mass:4.1f} {r.caco3_mass:7.4f} {r.temperature_C:5.0f} {r.time_h:5.1f} | "
             f"{f['amorphous']:5.3f} {f['turbostratic']:5.3f} {f['graphitic']:5.3f} "
             f"{mb['carbon']['ordering_q']:5.3f} | {mb['yield']['carbon_yield']:7.3f}")


def cmd_ablate(args):
    from sim.hypotheses import run_ablation
    from sim.kinetics import Recipe
    params = _load_fitted_params()
    recipe = Recipe(args.pc, args.fe, args.caco3, args.temperature, args.time)
    rows = run_ablation(recipe, params)
    print(f"{'H1':>5} {'H2':>5} {'H3':>5} | {'gr':>6} {'am':>6} {'q':>6} {'yield':>6} {'S_left':>7}")
    for r in rows:
        print(f"{str(r['H1']):>5} {str(r['H2']):>5} {str(r['H3']):>5} | "
             f"{r['graphitic_frac']:6.3f} {r['amorphous_frac']:6.3f} {r['ordering_q']:6.3f} "
             f"{r['carbon_yield']:6.3f} {r['sulfur_remaining_g']:7.4f}")


def cmd_report(args):
    OUT_DIR.mkdir(exist_ok=True)
    print("== ground truth ==")
    cmd_ground_truth(args)
    print("\n== fit ==")
    cmd_fit(args)
    print("\n== sweep (fitted params) ==")
    cmd_sweep(args)
    print(f"\nreport complete -> {OUT_DIR}/ (gitignored, contains run-derived numbers)")


def main():
    ap = argparse.ArgumentParser(prog="python -m sim", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ground-truth").set_defaults(func=cmd_ground_truth)
    sub.add_parser("fit").set_defaults(func=cmd_fit)
    sub.add_parser("sweep").set_defaults(func=cmd_sweep)
    ap_ablate = sub.add_parser("ablate")
    ap_ablate.add_argument("--pc", type=float, default=2.0)
    ap_ablate.add_argument("--fe", type=float, default=4.0)
    ap_ablate.add_argument("--caco3", type=float, default=1.0)
    ap_ablate.add_argument("--temperature", type=float, default=1200.0)
    ap_ablate.add_argument("--time", type=float, default=5.0)
    ap_ablate.set_defaults(func=cmd_ablate)
    sub.add_parser("report").set_defaults(func=cmd_report)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
