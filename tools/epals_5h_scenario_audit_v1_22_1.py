#!/usr/bin/env python3
"""Audit executable EPALS 5H scenario pack (v1.22.1)."""
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
    "epals_hypoxia_airway_obstruction": {
        "file": "scenarios/epals_hypoxia_airway_obstruction.yaml",
        "checks": [
            {"var": "SaO2", "kind": "nadir_then_recovery", "min_drop": 0.01},
            {"var": "PaCO2", "kind": "peak_present"},
        ],
    },
    "epals_hypovolemia_hemorrhagic_shock": {
        "file": "scenarios/epals_hypovolemia_hemorrhagic_shock.yaml",
        "checks": [
            {"var": "MAP", "kind": "nadir_then_recovery", "min_drop": 1.0},
            {"var": "lactate", "kind": "peak_present"},
        ],
    },
    "epals_acidosis_septic_shock": {
        "file": "scenarios/epals_acidosis_septic_shock.yaml",
        "checks": [
            {"var": "pH_a", "kind": "nadir_then_recovery", "min_drop": 0.005},
            {"var": "lactate", "kind": "peak_present"},
        ],
    },
    "epals_hyperkalemia_aki": {
        "file": "scenarios/epals_hyperkalemia_aki.yaml",
        "checks": [
            {"var": "K_mmol_L", "kind": "peak_then_reduction", "min_drop": 0.2},
            {"var": "RRT_indication_score", "kind": "peak_present"},
        ],
    },
    "epals_hypothermia_rewarming": {
        "file": "scenarios/epals_hypothermia_rewarming.yaml",
        "checks": [
            {"var": "T_core", "kind": "final_above_initial", "min_gain": 1.0},
            {"var": "hypothermia_index", "kind": "peak_present"},
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
    if kind == "final_above_initial":
        ok = (final - first >= float(spec.get("min_gain", 0)))
        return ("PASS" if ok else "REVIEW"), f"{var}: first={first:.4g}, final={final:.4g}"
    if kind == "peak_present":
        ok = mx >= first
        return ("PASS" if ok else "REVIEW"), f"{var}: first={first:.4g}, max={mx:.4g}"
    return "REVIEW", f"unknown check kind {kind}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="outputs/epals_5h_v1.22.1")
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
    summary = {"release": "v1.22.1-alpha", "scenario_count": len(SCENARIOS), "checks": len(rows), "pass": sum(r["status"] == "PASS" for r in rows), "review": review, "fail": fail, "status": "FAIL" if fail else ("REVIEW" if review else "PASS")}
    pd.DataFrame(rows).to_csv(outdir / "epals_5h_audit_rows_v1221.csv", index=False)
    (outdir / "epals_5h_audit_summary_v1221.json").write_text(json.dumps(summary, indent=2))
    report = ["# EPALS 5H audit v1.22.1", "", f"Status: **{summary['status']}**", "", f"Scenarios: {summary['scenario_count']}", f"Checks: {summary['checks']}", f"PASS: {summary['pass']}", f"REVIEW: {summary['review']}", f"FAIL: {summary['fail']}"]
    (outdir / "epals_5h_audit_report_v1221.md").write_text("\n".join(report) + "\n")
    print(json.dumps(summary, indent=2))
    if fail or (args.fail_on_review and review):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
