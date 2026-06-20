#!/usr/bin/env python3
"""Monte Carlo runner for PDT scenarios (v0.15).

Example
-------
python tools/run_montecarlo.py --scenario ards_mild --n 200 --dt 0.1

Outputs are written to outputs/montecarlo/<scenario>_<timestamp>/:
  - runs_summary.csv: one row per run with sampled parameters and outcomes
  - aggregate_summary.json: distribution summaries and event probabilities
  - outcome_distributions.png: compact figure of key outcomes
  - parameter_specs.yaml: the uncertainty model used for reproducibility

This is not clinical validation. It is uncertainty exploration around an
in-silico scenario.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from simtools import (  # noqa: E402
    aggregate_runs, infer_default_parameters, load_yaml, run_config, sample_config,
    scenario_path, summarize_dataframe, write_json,
)


def _load_specs(args, config):
    if args.param_spec:
        specs = yaml.safe_load(Path(args.param_spec).read_text())
    else:
        specs = infer_default_parameters(config)
    if not specs:
        raise SystemExit("No numeric uncertainty parameters found. Provide --param-spec YAML.")
    return specs


def _plot_outcomes(df: pd.DataFrame, out: Path) -> None:
    candidates = [
        "PaO2_final", "PaCO2_final", "MAP_final", "CO_final", "lactate_final",
        "VILI_risk_final", "SaO2_final", "sepsis_severity_score_final",
        "airway_obstruction_index_final", "ICP_mmHg_final",
    ]
    cols = [c for c in candidates if c in df.columns]
    if not cols:
        return
    n = min(6, len(cols))
    fig = plt.figure(figsize=(10, 1.8 * n))
    for i, col in enumerate(cols[:n], start=1):
        ax = fig.add_subplot(n, 1, i)
        ax.hist(df[col].dropna(), bins=min(30, max(8, int(np.sqrt(len(df))))))
        ax.set_title(col)
        ax.set_ylabel("n")
    ax.set_xlabel("value")
    fig.tight_layout()
    fig.savefig(out / "outcome_distributions.png", dpi=160)
    plt.close(fig)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True, help="scenario YAML path or name, e.g. ards_mild")
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--dt", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--param-spec", help="optional YAML with dotted parameter specs")
    parser.add_argument("--outdir", help="optional output directory")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    scen_path = scenario_path(args.scenario)
    base_config = load_yaml(scen_path)
    specs = _load_specs(args, base_config)
    rng = np.random.default_rng(args.seed)

    ts = time.strftime("%Y%m%d_%H%M%S")
    out = Path(args.outdir) if args.outdir else ROOT / "outputs" / "montecarlo" / f"{scen_path.stem}_{ts}"
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    failures = []
    for i in range(args.n):
        cfg_i, draws = sample_config(base_config, specs, rng)
        try:
            df = run_config(cfg_i, dt=args.dt, quiet=True)
            row = {"run": i, **{f"param.{k}": v for k, v in draws.items()}, **summarize_dataframe(df)}
            rows.append(row)
        except Exception as exc:
            failures.append({"run": i, "error": str(exc), **{f"param.{k}": v for k, v in draws.items()}})
        if not args.quiet and (i + 1) % max(1, args.n // 10) == 0:
            print(f"{i+1}/{args.n} runs completed")

    if not rows:
        raise SystemExit(f"All runs failed. First failure: {failures[0] if failures else 'unknown'}")

    df_runs = pd.DataFrame(rows)
    df_runs.to_csv(out / "runs_summary.csv", index=False)
    if failures:
        pd.DataFrame(failures).to_csv(out / "failed_runs.csv", index=False)

    aggregate = aggregate_runs(rows)
    # Event probabilities from boolean/int flags.
    event_cols = [c for c in df_runs.columns if c.endswith("_any") or c.endswith("_final") and c.startswith("high_")]
    aggregate["event_probabilities"] = {c: float(df_runs[c].mean()) for c in event_cols if c in df_runs}
    aggregate["scenario"] = scen_path.name
    aggregate["seed"] = args.seed
    aggregate["failed_runs"] = len(failures)
    write_json(aggregate, out / "aggregate_summary.json")
    Path(out / "parameter_specs.yaml").write_text(yaml.safe_dump(specs, sort_keys=False))
    _plot_outcomes(df_runs, out)

    print(f"Monte Carlo completed: {len(rows)}/{args.n} successful runs")
    print(f"Output: {out}")
    return 0 if len(rows) == args.n else 2


if __name__ == "__main__":
    raise SystemExit(main())
