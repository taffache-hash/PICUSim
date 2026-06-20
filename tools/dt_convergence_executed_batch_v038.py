#!/usr/bin/env python3
"""Executed dt convergence batch runner for v0.38.

Runs the existing strict convergence tool scenario-by-scenario in isolated
subprocesses, copies each scenario result, and aggregates the completed runs.
This avoids a single long run hanging the entire validation pack.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "data" / "dt_convergence_specs_v0.38.yaml"


def load_specs() -> dict[str, Any]:
    return yaml.safe_load(SPEC.read_text())


def plan_dts(specs: dict[str, Any], plan: str) -> list[str]:
    return [str(x) for x in specs[{"standard":"standard_dts","fine":"fine_dts","full":"full_dts"}[plan]]]


def scenario_names(specs: dict[str, Any], include_extended: bool) -> list[str]:
    return [k for k, v in specs["scenarios"].items() if include_extended or v.get("priority") == "core"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", choices=["standard", "fine", "full"], default="standard")
    ap.add_argument("--scenarios", nargs="+", default=None)
    ap.add_argument("--include-extended", action="store_true")
    ap.add_argument("--timeout-per-scenario", type=int, default=180)
    ap.add_argument("--outdir", default=str(ROOT / "outputs" / "validation_pack"))
    args = ap.parse_args()
    specs = load_specs()
    scenarios = args.scenarios or scenario_names(specs, args.include_extended)
    dts = plan_dts(specs, args.plan)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    tmpdir = outdir / f"dt_convergence_v038_{args.plan}_scenario_runs"
    tmpdir.mkdir(parents=True, exist_ok=True)

    scenario_rows = []
    all_checks = []
    all_summaries = []
    for scenario in scenarios:
        cmd = [sys.executable, str(ROOT / "tools" / "dt_convergence_hard.py"), "--scenarios", scenario, "--dts", *dts]
        status = "completed"
        timed_out = False
        try:
            proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=args.timeout_per_scenario)
            returncode = proc.returncode
        except subprocess.TimeoutExpired as e:
            status = "timeout_after_output"
            timed_out = True
            returncode = 124
        # The called tool writes canonical files even if primary checks fail.
        checks_path = outdir / "dt_convergence_hard_checks.csv"
        summaries_path = outdir / "dt_convergence_hard_summaries.csv"
        meta_path = outdir / "dt_convergence_hard_summary.json"
        checks = pd.read_csv(checks_path) if checks_path.exists() else pd.DataFrame()
        summaries = pd.read_csv(summaries_path) if summaries_path.exists() else pd.DataFrame()
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        if len(checks):
            checks.to_csv(tmpdir / f"{scenario}_checks.csv", index=False)
            all_checks.append(checks)
        if len(summaries):
            summaries.to_csv(tmpdir / f"{scenario}_summaries.csv", index=False)
            all_summaries.append(summaries)
        primary_failed = int(meta.get("primary_failed", 0))
        secondary_failed = int(meta.get("secondary_failed", 0))
        if primary_failed:
            result_status = "primary_review"
        elif secondary_failed:
            result_status = "secondary_review"
        elif int(meta.get("checks", 0)) > 0:
            result_status = "pass"
        else:
            result_status = "no_result"
        scenario_rows.append({
            "scenario": scenario,
            "run_status": status,
            "timed_out": timed_out,
            "returncode": returncode,
            "result_status": result_status,
            "checks": int(meta.get("checks", 0)),
            "passed": int(meta.get("passed", 0)),
            "failed": int(meta.get("failed", 0)),
            "primary_failed": primary_failed,
            "secondary_failed": secondary_failed,
        })

    checks_df = pd.concat(all_checks, ignore_index=True) if all_checks else pd.DataFrame()
    summaries_df = pd.concat(all_summaries, ignore_index=True) if all_summaries else pd.DataFrame()
    scen_df = pd.DataFrame(scenario_rows)
    prefix = f"dt_convergence_v038_{args.plan}_executed"
    checks_df.to_csv(outdir / f"{prefix}_checks.csv", index=False)
    summaries_df.to_csv(outdir / f"{prefix}_summaries.csv", index=False)
    scen_df.to_csv(outdir / f"{prefix}_scenario_status.csv", index=False)
    metadata = {
        "version": "v0.38",
        "plan": args.plan,
        "dts": [float(x) for x in dts],
        "scenarios": scenarios,
        "scenario_count": len(scenarios),
        "checks": int(len(checks_df)),
        "passed": int(checks_df["pass"].sum()) if len(checks_df) and "pass" in checks_df else 0,
        "failed": int((~checks_df["pass"].astype(bool)).sum()) if len(checks_df) and "pass" in checks_df else 0,
        "primary_failed": int(((checks_df.get("tier") == "primary") & (~checks_df.get("pass").astype(bool))).sum()) if len(checks_df) else 0,
        "secondary_failed": int(((checks_df.get("tier") == "secondary") & (~checks_df.get("pass").astype(bool))).sum()) if len(checks_df) else 0,
        "result_status_counts": scen_df["result_status"].value_counts().to_dict() if len(scen_df) else {},
    }
    (outdir / f"{prefix}_summary.json").write_text(json.dumps(metadata, indent=2))
    lines = [
        "# PDT v0.38 executed dt convergence batch",
        "",
        "This is an executed numerical convergence screen. It is not clinical validation.",
        "Primary failures are deliberately retained as review signals.",
        "",
        f"Plan: `{args.plan}`; dt values: `{metadata['dts']}`",
        f"Scenarios: {metadata['scenario_count']}",
        f"Checks: {metadata['checks']} | Passed: {metadata['passed']} | Failed: {metadata['failed']}",
        f"Primary failures: {metadata['primary_failed']} | Secondary failures: {metadata['secondary_failed']}",
        "",
        "## Scenario status",
        "",
        scen_df.to_markdown(index=False),
        "",
    ]
    if len(checks_df) and int(metadata["failed"]):
        failed = checks_df[~checks_df["pass"].astype(bool)]
        cols = ["scenario", "dt", "metric", "tier", "value", "reference", "abs_error", "rel_error", "abs_tol", "rel_tol", "status"]
        lines += ["## Failed checks", "", failed[[c for c in cols if c in failed.columns]].to_markdown(index=False), ""]
    (outdir / f"{prefix}_report.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(metadata, indent=2))
    # Do not fail the batch: the purpose is to expose failures.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
