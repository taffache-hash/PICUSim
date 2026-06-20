#!/usr/bin/env python3
"""Generate literature-anchor plausibility report for PDT scenarios (v0.39).

This is not external clinical validation. It compares selected synthetic scenario
outputs with broad literature-derived envelopes stored in
`data/literature_benchmark_targets_v0.39.yaml`.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.simtools import run_scenario, write_json  # noqa: E402


def _get_final_value(df: pd.DataFrame, variable: str, config: Dict[str, Any]) -> float:
    last = df.iloc[-1]
    if variable == "Vt_per_kg":
        wt = float(config.get("patient", {}).get("weight_kg", 1.0)) or 1.0
        return float(last.get("Vt", float("nan"))) / wt
    if variable in last.index:
        return float(last[variable])
    return float("nan")


def evaluate(spec_path: Path, dt: float, selected: list[str] | None = None, max_scenarios: int | None = None) -> pd.DataFrame:
    spec = yaml.safe_load(spec_path.read_text())
    scenarios = spec.get("scenarios", {})
    rows: List[Dict[str, Any]] = []
    count = 0
    for scenario, scfg in scenarios.items():
        if selected and scenario not in selected:
            continue
        if max_scenarios is not None and count >= max_scenarios:
            break
        count += 1
        try:
            config, df = run_scenario(scenario, dt=dt, quiet=True)
            run_error = ""
        except Exception as e:
            config, df, run_error = {}, pd.DataFrame(), repr(e)
        targets = scfg.get("targets", {})
        for variable, tcfg in targets.items():
            lo, hi = [float(x) for x in tcfg.get("range", [float("nan"), float("nan")])]
            value = float("nan") if df.empty else _get_final_value(df, variable, config)
            passed = bool(lo <= value <= hi) if pd.notna(value) and not run_error else False
            rows.append({
                "scenario": scenario,
                "variable": variable,
                "value": value,
                "low": lo,
                "high": hi,
                "pass": passed,
                "sources": ";".join(tcfg.get("source", [])),
                "target_type": tcfg.get("target_type", ""),
                "severity_band": tcfg.get("severity_band", scfg.get("severity_band", "")),
                "age_band": scfg.get("age_band", ""),
                "rationale": tcfg.get("rationale", ""),
                "derived_from": tcfg.get("derived_from", ""),
                "run_error": run_error,
            })
    return pd.DataFrame(rows)


def write_markdown(df: pd.DataFrame, spec: Dict[str, Any], path: Path) -> None:
    total = int(len(df))
    passed = int(df["pass"].sum()) if total else 0
    lines = [
        "# PDT v0.39 Literature Benchmark Report",
        "",
        "This report compares selected synthetic PDT scenario outputs with broad literature-derived plausibility envelopes.",
        "It is **not** external clinical validation and must not be used for clinical decision support.",
        "",
        f"**Overall:** {passed}/{total} checks passed.",
        "",
        "## Sources",
        "",
    ]
    for sid, src in spec.get("sources", {}).items():
        lines.append(f"- **{sid}** — {src.get('title','')}. {src.get('url','')}")
    lines.append("")
    if not df.empty:
        for scenario, sub in df.groupby("scenario"):
            s_pass = int(sub["pass"].sum())
            lines += [f"## {scenario}", "", f"Passed {s_pass}/{len(sub)} checks.", "", "| Variable | Value | Target | Type | Severity | Status | Sources |", "|---|---:|---:|---|---|---|---|"]
            for _, r in sub.iterrows():
                status = "PASS" if bool(r["pass"]) else "REVIEW"
                value = "nan" if pd.isna(r["value"]) else f"{float(r['value']):.4g}"
                target = f"{float(r['low']):.4g}–{float(r['high']):.4g}"
                lines.append(f"| {r['variable']} | {value} | {target} | {r.get('target_type','')} | {r.get('severity_band','')} | {status} | {r['sources']} |")
            lines.append("")
    path.write_text("\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default=str(ROOT / "data" / "literature_benchmark_targets_v0.39.yaml"))
    ap.add_argument("--dt", type=float, default=1.0)
    ap.add_argument("--outdir", default=str(ROOT / "outputs" / "validation_pack"))
    ap.add_argument("--scenarios", nargs="*", default=None)
    ap.add_argument("--max-scenarios", type=int, default=None)
    ap.add_argument("--fail-on-review", action="store_true")
    args = ap.parse_args()
    spec_path = Path(args.spec)
    spec = yaml.safe_load(spec_path.read_text())
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    df = evaluate(spec_path, dt=args.dt, selected=args.scenarios, max_scenarios=args.max_scenarios)
    df.to_csv(outdir / "literature_benchmark_report.csv", index=False)
    write_markdown(df, spec, outdir / "literature_benchmark_report.md")
    summary = {
        "checks": int(len(df)),
        "passed": int(df["pass"].sum()) if len(df) else 0,
        "review": int((~df["pass"]).sum()) if len(df) else 0,
        "dt": args.dt,
        "spec": str(spec_path.name),
    }
    write_json(summary, outdir / "literature_benchmark_summary.json")
    print(json.dumps(summary, indent=2))
    return 1 if args.fail_on_review and summary["review"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
