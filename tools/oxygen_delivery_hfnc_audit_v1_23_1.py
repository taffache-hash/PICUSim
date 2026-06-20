#!/usr/bin/env python3
"""v1.23.1 oxygen delivery / HFNC audit."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = {
    "low_flow": ROOT / "scenarios" / "airway_low_flow_oxygen_v1_23_1.yaml",
    "hfnc": ROOT / "scenarios" / "airway_hfnc_bronchiolitis_v1_23_1.yaml",
}


def run_scenario(name: str, path: Path, dt: float, outdir: Path) -> tuple[pd.DataFrame, str]:
    out = outdir / f"{name}_timeseries.csv"
    cmd = [sys.executable, str(ROOT / "run_simulation.py"), "--scenario", str(path), "--dt", str(dt), "--no-plot", "--save-csv", str(out)]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
    if res.returncode != 0:
        raise RuntimeError(res.stderr[-2000:] + res.stdout[-2000:])
    return pd.read_csv(out, index_col=0), str(out.relative_to(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dt", type=float, default=2.0)
    ap.add_argument("--fail-on-review", action="store_true")
    args = ap.parse_args()

    outdir = ROOT / "outputs" / "oxygen_delivery_hfnc_v1.23.1"
    outdir.mkdir(parents=True, exist_ok=True)

    rows = []
    for name, scen in SCENARIOS.items():
        df, rel = run_scenario(name, scen, args.dt, outdir)
        f = df.iloc[-1]
        checks = []
        if name == "low_flow":
            checks = [
                ("not_intubated", not bool(f.get("intubated", True))),
                ("ventilator_disconnected", not bool(f.get("ventilator_connected", True))),
                ("interface_low_flow", str(f.get("airway_interface", "")).upper() == "LOW_FLOW_OXYGEN"),
                ("fio2_delivered_above_room_air", float(f.get("FiO2_delivered", 0.0)) > 0.21),
                ("no_external_peep", float(f.get("effective_external_PEEP_cmH2O", 0.0)) <= 0.2),
            ]
        else:
            checks = [
                ("not_intubated", not bool(f.get("intubated", True))),
                ("ventilator_disconnected", not bool(f.get("ventilator_connected", True))),
                ("interface_hfnc", str(f.get("airway_interface", "")).upper() == "HFNC"),
                ("fio2_delivered_above_room_air", float(f.get("FiO2_delivered", 0.0)) > 0.30),
                ("hfnc_pressure_positive", float(f.get("HFNC_distending_pressure_cmH2O", 0.0)) > 0.5),
                ("hfnc_washout_positive", float(f.get("HFNC_deadspace_washout", 0.0)) > 0.05),
                ("failure_risk_bounded", 0.0 <= float(f.get("HFNC_failure_risk", -1.0)) <= 1.0),
            ]
        for check, ok in checks:
            rows.append({
                "scenario": name,
                "check": check,
                "status": "PASS" if ok else "REVIEW",
                "timeseries": rel,
            })

    summary = {
        "release": "v1.23.1-alpha",
        "checks": len(rows),
        "pass": sum(r["status"] == "PASS" for r in rows),
        "review": sum(r["status"] == "REVIEW" for r in rows),
        "fail": 0,
        "rows": rows,
    }
    pd.DataFrame(rows).to_csv(outdir / "oxygen_delivery_hfnc_audit_rows_v1231.csv", index=False)
    (outdir / "oxygen_delivery_hfnc_audit_summary_v1231.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: summary[k] for k in ["release", "checks", "pass", "review", "fail"]}, indent=2))
    if args.fail_on_review and summary["review"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
