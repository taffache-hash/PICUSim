#!/usr/bin/env python3
"""Audit v1.24 airway intubation/extubation event system."""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = [
    "scenarios/airway_rsi_hypoxic_child_v1_24.yaml",
    "scenarios/airway_accidental_extubation_picu_v1_24.yaml",
]


def run_scenario(path: str, dt: float, out: Path) -> pd.DataFrame:
    cmd = [sys.executable, str(ROOT / "run_simulation.py"), "--scenario", path, "--dt", str(dt), "--no-plot", "--save-csv", str(out)]
    subprocess.run(cmd, cwd=ROOT, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return pd.read_csv(out)


def evaluate(df: pd.DataFrame, scenario: str) -> list[dict]:
    rows=[]
    final=df.iloc[-1]
    def add(check, ok, value=None): rows.append({"scenario":scenario,"check":check,"status":"PASS" if ok else "FAIL","value":value})
    add("airway_event_revision_present", "airway_event_revision" in df.columns and df["airway_event_revision"].max() >= 1240, float(df["airway_event_revision"].max()) if "airway_event_revision" in df else None)
    add("event_type_non_none", "airway_event_type" in df.columns and str(final.get("airway_event_type", "none")) != "none", str(final.get("airway_event_type", "none")))
    add("final_intubated", bool(final.get("intubated", False)) is True, bool(final.get("intubated", False)))
    add("final_interface_ETT", str(final.get("airway_interface", "")) == "ETT", str(final.get("airway_interface", "")))
    add("success_time_recorded", float(final.get("intubation_success_time_s", -1)) > 0, float(final.get("intubation_success_time_s", -1)))
    add("ventilator_connected_final", bool(final.get("ventilator_connected", False)) is True, bool(final.get("ventilator_connected", False)))
    if "rsi" in scenario:
        add("failed_attempt_recorded", int(final.get("failed_intubation_count", 0)) >= 1, int(final.get("failed_intubation_count", 0)))
        add("bag_mask_phase_present", "bag_mask_ventilation_active" in df.columns and df["bag_mask_ventilation_active"].astype(str).str.lower().isin(["true","1"]).any(), None)
    if "accidental_extubation" in scenario:
        add("extubation_time_recorded", float(final.get("extubation_time_s", -1)) > 0, float(final.get("extubation_time_s", -1)))
        add("at_risk_phase_present", "airway_rescue_state" in df.columns and (df["airway_rescue_state"].astype(str) == "at_risk").any(), None)
    return rows


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--dt", type=float, default=10.0)
    ap.add_argument("--fail-on-review", action="store_true")
    args=ap.parse_args()
    outdir=ROOT/"outputs"/"airway_events_v1.24"
    outdir.mkdir(parents=True, exist_ok=True)
    all_rows=[]
    for scen in SCENARIOS:
        outcsv=outdir/(Path(scen).stem+"_timeseries.csv")
        df=run_scenario(scen,args.dt,outcsv)
        all_rows.extend(evaluate(df,Path(scen).stem))
    pd.DataFrame(all_rows).to_csv(outdir/"airway_event_audit_v124.csv", index=False)
    summary={
        "release":"v1.24-alpha",
        "scenario_count":len(SCENARIOS),
        "checks":len(all_rows),
        "pass":sum(r["status"]=="PASS" for r in all_rows),
        "fail":sum(r["status"]=="FAIL" for r in all_rows),
        "status":"PASS" if all(r["status"]=="PASS" for r in all_rows) else "FAIL",
    }
    (outdir/"airway_event_audit_summary_v124.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    if args.fail_on_review and summary["fail"]:
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
