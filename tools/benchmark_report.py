#!/usr/bin/env python3
"""Generate internal quantitative benchmark report for PDT scenarios (v0.28).

This is not external clinical validation. It is a reproducible regression layer:
scenario outputs are compared with broad, documented plausibility envelopes.
"""
from __future__ import annotations
import argparse, sys, json
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.simtools import run_scenario, write_json  # noqa: E402


def _fmt(x: Any) -> str:
    try:
        return f"{float(x):.3g}"
    except Exception:
        return str(x)


def evaluate_benchmarks(spec_path: Path, dt: float = 1.0) -> pd.DataFrame:
    spec = yaml.safe_load(spec_path.read_text())
    rows: List[Dict[str, Any]] = []
    for scenario, cfg in spec.items():
        max_time = float(cfg.get("max_time_s", 300))
        _, df = run_scenario(scenario, dt=dt, quiet=True)
        # restrict to requested evaluation horizon if scenario is longer
        if "time" in df.columns:
            eval_df = df[df["time"] <= max_time]
            if len(eval_df):
                df = eval_df
        row = df.iloc[-1]
        for variable, bounds in cfg.get("ranges", {}).items():
            lo, hi = float(bounds[0]), float(bounds[1])
            val = float(row[variable]) if variable in row.index else float("nan")
            passed = bool(lo <= val <= hi)
            rows.append({
                "scenario": scenario,
                "variable": variable,
                "value": val,
                "low": lo,
                "high": hi,
                "pass": passed,
                "time_s": float(row.get("time", max_time)),
            })
    return pd.DataFrame(rows)


def write_markdown(df: pd.DataFrame, path: Path) -> None:
    passed = int(df["pass"].sum()) if len(df) else 0
    total = int(len(df))
    lines = [
        "# PDT v0.28 Internal Benchmark Report",
        "",
        "This report compares selected scenario outputs with broad internal plausibility ranges.",
        "It is a regression/credibility aid, not external clinical validation.",
        "",
        f"**Overall:** {passed}/{total} checks passed.",
        "",
    ]
    for scenario, sub in df.groupby("scenario"):
        s_pass = int(sub["pass"].sum())
        lines += [f"## {scenario}", "", f"Passed {s_pass}/{len(sub)} checks.", "", "| Variable | Value | Expected range | Status |", "|---|---:|---:|---|"]
        for _, r in sub.iterrows():
            status = "PASS" if bool(r["pass"]) else "FAIL"
            lines.append(f"| {r['variable']} | {_fmt(r['value'])} | {_fmt(r['low'])}–{_fmt(r['high'])} | {status} |")
        lines.append("")
    path.write_text("\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default=str(ROOT / "benchmarks" / "expected_ranges.yaml"))
    ap.add_argument("--dt", type=float, default=1.0)
    ap.add_argument("--outdir", default=str(ROOT / "outputs" / "validation_pack"))
    ap.add_argument("--fail-on-error", action="store_true")
    args = ap.parse_args()
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    df = evaluate_benchmarks(Path(args.spec), dt=args.dt)
    df.to_csv(outdir / "benchmark_report.csv", index=False)
    write_markdown(df, outdir / "benchmark_report.md")
    write_json({"checks": int(len(df)), "passed": int(df["pass"].sum()), "failed": int((~df["pass"]).sum())}, outdir / "benchmark_summary.json")
    print(f"Benchmark report written to {outdir}")
    if args.fail_on_error and not bool(df["pass"].all()):
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
