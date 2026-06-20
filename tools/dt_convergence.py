#!/usr/bin/env python3
"""Numerical convergence screen across dt values for selected PDT scenarios."""
from __future__ import annotations
import argparse, sys, math
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.simtools import run_scenario, summarize_dataframe, write_json  # noqa: E402

KEYS = ["MAP_final", "HR_final", "PaO2_final", "PaCO2_final", "pH_a_final", "CO_final", "lactate_final", "Vt_final", "ICP_mmHg_final"]


def convergence(scenarios: list[str], dts: list[float], tolerance: float = 0.20) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for scenario in scenarios:
        summaries = {}
        for dt in dts:
            _, df = run_scenario(scenario, dt=dt, quiet=True)
            summaries[dt] = summarize_dataframe(df)
            row = {"scenario": scenario, "dt": dt, **summaries[dt]}
            rows.append(row)
        ref_dt = min(dts)
        ref = summaries[ref_dt]
        for dt in dts:
            if dt == ref_dt:
                continue
            for key in KEYS:
                if key not in ref or key not in summaries[dt]:
                    continue
                denom = max(abs(float(ref[key])), 1e-6)
                rel = abs(float(summaries[dt][key]) - float(ref[key])) / denom
                rows.append({"scenario": scenario, "dt": dt, "metric": key, "relative_error_vs_finest": rel, "pass": rel <= tolerance})
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", nargs="+", default=["healthy_child_20kg", "ards_mild", "septic_shock"])
    ap.add_argument("--dts", nargs="+", type=float, default=[1.0, 0.5, 0.2])
    ap.add_argument("--tolerance", type=float, default=0.25)
    ap.add_argument("--outdir", default=str(ROOT / "outputs" / "validation_pack"))
    args = ap.parse_args()
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    df = convergence(args.scenarios, args.dts, args.tolerance)
    df.to_csv(outdir / "dt_convergence.csv", index=False)
    checks = df[df.get("relative_error_vs_finest").notna()] if "relative_error_vs_finest" in df else pd.DataFrame()
    write_json({"checks": int(len(checks)), "passed": int(checks.get("pass", pd.Series(dtype=bool)).sum()) if len(checks) else 0, "tolerance": args.tolerance}, outdir / "dt_convergence_summary.json")
    print(f"dt convergence report written to {outdir}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
