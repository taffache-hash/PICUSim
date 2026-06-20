#!/usr/bin/env python3
"""PDT v5.0A literature benchmark engine.

Runs a small, publication-oriented physiological plausibility suite. This is not
external validation; it produces reproducible in-silico checks against broad,
source-traceable corridors.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.simtools import run_scenario, write_json  # noqa: E402


def load_spec(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _series(df: pd.DataFrame, variable: str) -> pd.Series:
    if variable in df.columns:
        return pd.to_numeric(df[variable], errors="coerce")
    return pd.Series(dtype=float)


def extract_value(df: pd.DataFrame, variable: str) -> float:
    """Extract final/min/max values from a run dataframe.

    Convention: variables ending in _min use trajectory minimum, _max use maximum,
    otherwise final value is used.
    """
    if df.empty:
        return float("nan")
    if variable.endswith("_min"):
        base = variable[:-4]
        s = _series(df, base)
        return float(s.min()) if not s.empty else float("nan")
    if variable.endswith("_max"):
        base = variable[:-4]
        s = _series(df, base)
        return float(s.max()) if not s.empty else float("nan")
    s = _series(df, variable)
    return float(s.iloc[-1]) if not s.empty else float("nan")


def pct_deviation(value: float, low: float, high: float) -> float:
    if math.isnan(value):
        return float("nan")
    if low <= value <= high:
        return 0.0
    if value < low:
        return 100.0 * (low - value) / max(abs(low), 1e-9)
    return 100.0 * (value - high) / max(abs(high), 1e-9)


def build_source_matrix(spec: Dict[str, Any]) -> pd.DataFrame:
    rows = []
    known = set(spec.get("sources", {}).keys())
    for scenario, scfg in spec.get("scenarios", {}).items():
        for variable, tcfg in scfg.get("targets", {}).items():
            refs = tcfg.get("source", []) or []
            rows.append({
                "scenario": scenario,
                "variable": variable,
                "low": (tcfg.get("range") or [None, None])[0],
                "high": (tcfg.get("range") or [None, None])[1],
                "sources": ";".join(refs),
                "missing_sources": ";".join([r for r in refs if r not in known]),
            })
    return pd.DataFrame(rows)


def evaluate(spec: Dict[str, Any], dt: float, selected: Iterable[str] | None = None) -> pd.DataFrame:
    selected_set = set(selected or [])
    rows: List[Dict[str, Any]] = []
    for scenario, scfg in spec.get("scenarios", {}).items():
        if selected_set and scenario not in selected_set:
            continue
        try:
            _config, df = run_scenario(scenario, dt=dt, quiet=True)
            run_error = ""
        except Exception as exc:  # pragma: no cover - recorded in output
            df = pd.DataFrame()
            run_error = repr(exc)
        for variable, tcfg in scfg.get("targets", {}).items():
            low, high = [float(x) for x in tcfg.get("range", [float("nan"), float("nan")])]
            value = extract_value(df, variable)
            has_value = not math.isnan(value)
            passed = bool((not run_error) and has_value and low <= value <= high)
            rows.append({
                "scenario": scenario,
                "variable": variable,
                "value": value,
                "low": low,
                "high": high,
                "status": "PASS" if passed else ("NO_DATA" if not has_value else "REVIEW"),
                "pass": passed,
                "pct_deviation": pct_deviation(value, low, high),
                "sources": ";".join(tcfg.get("source", []) or []),
                "run_error": run_error,
            })
    return pd.DataFrame(rows)


def write_markdown(path: Path, spec: Dict[str, Any], source_matrix: pd.DataFrame, eval_df: pd.DataFrame | None) -> None:
    lines = [
        "# Step 5.0A — Literature Benchmark Engine Report",
        "",
        "Scope: physiological plausibility benchmarking for the PDT v3.1 alpha simulator.",
        "",
        "This is **not** external clinical validation and **not** medical decision support.",
        "It is a regression and plausibility gate before the larger 5.0 validation pack.",
        "",
        f"Spec version: **{spec.get('version', '')}**",
        "",
        "## Benchmarked scenarios",
        "",
    ]
    for scenario, scfg in spec.get("scenarios", {}).items():
        lines.append(f"- **{scenario}** — {scfg.get('description', '')}")
    lines += ["", "## Source traceability", "", "| Scenario | Variable | Range | Sources | Missing sources |", "|---|---|---:|---|---|"]
    for _, r in source_matrix.iterrows():
        lines.append(f"| {r['scenario']} | {r['variable']} | {r['low']}–{r['high']} | {r['sources']} | {r['missing_sources']} |")
    if eval_df is not None:
        total = int(len(eval_df))
        passed = int(eval_df["pass"].sum()) if total else 0
        review = int((eval_df["status"] == "REVIEW").sum()) if total else 0
        no_data = int((eval_df["status"] == "NO_DATA").sum()) if total else 0
        lines += [
            "", "## Evaluation", "",
            f"Checks passed: **{passed}/{total}**. Review: **{review}**. No data: **{no_data}**.", "",
            "| Scenario | Variable | Value | Target | Deviation % | Status |",
            "|---|---|---:|---:|---:|---|",
        ]
        for _, r in eval_df.iterrows():
            value = "nan" if pd.isna(r["value"]) else f"{float(r['value']):.4g}"
            dev = "nan" if pd.isna(r["pct_deviation"]) else f"{float(r['pct_deviation']):.2f}"
            lines.append(f"| {r['scenario']} | {r['variable']} | {value} | {r['low']:.4g}–{r['high']:.4g} | {dev} | {r['status']} |")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default=str(ROOT / "data" / "literature_benchmark_targets_v5.0A.yaml"))
    ap.add_argument("--outdir", default=str(ROOT / "outputs" / "literature_benchmark_v5.0A"))
    ap.add_argument("--dt", type=float, default=10.0)
    ap.add_argument("--scenarios", nargs="*", default=None)
    ap.add_argument("--no-run", action="store_true")
    ap.add_argument("--fail-on-review", action="store_true")
    args = ap.parse_args()

    spec = load_spec(Path(args.spec))
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    matrix = build_source_matrix(spec)
    matrix.to_csv(outdir / "literature_benchmark_source_matrix_v50A.csv", index=False)
    eval_df = None if args.no_run else evaluate(spec, dt=args.dt, selected=args.scenarios)
    if eval_df is not None:
        eval_df.to_csv(outdir / "literature_benchmark_results_v50A.csv", index=False)
    write_markdown(outdir / "literature_benchmark_report_v50A.md", spec, matrix, eval_df)

    missing = int((matrix["missing_sources"].fillna("") != "").sum()) if not matrix.empty else 0
    summary = {
        "release_step": "5.0A",
        "spec": Path(args.spec).name,
        "benchmark_scenarios": len(spec.get("scenarios", {})),
        "target_rows": int(len(matrix)),
        "missing_source_rows": missing,
        "evaluated_checks": int(len(eval_df)) if eval_df is not None else 0,
        "pass": int(eval_df["pass"].sum()) if eval_df is not None and not eval_df.empty else 0,
        "review": int((eval_df["status"] == "REVIEW").sum()) if eval_df is not None and not eval_df.empty else 0,
        "no_data": int((eval_df["status"] == "NO_DATA").sum()) if eval_df is not None and not eval_df.empty else 0,
    }
    write_json(summary, outdir / "literature_benchmark_summary_v50A.json")
    print(json.dumps(summary, indent=2))
    if args.fail_on_review and (summary["review"] or summary["no_data"] or summary["missing_source_rows"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
