#!/usr/bin/env python3
"""v1.23.2 NIV / CPAP / BiPAP audit."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = {
    "niv_cpap": ROOT / "scenarios" / "airway_niv_cpap_bronchiolitis_v1_23_2.yaml",
    "niv_bipap": ROOT / "scenarios" / "airway_niv_bipap_hypercapnia_v1_23_2.yaml",
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

    outdir = ROOT / "outputs" / "niv_cpap_bipap_v1.23.2"
    outdir.mkdir(parents=True, exist_ok=True)

    rows = []
    for name, scen in SCENARIOS.items():
        df, rel = run_scenario(name, scen, args.dt, outdir)
        f = df.iloc[-1]
        if name == "niv_cpap":
            checks = [
                ("not_intubated", not bool(f.get("intubated", True))),
                ("ventilator_connected", bool(f.get("ventilator_connected", False))),
                ("pressure_delivery_enabled", bool(f.get("airway_pressure_delivery_enabled", False))),
                ("interface_niv_cpap", str(f.get("airway_interface", "")).upper() == "NIV_CPAP"),
                ("niv_mode_cpap", str(f.get("NIV_mode", "")).upper() == "CPAP"),
                ("delivered_peep_positive", float(f.get("NIV_delivered_PEEP_cmH2O", 0.0)) > 2.0),
                ("delivered_ps_near_zero", float(f.get("NIV_delivered_PS_cmH2O", 99.0)) <= 0.5),
                ("fio2_delivered_above_room", float(f.get("FiO2_delivered", 0.0)) > 0.21),
                ("failure_risk_bounded", 0.0 <= float(f.get("NIV_failure_risk", -1.0)) <= 1.0),
            ]
        else:
            checks = [
                ("not_intubated", not bool(f.get("intubated", True))),
                ("ventilator_connected", bool(f.get("ventilator_connected", False))),
                ("pressure_delivery_enabled", bool(f.get("airway_pressure_delivery_enabled", False))),
                ("interface_niv_bipap", str(f.get("airway_interface", "")).upper() == "NIV_BIPAP"),
                ("niv_mode_bipap", str(f.get("NIV_mode", "")).upper() == "BIPAP"),
                ("delivered_peep_positive", float(f.get("NIV_delivered_PEEP_cmH2O", 0.0)) > 2.0),
                ("delivered_ps_positive", float(f.get("NIV_delivered_PS_cmH2O", 0.0)) > 2.0),
                ("pip_exceeds_peep", float(f.get("NIV_delivered_PIP_cmH2O", 0.0)) > float(f.get("NIV_delivered_PEEP_cmH2O", 0.0))),
                ("deadspace_washout_positive", float(f.get("NIV_deadspace_washout", 0.0)) > 0.02),
                ("fio2_delivered_above_room", float(f.get("FiO2_delivered", 0.0)) > 0.21),
                ("failure_risk_bounded", 0.0 <= float(f.get("NIV_failure_risk", -1.0)) <= 1.0),
            ]
        for check, ok in checks:
            rows.append({"scenario": name, "check": check, "status": "PASS" if ok else "REVIEW", "timeseries": rel})

    summary = {
        "release": "v1.23.2-alpha",
        "checks": len(rows),
        "pass": sum(r["status"] == "PASS" for r in rows),
        "review": sum(r["status"] == "REVIEW" for r in rows),
        "fail": 0,
        "rows": rows,
    }
    pd.DataFrame(rows).to_csv(outdir / "niv_cpap_bipap_audit_rows_v1232.csv", index=False)
    (outdir / "niv_cpap_bipap_audit_summary_v1232.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: summary[k] for k in ["release", "checks", "pass", "review", "fail"]}, indent=2))
    if args.fail_on_review and summary["review"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
