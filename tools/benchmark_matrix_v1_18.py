#!/usr/bin/env python3
"""v1.18 benchmark matrix and coverage dashboard.

This tool extends the previous literature benchmark report with:
- a source-to-target matrix;
- scenario YAML coverage accounting;
- optional fast scenario evaluation;
- explicit PASS/REVIEW/FALSE run-error status.

It is a plausibility/regression layer, not external clinical validation.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.simtools import run_scenario, write_json  # noqa: E402


def load_spec(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text())


def _final_value(df: pd.DataFrame, config: Dict[str, Any], variable: str) -> float:
    if df.empty:
        return float("nan")
    row = df.iloc[-1]
    if variable == "Vt_per_kg":
        wt = float(config.get("patient", {}).get("weight_kg", 1.0)) or 1.0
        return float(row.get("Vt", float("nan"))) / wt
    if variable == "fluid_overload_percent":
        # direct variable when present; otherwise derive roughly from fluid balance / body weight.
        if "fluid_overload_percent" in row.index:
            return float(row["fluid_overload_percent"])
        wt = float(config.get("patient", {}).get("weight_kg", 1.0)) or 1.0
        return 100.0 * float(row.get("fluid_balance", 0.0)) / (wt * 1000.0)
    if variable in row.index:
        return float(row[variable])
    return float("nan")


def build_target_matrix(spec: Dict[str, Any]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for scenario, scfg in spec.get("scenarios", {}).items():
        for variable, tcfg in scfg.get("targets", {}).items():
            refs = tcfg.get("source", []) or []
            rows.append({
                "scenario": scenario,
                "age_band": scfg.get("age_band", ""),
                "scenario_severity": scfg.get("severity_band", ""),
                "variable": variable,
                "low": (tcfg.get("range", [None, None]) or [None, None])[0],
                "high": (tcfg.get("range", [None, None]) or [None, None])[1],
                "target_type": tcfg.get("target_type", ""),
                "target_severity": tcfg.get("severity_band", scfg.get("severity_band", "")),
                "sources": ";".join(refs),
                "missing_source_ids": ";".join([r for r in refs if r not in spec.get("sources", {})]),
                "derived_from": tcfg.get("derived_from", ""),
                "rationale": tcfg.get("rationale", ""),
            })
    return pd.DataFrame(rows)


def build_coverage(spec: Dict[str, Any]) -> pd.DataFrame:
    benchmarked = set(spec.get("scenarios", {}).keys())
    all_scenarios = sorted(p.stem for p in (ROOT / "scenarios").glob("*.yaml"))
    rows = []
    for s in all_scenarios:
        targets = spec.get("scenarios", {}).get(s, {}).get("targets", {})
        rows.append({
            "scenario": s,
            "has_benchmark": s in benchmarked,
            "target_count": len(targets),
        })
    return pd.DataFrame(rows)


def evaluate(spec: Dict[str, Any], dt: float, selected: list[str] | None = None, max_scenarios: int | None = None) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    count = 0
    for scenario, scfg in spec.get("scenarios", {}).items():
        if selected and scenario not in selected:
            continue
        if max_scenarios is not None and count >= max_scenarios:
            break
        count += 1
        try:
            config, df = run_scenario(scenario, dt=dt, quiet=True)
            run_error = ""
        except Exception as exc:  # pragma: no cover - captured in output
            config, df = {}, pd.DataFrame()
            run_error = repr(exc)
        for variable, tcfg in scfg.get("targets", {}).items():
            lo, hi = [float(x) for x in tcfg.get("range", [float("nan"), float("nan")])]
            val = _final_value(df, config, variable)
            is_num = not (isinstance(val, float) and math.isnan(val))
            passed = bool(is_num and not run_error and lo <= float(val) <= hi)
            rows.append({
                "scenario": scenario,
                "variable": variable,
                "value": val,
                "low": lo,
                "high": hi,
                "status": "PASS" if passed else "REVIEW",
                "pass": passed,
                "sources": ";".join(tcfg.get("source", []) or []),
                "target_type": tcfg.get("target_type", ""),
                "severity_band": tcfg.get("severity_band", scfg.get("severity_band", "")),
                "run_error": run_error,
            })
    return pd.DataFrame(rows)


def write_markdown(path: Path, spec: Dict[str, Any], matrix: pd.DataFrame, coverage: pd.DataFrame, eval_df: pd.DataFrame | None) -> None:
    lines = [
        "# PDT v1.18 Benchmark Matrix",
        "",
        "This dashboard expands scenario-level literature-anchor plausibility corridors.",
        "It is **not** external clinical validation and must not be used for clinical decision support.",
        "",
        f"Spec version: **{spec.get('version','')}**",
        "",
    ]
    if not coverage.empty:
        covered = int(coverage["has_benchmark"].sum())
        total = int(len(coverage))
        pct = 100.0 * covered / total if total else 0.0
        lines += [f"## Coverage", "", f"Benchmarked scenarios: **{covered}/{total}** ({pct:.1f}%).", ""]
    lines += ["## Source inventory", ""]
    for sid, src in spec.get("sources", {}).items():
        lines.append(f"- **{sid}** — {src.get('title','')} — {src.get('url','')}")
    lines += ["", "## Target matrix", "", "| Scenario | Variable | Range | Type | Sources |", "|---|---|---:|---|---|"]
    for _, r in matrix.iterrows():
        lines.append(f"| {r['scenario']} | {r['variable']} | {r['low']}–{r['high']} | {r['target_type']} | {r['sources']} |")
    if eval_df is not None:
        passed = int(eval_df["pass"].sum()) if not eval_df.empty else 0
        total = int(len(eval_df))
        lines += ["", "## Evaluation", "", f"Checks passed: **{passed}/{total}**.", "", "| Scenario | Variable | Value | Target | Status |", "|---|---|---:|---:|---|"]
        for _, r in eval_df.iterrows():
            val = "nan" if pd.isna(r["value"]) else f"{float(r['value']):.4g}"
            lines.append(f"| {r['scenario']} | {r['variable']} | {val} | {r['low']:.4g}–{r['high']:.4g} | {r['status']} |")
    path.write_text("\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default=str(ROOT / "data" / "literature_benchmark_targets_v1.18.yaml"))
    ap.add_argument("--outdir", default=str(ROOT / "outputs" / "benchmark_matrix_v1.18"))
    ap.add_argument("--dt", type=float, default=10.0)
    ap.add_argument("--scenarios", nargs="*", default=None)
    ap.add_argument("--max-scenarios", type=int, default=None)
    ap.add_argument("--no-run", action="store_true")
    ap.add_argument("--fail-on-review", action="store_true")
    args = ap.parse_args()

    spec = load_spec(Path(args.spec))
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)

    matrix = build_target_matrix(spec)
    coverage = build_coverage(spec)
    matrix.to_csv(outdir / "benchmark_target_matrix_v118.csv", index=False)
    coverage.to_csv(outdir / "benchmark_scenario_coverage_v118.csv", index=False)

    eval_df = None if args.no_run else evaluate(spec, dt=args.dt, selected=args.scenarios, max_scenarios=args.max_scenarios)
    if eval_df is not None:
        eval_df.to_csv(outdir / "benchmark_evaluation_v118.csv", index=False)

    write_markdown(outdir / "benchmark_matrix_report_v118.md", spec, matrix, coverage, eval_df)

    missing_refs = int((matrix["missing_source_ids"].fillna("") != "").sum()) if not matrix.empty else 0
    covered = int(coverage["has_benchmark"].sum()) if not coverage.empty else 0
    scenario_total = int(len(coverage))
    summary = {
        "release": "v1.18-alpha",
        "spec": Path(args.spec).name,
        "sources": len(spec.get("sources", {})),
        "benchmark_scenarios": len(spec.get("scenarios", {})),
        "scenario_yaml_count": scenario_total,
        "scenario_coverage_pct": round(100.0 * covered / scenario_total, 2) if scenario_total else 0.0,
        "target_rows": int(len(matrix)),
        "missing_source_rows": missing_refs,
        "evaluated_checks": int(len(eval_df)) if eval_df is not None else 0,
        "pass": int(eval_df["pass"].sum()) if eval_df is not None and not eval_df.empty else 0,
        "review": int((~eval_df["pass"]).sum()) if eval_df is not None and not eval_df.empty else 0,
    }
    write_json(summary, outdir / "benchmark_matrix_summary_v118.json")
    print(json.dumps(summary, indent=2))

    if args.fail_on_review and summary["review"]:
        return 1
    if args.fail_on_review and summary["missing_source_rows"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
