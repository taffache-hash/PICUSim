#!/usr/bin/env python3
"""Airway interface audit v1.23."""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "scenarios" / "airway_unassisted_spontaneous_breathing_v1_23.yaml"

def run_scenario(dt: float) -> pd.DataFrame:
    out = ROOT / "outputs" / "airway_interface_v1.23" / "airway_unassisted.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(ROOT / "run_simulation.py"), "--scenario", str(SCENARIO), "--dt", str(dt), "--no-plot", "--save-csv", str(out)]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=90)
    if res.returncode != 0:
        raise RuntimeError(res.stderr[-2000:] + res.stdout[-2000:])
    return pd.read_csv(out, index_col=0)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dt", type=float, default=2.0)
    ap.add_argument("--fail-on-review", action="store_true")
    args = ap.parse_args()
    df = run_scenario(args.dt)
    final = df.iloc[-1]
    rows = []
    def check(name, ok, value):
        rows.append({"check": name, "status": "PASS" if ok else "REVIEW", "value": str(value)})
    check("vent_mode_NONE", str(final.get("vent_mode", "")).upper() == "NONE", final.get("vent_mode"))
    check("airway_UNASSISTED", str(final.get("airway_interface", "")).upper() == "UNASSISTED", final.get("airway_interface"))
    check("not_intubated", str(final.get("intubated", "False")).lower() in ("false", "0", "0.0"), final.get("intubated"))
    check("not_connected", str(final.get("ventilator_connected", "False")).lower() in ("false", "0", "0.0"), final.get("ventilator_connected"))
    check("paw_ambient", abs(float(final.get("Paw", 99))) <= 0.2, final.get("Paw"))
    check("peep_zero", abs(float(final.get("PEEP", 99))) <= 0.2, final.get("PEEP"))
    check("pmus_positive", float(final.get("Pmus", 0)) > 0.5, final.get("Pmus"))
    check("vt_positive", float(final.get("Vt", 0)) > 20.0, final.get("Vt"))
    check("gas_stable", 0.80 <= float(final.get("SaO2", 0)) <= 1.0 and 25 <= float(final.get("PaCO2", 999)) <= 70, f"SaO2={final.get('SaO2')}, PaCO2={final.get('PaCO2')}")
    summary = {
        "release": "v1.23-alpha",
        "scenario": SCENARIO.name,
        "checks": len(rows),
        "pass": sum(r["status"] == "PASS" for r in rows),
        "review": sum(r["status"] == "REVIEW" for r in rows),
        "rows": rows,
    }
    outdir = ROOT / "outputs" / "airway_interface_v1.23"
    (outdir / "airway_interface_audit_summary_v123.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: summary[k] for k in ["release", "checks", "pass", "review"]}, indent=2))
    if args.fail_on_review and summary["review"]:
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
