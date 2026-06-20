#!/usr/bin/env python3
"""PDT v0.38 executed dt convergence pack.

Runs dt convergence scenario-by-scenario and writes an auditable report. This
wrapper is intentionally conservative: it records failures rather than hiding
or auto-relaxing tolerances. Use --plan standard for a fast all-core screen,
--plan fine for dt=1/0.5/0.2, and --plan full for dt=1/0.5/0.2/0.1.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.dt_convergence_hard import load_specs, run_dt_convergence  # noqa: E402
from tools.simtools import write_json  # noqa: E402

SPEC_PATH = ROOT / "data" / "dt_convergence_specs_v0.38.yaml"


def _get_plan_dts(specs: Dict[str, Any], plan: str) -> list[float]:
    key = {"standard": "standard_dts", "fine": "fine_dts", "full": "full_dts"}[plan]
    return [float(x) for x in specs[key]]


def _scenario_names(specs: Dict[str, Any], include_extended: bool) -> list[str]:
    out = []
    for name, s in specs["scenarios"].items():
        if include_extended or s.get("priority") == "core":
            out.append(name)
    return out


def classify_recommendation(checks: pd.DataFrame) -> dict[str, Any]:
    if checks.empty:
        return {"status": "no_checks", "recommended_max_dt": None, "primary_failed": 0, "secondary_failed": 0}
    primary_failed = int(((checks["tier"] == "primary") & (~checks["pass"].astype(bool))).sum())
    secondary_failed = int(((checks["tier"] == "secondary") & (~checks["pass"].astype(bool))).sum())
    if primary_failed == 0 and secondary_failed == 0:
        status = "pass"
    elif primary_failed == 0:
        status = "secondary_review"
    else:
        status = "primary_review"
    # Recommend the largest dt that has no primary failures among its checks.
    recommended = None
    for dt in sorted(checks["dt"].dropna().unique(), reverse=True):
        sub = checks[checks["dt"] == dt]
        if int(((sub["tier"] == "primary") & (~sub["pass"].astype(bool))).sum()) == 0:
            recommended = float(dt)
            break
    return {
        "status": status,
        "recommended_max_dt": recommended,
        "primary_failed": primary_failed,
        "secondary_failed": secondary_failed,
    }


def run_pack(scenarios: Iterable[str], dts: Iterable[float], spec_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    all_summaries = []
    all_checks = []
    per_scenario = []
    for scenario in scenarios:
        summaries, checks, meta = run_dt_convergence([scenario], dts, spec_path, quiet=True)
        rec = classify_recommendation(checks)
        per_scenario.append({
            "scenario": scenario,
            "checks": int(meta.get("checks", 0)),
            "passed": int(meta.get("passed", 0)),
            "failed": int(meta.get("failed", 0)),
            **rec,
        })
        all_summaries.append(summaries)
        all_checks.append(checks)
    summaries_df = pd.concat(all_summaries, ignore_index=True) if all_summaries else pd.DataFrame()
    checks_df = pd.concat(all_checks, ignore_index=True) if all_checks else pd.DataFrame()
    scenario_df = pd.DataFrame(per_scenario)
    metadata = {
        "version": "v0.38",
        "scenarios": list(scenarios),
        "dts": [float(x) for x in dts],
        "reference_dt": min([float(x) for x in dts]),
        "scenario_count": len(per_scenario),
        "checks": int(len(checks_df)),
        "passed": int(checks_df["pass"].sum()) if len(checks_df) else 0,
        "failed": int((~checks_df["pass"].astype(bool)).sum()) if len(checks_df) else 0,
        "primary_failed": int(((checks_df.get("tier") == "primary") & (~checks_df.get("pass").astype(bool))).sum()) if len(checks_df) else 0,
        "secondary_failed": int(((checks_df.get("tier") == "secondary") & (~checks_df.get("pass").astype(bool))).sum()) if len(checks_df) else 0,
        "status_counts": scenario_df["status"].value_counts().to_dict() if len(scenario_df) else {},
    }
    return summaries_df, checks_df, scenario_df, metadata


def write_report(checks: pd.DataFrame, scenario_df: pd.DataFrame, metadata: Dict[str, Any], path: Path) -> None:
    lines = [
        "# PDT v0.38 full dt convergence pack",
        "",
        "This report is an internal numerical convergence screen, not clinical validation.",
        "Failures are intentionally reported, not hidden. A primary failure means that the coarser dt should not be used for that scenario/metric without review.",
        "",
        f"Scenarios: {metadata['scenario_count']}",
        f"dt values: `{metadata['dts']}`; reference dt: `{metadata['reference_dt']}`",
        f"Checks: {metadata['checks']} | Passed: {metadata['passed']} | Failed: {metadata['failed']}",
        f"Primary failures: {metadata['primary_failed']} | Secondary failures: {metadata['secondary_failed']}",
        "",
        "## Per-scenario recommendation",
        "",
        scenario_df.to_markdown(index=False) if len(scenario_df) else "No scenarios executed.",
        "",
    ]
    failed = checks[~checks["pass"].astype(bool)].copy() if len(checks) else pd.DataFrame()
    if len(failed):
        cols = ["scenario", "dt", "metric", "tier", "value", "reference", "abs_error", "rel_error", "abs_tol", "rel_tol", "status"]
        lines += ["## Failed checks", "", failed[[c for c in cols if c in failed.columns]].to_markdown(index=False), ""]
    else:
        lines += ["## Failed checks", "", "No failed checks.", ""]
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", choices=["standard", "fine", "full"], default="standard")
    ap.add_argument("--scenarios", nargs="+", default=None)
    ap.add_argument("--include-extended", action="store_true")
    ap.add_argument("--outdir", default=str(ROOT / "outputs" / "validation_pack"))
    ap.add_argument("--fail-on-primary", action="store_true")
    args = ap.parse_args()
    specs = load_specs(SPEC_PATH)
    dts = _get_plan_dts(specs, args.plan)
    scenarios = args.scenarios or _scenario_names(specs, args.include_extended)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    summaries, checks, scenario_df, metadata = run_pack(scenarios, dts, SPEC_PATH)
    prefix = f"dt_convergence_v038_{args.plan}"
    summaries.to_csv(outdir / f"{prefix}_summaries.csv", index=False)
    checks.to_csv(outdir / f"{prefix}_checks.csv", index=False)
    scenario_df.to_csv(outdir / f"{prefix}_scenario_recommendations.csv", index=False)
    write_json(metadata, outdir / f"{prefix}_summary.json")
    write_report(checks, scenario_df, metadata, outdir / f"{prefix}_report.md")
    print(json.dumps(metadata, indent=2))
    if args.fail_on_primary and int(metadata.get("primary_failed", 0)) > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
