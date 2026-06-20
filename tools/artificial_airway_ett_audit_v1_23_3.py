#!/usr/bin/env python3
"""Audit artificial-airway ETT/tracheostomy scaffold v1.23.3."""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = [
    "scenarios/airway_ett_tube_resistance_v1_23_3.yaml",
    "scenarios/airway_ett_partial_obstruction_v1_23_3.yaml",
]
FIELDS = [
    "airway_interface", "intubated", "ventilator_connected",
    "tube_internal_diameter_mm", "tube_resistance_cmH2O_L_s",
    "tube_resistance_factor", "tube_dead_space_mL", "tube_VdVt_add",
    "airway_resistance_mod", "PaCO2", "Vt", "ETT_failure_risk",
    "artificial_airway_revision",
]

def run_scenario(scenario: str, dt: float) -> dict:
    outdir = ROOT / "outputs" / "artificial_airway_v1.23.3"
    outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / (Path(scenario).stem + ".csv")
    cmd = [sys.executable, str(ROOT / "run_simulation.py"), "--scenario", scenario, "--dt", str(dt), "--no-plot", "--save-csv", str(csv_path)]
    subprocess.run(cmd, cwd=str(ROOT), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    df = pd.read_csv(csv_path)
    final = df.iloc[-1].to_dict()
    return {k: final.get(k, None) for k in FIELDS}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dt", type=float, default=10.0)
    ap.add_argument("--fail-on-review", action="store_true")
    args = ap.parse_args()
    rows = []
    for scen in SCENARIOS:
        final = run_scenario(scen, args.dt)
        sid = Path(scen).stem
        def add(check, status, value=None):
            rows.append({"scenario": sid, "check": check, "status": status, "value": value})
        add("intubated", "PASS" if bool(final["intubated"]) else "FAIL", final["intubated"])
        add("interface_ETT", "PASS" if str(final["airway_interface"]).upper() == "ETT" else "FAIL", final["airway_interface"])
        add("revision_1233", "PASS" if int(final["artificial_airway_revision"]) == 1233 else "FAIL", final["artificial_airway_revision"])
        add("tube_resistance_positive", "PASS" if float(final["tube_resistance_cmH2O_L_s"]) > 0 else "FAIL", final["tube_resistance_cmH2O_L_s"])
        add("tube_deadspace_positive", "PASS" if float(final["tube_dead_space_mL"]) > 0 else "FAIL", final["tube_dead_space_mL"])
        add("tube_VdVt_bounded", "PASS" if 0 <= float(final["tube_VdVt_add"]) <= 0.25 else "FAIL", final["tube_VdVt_add"])
        add("failure_risk_bounded", "PASS" if 0 <= float(final["ETT_failure_risk"]) <= 1 else "FAIL", final["ETT_failure_risk"])
        if "partial_obstruction" in sid:
            add("obstructed_resistance_visible", "PASS" if float(final["tube_resistance_factor"]) > 1.5 else "REVIEW", final["tube_resistance_factor"])
    summary = {
        "release": "v1.23.3-alpha",
        "checks": len(rows),
        "pass": sum(r["status"] == "PASS" for r in rows),
        "review": sum(r["status"] == "REVIEW" for r in rows),
        "fail": sum(r["status"] == "FAIL" for r in rows),
        "rows": rows,
    }
    outdir = ROOT / "outputs" / "artificial_airway_v1.23.3"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "artificial_airway_audit_summary_v1233.json").write_text(json.dumps(summary, indent=2))
    pd.DataFrame(rows).to_csv(outdir / "artificial_airway_audit_rows_v1233.csv", index=False)
    print(json.dumps({k: summary[k] for k in ["release","checks","pass","review","fail"]}, indent=2))
    if summary["fail"] or (args.fail_on_review and summary["review"]):
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
