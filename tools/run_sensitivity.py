#!/usr/bin/env python3
"""One-at-a-time sensitivity analysis for PDT scenarios (v0.15).

Example
-------
python tools/run_sensitivity.py --scenario septic_shock --dt 0.1

Each selected parameter is perturbed down/up from baseline and final outcomes
are compared with the baseline scenario.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from simtools import (  # noqa: E402
    get_nested, infer_default_parameters, load_yaml, run_config, scenario_path,
    set_nested, summarize_dataframe, write_json,
)

DEFAULT_OUTCOMES = ["PaO2_final", "PaCO2_final", "MAP_final", "CO_final", "lactate_final", "VILI_risk_final"]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--dt", type=float, default=0.1)
    parser.add_argument("--fraction", type=float, default=0.20, help="relative down/up perturbation for positive parameters")
    parser.add_argument("--param-spec", help="optional YAML; keys define parameters to perturb")
    parser.add_argument("--outcomes", nargs="*", default=DEFAULT_OUTCOMES)
    parser.add_argument("--outdir")
    args = parser.parse_args(argv)

    scen = scenario_path(args.scenario)
    config = load_yaml(scen)
    specs = yaml.safe_load(Path(args.param_spec).read_text()) if args.param_spec else infer_default_parameters(config)
    params = list(specs.keys())
    if not params:
        raise SystemExit("No parameters available for sensitivity analysis.")

    ts = time.strftime("%Y%m%d_%H%M%S")
    out = Path(args.outdir) if args.outdir else ROOT / "outputs" / "sensitivity" / f"{scen.stem}_{ts}"
    out.mkdir(parents=True, exist_ok=True)

    base_df = run_config(config, dt=args.dt, quiet=True)
    base_summary = summarize_dataframe(base_df)
    rows = []
    for p in params:
        base_val = float(get_nested(config, p, specs[p].get("base", 0.0)))
        if base_val == 0:
            # Use absolute sd if baseline is zero.
            delta = float(specs[p].get("sd", 0.05))
            vals = [("down", max(float(specs[p].get("min", 0.0)), base_val - delta)),
                    ("up", min(float(specs[p].get("max", 1.0)), base_val + delta))]
        else:
            vals = [("down", base_val * (1 - args.fraction)), ("up", base_val * (1 + args.fraction))]
            vals = [(lab, max(float(specs[p].get("min", -1e99)), min(float(specs[p].get("max", 1e99)), val))) for lab, val in vals]
        for direction, val in vals:
            cfg = yaml.safe_load(yaml.safe_dump(config))
            set_nested(cfg, p, float(val))
            try:
                df = run_config(cfg, dt=args.dt, quiet=True)
                summary = summarize_dataframe(df)
                row = {"parameter": p, "direction": direction, "baseline_value": base_val, "value": val}
                for outcome in args.outcomes:
                    b = float(base_summary.get(outcome, float("nan")))
                    x = float(summary.get(outcome, float("nan")))
                    row[outcome] = x
                    row[f"delta_{outcome}"] = x - b
                rows.append(row)
            except Exception as exc:
                rows.append({"parameter": p, "direction": direction, "baseline_value": base_val, "value": val, "error": str(exc)})

    result = pd.DataFrame(rows)
    result.to_csv(out / "sensitivity_results.csv", index=False)
    write_json({"scenario": scen.name, "baseline": base_summary, "parameters": params}, out / "baseline_summary.json")

    # Tornado plot for first available outcome.
    outcome = next((o for o in args.outcomes if f"delta_{o}" in result.columns), None)
    if outcome:
        pivot = result.pivot_table(index="parameter", columns="direction", values=f"delta_{outcome}", aggfunc="mean").fillna(0)
        width = (pivot.get("up", 0) - pivot.get("down", 0)).abs().sort_values(ascending=True)
        top = width.tail(12).index
        fig = plt.figure(figsize=(9, max(4, 0.35 * len(top))))
        ax = fig.add_subplot(1, 1, 1)
        y = range(len(top))
        lows = pivot.loc[top].get("down", pd.Series(0, index=top))
        ups = pivot.loc[top].get("up", pd.Series(0, index=top))
        ax.barh(list(y), lows, label="down")
        ax.barh(list(y), ups, label="up")
        ax.set_yticks(list(y))
        ax.set_yticklabels(list(top))
        ax.set_xlabel(f"Δ {outcome}")
        ax.set_title(f"One-at-a-time sensitivity: {outcome}")
        ax.legend()
        fig.tight_layout()
        fig.savefig(out / "tornado_plot.png", dpi=160)
        plt.close(fig)

    print(f"Sensitivity analysis completed: {len(result)} runs")
    print(f"Output: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
