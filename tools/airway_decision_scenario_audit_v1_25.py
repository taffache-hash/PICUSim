#!/usr/bin/env python3
"""Audit v1.25 airway decision scenario pack."""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "data" / "airway_decision_scenario_pack_v1.25.yaml"


def _boolish(x) -> bool:
    return str(x).strip().lower() in {"true", "1", "yes"}


def run_scenario(path: str, dt: float, out: Path) -> pd.DataFrame:
    cmd = [sys.executable, str(ROOT / "run_simulation.py"), "--scenario", path, "--dt", str(dt), "--no-plot", "--save-csv", str(out)]
    subprocess.run(cmd, cwd=ROOT, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
    return pd.read_csv(out)


def has_state(df: pd.DataFrame, col: str, value: str) -> bool:
    return col in df.columns and (df[col].astype(str) == value).any()


def evaluate(df: pd.DataFrame, scenario_id: str) -> list[dict]:
    rows=[]
    final=df.iloc[-1]
    def add(check, ok, value=None):
        rows.append({"scenario": scenario_id, "check": check, "status": "PASS" if ok else "FAIL", "value": value})
    add("no_nan_required_vitals", all(col in df.columns and not df[col].isna().any() for col in ["SaO2","PaCO2","HR","MAP"]), None)
    add("airway_event_revision_present", "airway_event_revision" in df.columns and float(df["airway_event_revision"].max()) >= 1240, float(df["airway_event_revision"].max()) if "airway_event_revision" in df else None)
    add("event_type_present", "airway_event_type" in df.columns and df["airway_event_type"].astype(str).ne("none").any(), str(final.get("airway_event_type","none")))
    add("final_airway_secured", _boolish(final.get("intubated", False)) and str(final.get("airway_interface", "")) == "ETT", str(final.get("airway_interface", "")))
    add("success_time_recorded", float(final.get("intubation_success_time_s", -1)) > 0, float(final.get("intubation_success_time_s", -1)))
    add("ventilator_connected_final", _boolish(final.get("ventilator_connected", False)), final.get("ventilator_connected", None))
    add("hypoxia_burden_recorded", float(final.get("airway_event_hypoxia_burden", 0.0)) >= 0.0, float(final.get("airway_event_hypoxia_burden", 0.0)))
    if "failed_intubation" in scenario_id:
        add("multiple_failed_attempts", int(final.get("failed_intubation_count", 0)) >= 2, int(final.get("failed_intubation_count", 0)))
        add("laryngospasm_phase_present", float(final.get("laryngospasm_score", 0.0)) > 0.0 or has_state(df,"airway_rescue_state","upper_airway_obstruction"), float(final.get("laryngospasm_score", 0.0)))
        add("difficult_bvm_phase_present", has_state(df, "airway_rescue_state", "rescued_BVM"), None)
    if "extubation_failure" in scenario_id:
        add("extubation_time_recorded", float(final.get("extubation_time_s", -1)) > 0, float(final.get("extubation_time_s", -1)))
        add("HFNC_phase_present", has_state(df, "airway_interface", "HFNC"), None)
        add("obstruction_phase_present", has_state(df, "airway_rescue_state", "obstructed_airway"), None)
    if "laryngospasm" in scenario_id:
        add("laryngospasm_score_positive", float(final.get("laryngospasm_score", 0.0)) > 0, float(final.get("laryngospasm_score", 0.0)))
        add("post_extubation_phase_present", float(final.get("extubation_time_s", -1)) > 0, float(final.get("extubation_time_s", -1)))
    if "aspiration" in scenario_id:
        add("aspiration_risk_positive", float(final.get("aspiration_risk", 0.0)) >= 0.3, float(final.get("aspiration_risk", 0.0)))
        add("airway_protection_bounded", 0.0 <= float(final.get("airway_protection_score", 0.0)) <= 1.0, float(final.get("airway_protection_score", 0.0)))
    if "opioid_sedation" in scenario_id:
        add("manual_ventilation_phase_present", "bag_mask_ventilation_active" in df.columns and df["bag_mask_ventilation_active"].astype(str).str.lower().isin(["true","1"]).any(), None)
        
        sedation_present = ("C_morphine_ng_mL" in df.columns and float(df["C_morphine_ng_mL"].max()) > 0.0) or ("morphine_resp_depression_signal" in df.columns and float(df["morphine_resp_depression_signal"].max()) > 0.0)
        add("sedation_proxy_present", sedation_present, float(df["C_morphine_ng_mL"].max()) if "C_morphine_ng_mL" in df.columns else None)
    if "niv_failure" in scenario_id:
        add("NIV_phase_present", has_state(df, "airway_interface", "NIV_BIPAP"), None)
        add("NIV_failure_risk_present", "NIV_failure_risk" in df.columns and float(df["NIV_failure_risk"].max()) >= 0.0, float(df["NIV_failure_risk"].max()) if "NIV_failure_risk" in df else None)
    return rows


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--dt", type=float, default=10.0)
    ap.add_argument("--fail-on-review", action="store_true")
    args=ap.parse_args()
    pack=yaml.safe_load(PACK.read_text())
    outdir=ROOT/"outputs"/"airway_decision_scenarios_v1.25"
    outdir.mkdir(parents=True, exist_ok=True)
    all_rows=[]
    scenario_rows=[]
    for item in pack["scenarios"]:
        path=item["path"]
        sid=item["id"]
        outcsv=outdir/(sid+"_timeseries.csv")
        df=run_scenario(path,args.dt,outcsv)
        checks=evaluate(df,sid)
        all_rows.extend(checks)
        final=df.iloc[-1]
        scenario_rows.append({
            "scenario": sid,
            "final_airway_interface": str(final.get("airway_interface","")),
            "final_intubated": bool(_boolish(final.get("intubated", False))),
            "intubation_success_time_s": float(final.get("intubation_success_time_s", -1)),
            "failed_intubation_count": int(final.get("failed_intubation_count", 0)),
            "aspiration_risk": float(final.get("aspiration_risk", 0.0)),
            "laryngospasm_score": float(final.get("laryngospasm_score", 0.0)),
            "SaO2_final": float(final.get("SaO2", float("nan"))),
            "PaCO2_final": float(final.get("PaCO2", float("nan"))),
        })
    pd.DataFrame(all_rows).to_csv(outdir/"airway_decision_checks_v125.csv", index=False)
    pd.DataFrame(scenario_rows).to_csv(outdir/"airway_decision_scenario_summary_v125.csv", index=False)
    summary={
        "release":"v1.25-alpha",
        "scenario_count": len(pack["scenarios"]),
        "checks": len(all_rows),
        "pass": sum(r["status"]=="PASS" for r in all_rows),
        "fail": sum(r["status"]=="FAIL" for r in all_rows),
    }
    summary["status"]="PASS" if summary["fail"]==0 else "FAIL"
    (outdir/"airway_decision_audit_summary_v125.json").write_text(json.dumps(summary, indent=2))
    report=[f"# Airway decision scenario audit v1.25", "", f"Status: **{summary['status']}**", "", f"Scenarios: {summary['scenario_count']}", f"Checks: {summary['checks']}"]
    (outdir/"airway_decision_audit_report_v125.md").write_text("\n".join(report)+"\n")
    print(json.dumps(summary, indent=2))
    if args.fail_on_review and summary["fail"]:
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
