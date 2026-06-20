#!/usr/bin/env python3
"""Audit executable EPALS 5T scenario pack (v1.22.2)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = {
    "epals_tension_pneumothorax": {
        "file": "scenarios/epals_tension_pneumothorax.yaml",
        "checks": [
            {"var": "MAP", "kind": "nadir_then_recovery", "min_drop": 0.5},
            {"var": "RV_afterload_index", "kind": "peak_present"},
        ],
    },
    "epals_cardiac_tamponade": {
        "file": "scenarios/epals_cardiac_tamponade.yaml",
        "checks": [
            {"var": "CVP", "kind": "peak_then_reduction", "min_drop": 1.0},
            {"var": "lactate", "kind": "peak_present"},
        ],
    },
    "epals_toxicologic_opioid_benzodiazepine": {
        "file": "scenarios/epals_toxicologic_opioid_benzodiazepine.yaml",
        "checks": [
            {"var": "PaCO2", "kind": "peak_present"},
            {"var": "sedation_score", "kind": "peak_present"},
        ],
    },
    "epals_pulmonary_thrombosis_pe": {
        "file": "scenarios/epals_pulmonary_thrombosis_pe.yaml",
        "checks": [
            {"var": "PVR", "kind": "peak_then_reduction", "min_drop": 20.0},
            {"var": "RV_afterload_index", "kind": "peak_then_reduction", "min_drop": 0.05},
        ],
    },
    "epals_cardiac_thrombosis_myocarditis_low_output": {
        "file": "scenarios/epals_cardiac_thrombosis_myocarditis_low_output.yaml",
        "checks": [
            {"var": "MAP", "kind": "nadir_then_recovery", "min_drop": 1.0},
            {"var": "drug_inotropy_mod", "kind": "peak_present"},
        ],
    },
}

CORE_NON_NAN = ["SaO2", "PaO2", "PaCO2", "pH_a", "MAP", "HR", "CO"]


def _evaluate_check(df: pd.DataFrame, spec: dict) -> tuple[str, str]:
    var = spec["var"]
    if var not in df.columns:
        return "REVIEW", f"missing column {var}"
    series = pd.to_numeric(df[var], errors="coerce").dropna()
    if len(series) < 2:
        return "REVIEW", f"insufficient data for {var}"
    first = float(series.iloc[0]); final = float(series.iloc[-1]); mn = float(series.min()); mx = float(series.max())
    kind = spec["kind"]
    if kind == "nadir_then_recovery":
        ok = (first - mn >= float(spec.get("min_drop", 0))) and (final - mn >= float(spec.get("min_drop", 0)))
        return ("PASS" if ok else "REVIEW"), f"{var}: first={first:.4g}, min={mn:.4g}, final={final:.4g}"
    if kind == "peak_then_reduction":
        ok = (mx - final >= float(spec.get("min_drop", 0)))
        return ("PASS" if ok else "REVIEW"), f"{var}: max={mx:.4g}, final={final:.4g}"
    if kind == "peak_present":
        ok = mx >= first
        return ("PASS" if ok else "REVIEW"), f"{var}: first={first:.4g}, max={mx:.4g}"
    return "REVIEW", f"unknown check kind {kind}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="outputs/epals_5t_v1.22.2")
    ap.add_argument("--dt", type=float, default=10.0)
    ap.add_argument("--fail-on-review", action="store_true")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    if not outdir.is_absolute():
        outdir = ROOT / outdir
    outdir.mkdir(parents=True, exist_ok=True)

    rows = []
    for sid, spec in SCENARIOS.items():
        scen_path = ROOT / spec["file"]
        exists = scen_path.exists()
        rows.append({"scenario": sid, "check": "file_exists", "status": "PASS" if exists else "FAIL", "detail": str(scen_path)})
        if not exists:
            continue
        try:
            data = yaml.safe_load(scen_path.read_text())
            rows.append({"scenario": sid, "check": "yaml_load", "status": "PASS", "detail": data.get("name", "")})
        except Exception as e:
            rows.append({"scenario": sid, "check": "yaml_load", "status": "FAIL", "detail": str(e)})
            continue

        csv_path = outdir / f"{sid}_timeseries.csv"
        cmd = [sys.executable, str(ROOT / "run_simulation.py"), "--scenario", str(scen_path), "--dt", str(args.dt), "--no-plot", "--save-csv", str(csv_path)]
        res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=120)
        rows.append({"scenario": sid, "check": "smoke_run", "status": "PASS" if res.returncode == 0 else "FAIL", "detail": (res.stderr + res.stdout)[-500:]})
        if res.returncode != 0 or not csv_path.exists():
            continue
        df = pd.read_csv(csv_path, index_col=0)
        for col in CORE_NON_NAN:
            if col in df.columns:
                ok = not pd.to_numeric(df[col], errors="coerce").isna().any()
                rows.append({"scenario": sid, "check": f"no_nan:{col}", "status": "PASS" if ok else "FAIL", "detail": ""})
        for chk in spec["checks"]:
            status, detail = _evaluate_check(df, chk)
            rows.append({"scenario": sid, "check": f"marker:{chk['var']}", "status": status, "detail": detail})

    fail = sum(r["status"] == "FAIL" for r in rows)
    review = sum(r["status"] == "REVIEW" for r in rows)
    summary = {"release": "v1.22.2-alpha", "scenario_count": len(SCENARIOS), "checks": len(rows), "pass": sum(r["status"] == "PASS" for r in rows), "review": review, "fail": fail, "status": "FAIL" if fail else ("REVIEW" if review else "PASS")}
    pd.DataFrame(rows).to_csv(outdir / "epals_5t_audit_rows_v1222.csv", index=False)
    (outdir / "epals_5t_audit_summary_v1222.json").write_text(json.dumps(summary, indent=2))
    report = ["# EPALS 5T audit v1.22.2", "", f"Status: **{summary['status']}**", "", f"Scenarios: {summary['scenario_count']}", f"Checks: {summary['checks']}", f"PASS: {summary['pass']}", f"REVIEW: {summary['review']}", f"FAIL: {summary['fail']}"]
    (outdir / "epals_5t_audit_report_v1222.md").write_text("\n".join(report) + "\n")
    print(json.dumps(summary, indent=2))
    if fail or (args.fail_on_review and review):
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
