#!/usr/bin/env python3
"""Run multiple PDT scenarios and export a compact comparison table (v0.15)."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from simtools import run_scenario, scenario_path, summarize_dataframe, write_json  # noqa: E402

DEFAULT_METRICS = ["PaO2_final", "PaCO2_final", "MAP_final", "HR_final", "CO_final", "lactate_final", "VILI_risk_final", "SaO2_min", "MAP_min"]


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--scenarios", nargs="+", required=True)
    p.add_argument("--dt", type=float, default=0.1)
    p.add_argument("--outdir")
    args = p.parse_args(argv)

    ts = time.strftime("%Y%m%d_%H%M%S")
    out = Path(args.outdir) if args.outdir else ROOT / "outputs" / "comparisons" / ts
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    for s in args.scenarios:
        scen = scenario_path(s)
        _, df = run_scenario(scen, dt=args.dt, quiet=True)
        summ = summarize_dataframe(df)
        rows.append({"scenario": scen.stem, **summ})
    table = pd.DataFrame(rows)
    table.to_csv(out / "scenario_comparison.csv", index=False)
    write_json({"scenarios": args.scenarios, "metrics": DEFAULT_METRICS}, out / "comparison_metadata.json")

    plot_cols = [c for c in DEFAULT_METRICS if c in table.columns]
    if plot_cols:
        fig = plt.figure(figsize=(11, max(4, 0.55 * len(args.scenarios))))
        ax = fig.add_subplot(1, 1, 1)
        # Normalize each metric for visualization only.
        vis = table[["scenario", *plot_cols]].copy()
        for c in plot_cols:
            mn, mx = vis[c].min(), vis[c].max()
            vis[c] = 0 if mx == mn else (vis[c] - mn) / (mx - mn)
        bottom = None
        for c in plot_cols:
            vals = vis[c].values
            ax.barh(vis["scenario"], vals, left=bottom, label=c)
            bottom = vals if bottom is None else bottom + vals
        ax.set_title("Normalized scenario comparison")
        ax.legend(fontsize=7, ncol=2)
        fig.tight_layout()
        fig.savefig(out / "scenario_comparison.png", dpi=160)
        plt.close(fig)

    print(f"Scenario comparison written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
