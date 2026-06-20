#!/usr/bin/env python3
"""Stricter dt convergence screening for PDT v0.33.

This tool compares scenario summaries at several dt values against the finest
available dt. It reports primary vs secondary variables separately and supports
absolute tolerances for variables such as pH or ICP where relative error is not
clinically meaningful.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.simtools import run_scenario, summarize_dataframe, write_json  # noqa: E402

SPEC_PATH = ROOT / "data" / "dt_convergence_specs_v0.33.yaml"


def load_specs(path: str | Path = SPEC_PATH) -> Dict[str, Any]:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def _as_float(x: Any) -> float | None:
    try:
        if x is None:
            return None
        v = float(x)
        if v != v:  # NaN
            return None
        return v
    except Exception:
        return None


def metric_error(value: float, reference: float, rule: Mapping[str, Any]) -> Dict[str, float | bool | str]:
    """Return error metrics and pass/fail for one value.

    If abs_tol is supplied, absolute error must pass. If rel_tol is supplied,
    relative error must pass. If both are supplied, passing either tolerance is
    acceptable; this avoids over-penalising values near zero while still keeping
    a clinically meaningful absolute bound.
    """
    abs_err = abs(value - reference)
    denom = max(abs(reference), 1e-9)
    rel_err = abs_err / denom
    abs_tol = rule.get("abs_tol")
    rel_tol = rule.get("rel_tol")
    abs_pass = True if abs_tol is None else abs_err <= float(abs_tol)
    rel_pass = True if rel_tol is None else rel_err <= float(rel_tol)
    if abs_tol is not None and rel_tol is not None:
        passed = bool(abs_pass or rel_pass)
        criterion = "abs_or_rel"
    elif abs_tol is not None:
        passed = bool(abs_pass)
        criterion = "abs"
    else:
        passed = bool(rel_pass)
        criterion = "rel"
    return {
        "abs_error": float(abs_err),
        "rel_error": float(rel_err),
        "abs_tol": None if abs_tol is None else float(abs_tol),
        "rel_tol": None if rel_tol is None else float(rel_tol),
        "criterion": criterion,
        "pass": passed,
    }


def _metric_rules(specs: Mapping[str, Any], scenario: str) -> Dict[str, Dict[str, Any]]:
    s = specs["scenarios"][scenario]
    rules: Dict[str, Dict[str, Any]] = {}
    for tier in ("primary", "secondary"):
        for metric, rule in s.get(tier, {}).items():
            r = dict(rule or {})
            r["tier"] = tier
            if "rel_tol" not in r and "abs_tol" not in r:
                r["rel_tol"] = specs["default_primary_rel_tol"] if tier == "primary" else specs["default_secondary_rel_tol"]
            rules[metric] = r
    return rules


def run_dt_convergence(
    scenarios: Iterable[str] | None = None,
    dts: Iterable[float] | None = None,
    spec_path: str | Path = SPEC_PATH,
    quiet: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    specs = load_specs(spec_path)
    scenario_names = list(scenarios) if scenarios else list(specs["scenarios"].keys())
    dt_values = sorted([float(x) for x in (dts if dts else specs.get("recommended_dts", [1.0, 0.5, 0.2, 0.1]))], reverse=True)
    ref_dt = min(dt_values)

    summary_rows: list[dict[str, Any]] = []
    check_rows: list[dict[str, Any]] = []
    for scenario in scenario_names:
        summaries: Dict[float, Dict[str, Any]] = {}
        for dt in dt_values:
            _, df = run_scenario(scenario, dt=dt, quiet=quiet)
            summ = summarize_dataframe(df)
            summaries[dt] = summ
            summary_rows.append({"scenario": scenario, "dt": dt, **summ})

        ref = summaries[ref_dt]
        rules = _metric_rules(specs, scenario)
        for dt in dt_values:
            if dt == ref_dt:
                continue
            for metric, rule in rules.items():
                value = _as_float(summaries[dt].get(metric))
                reference = _as_float(ref.get(metric))
                if value is None or reference is None:
                    check_rows.append({
                        "scenario": scenario,
                        "dt": dt,
                        "reference_dt": ref_dt,
                        "metric": metric,
                        "tier": rule.get("tier"),
                        "value": value,
                        "reference": reference,
                        "pass": False,
                        "status": "missing_metric",
                    })
                    continue
                e = metric_error(value, reference, rule)
                check_rows.append({
                    "scenario": scenario,
                    "dt": dt,
                    "reference_dt": ref_dt,
                    "metric": metric,
                    "tier": rule.get("tier"),
                    "value": value,
                    "reference": reference,
                    "status": "pass" if e["pass"] else "fail",
                    **e,
                })

    summaries_df = pd.DataFrame(summary_rows)
    checks_df = pd.DataFrame(check_rows)
    metadata = {
        "version": specs.get("version", "v0.33"),
        "reference_dt": ref_dt,
        "dts": dt_values,
        "scenarios": scenario_names,
        "checks": int(len(checks_df)),
        "passed": int(checks_df["pass"].sum()) if len(checks_df) and "pass" in checks_df else 0,
        "failed": int((~checks_df["pass"].astype(bool)).sum()) if len(checks_df) and "pass" in checks_df else 0,
        "primary_failed": int(((checks_df.get("tier") == "primary") & (~checks_df.get("pass").astype(bool))).sum()) if len(checks_df) else 0,
        "secondary_failed": int(((checks_df.get("tier") == "secondary") & (~checks_df.get("pass").astype(bool))).sum()) if len(checks_df) else 0,
    }
    return summaries_df, checks_df, metadata


def write_markdown(checks: pd.DataFrame, metadata: Mapping[str, Any], path: Path) -> None:
    lines = [
        "# PDT v0.33 dt convergence report",
        "",
        "This is an internal numerical stability screen, not clinical validation.",
        "The finest dt in the run is treated as the reference.",
        "",
        f"Reference dt: `{metadata.get('reference_dt')}`",
        f"Scenarios: `{', '.join(metadata.get('scenarios', []))}`",
        f"Checks: {metadata.get('checks')} | Passed: {metadata.get('passed')} | Failed: {metadata.get('failed')}",
        f"Primary failures: {metadata.get('primary_failed')} | Secondary failures: {metadata.get('secondary_failed')}",
        "",
    ]
    if len(checks) and int(metadata.get("failed", 0)):
        failed = checks[~checks["pass"].astype(bool)].copy()
        lines += ["## Failed checks", ""]
        cols = ["scenario", "dt", "metric", "tier", "value", "reference", "abs_error", "rel_error", "abs_tol", "rel_tol", "status"]
        lines.append(failed[[c for c in cols if c in failed.columns]].to_markdown(index=False))
    else:
        lines += ["## Result", "", "All configured checks passed."]
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", nargs="+", default=None)
    ap.add_argument("--dts", nargs="+", type=float, default=None)
    ap.add_argument("--quick", action="store_true", help="Use quick dt values from the spec instead of full recommended dts.")
    ap.add_argument("--spec", default=str(SPEC_PATH))
    ap.add_argument("--outdir", default=str(ROOT / "outputs" / "validation_pack"))
    ap.add_argument("--fail-on-primary", action="store_true", help="Exit non-zero if any primary convergence check fails.")
    args = ap.parse_args()

    specs = load_specs(args.spec)
    dts = args.dts
    if dts is None and args.quick:
        dts = specs.get("quick_dts", [1.0, 0.5, 0.2])

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    summaries, checks, metadata = run_dt_convergence(args.scenarios, dts, args.spec)
    summaries.to_csv(outdir / "dt_convergence_hard_summaries.csv", index=False)
    checks.to_csv(outdir / "dt_convergence_hard_checks.csv", index=False)
    write_json(metadata, outdir / "dt_convergence_hard_summary.json")
    write_markdown(checks, metadata, outdir / "dt_convergence_hard_report.md")
    print(f"dt convergence hard report written to {outdir}")
    print(metadata)
    if args.fail_on_primary and int(metadata.get("primary_failed", 0)) > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
