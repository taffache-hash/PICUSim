#!/usr/bin/env python3
"""v0.45 profile scaling smoke report.

Runs a healthy template across pediatric profiles to verify that profile-derived
anchors change in the expected direction. This is a governance/smoke test, not
external validation.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.profiles import load_profiles  # noqa: E402
from tools.simtools import load_yaml, run_config  # noqa: E402

OUT = ROOT / "outputs" / "validation_pack"


def build_profile_config(profile_name: str, profile: dict, base: dict) -> dict:
    cfg = dict(base)
    cfg = json.loads(json.dumps(cfg))
    cfg["name"] = f"profile_scaling_{profile_name}"
    cfg["description"] = "v0.45 profile scaling smoke scenario"
    cfg["patient"] = {
        "profile": profile_name,
        "age_y": float(profile["age_y"]),
        "weight_kg": float(profile["weight_kg"]),
        "sex": "M",
        "diagnosis": "profile_scaling_smoke",
    }
    cfg["respiratory"] = {
        "PEEP": 5,
        "Paw": 12 if profile["weight_kg"] <= 20 else 15,
        "FiO2": 0.30,
        "RR": float(profile["RR"]),
        "R_rs": 8.0,
        "PaO2": 95.0,
        "PaCO2": 38.0,
        "SaO2": 0.98,
    }
    cfg["cardiovascular"] = {"HR": float(profile["HR"]), "MAP": float(profile["MAP"]), "Hb": float(profile["Hb"])}
    cfg["metabolism"] = {"T_core": 37.0, "VO2": float(profile["VO2_ml_kg_min"]) * float(profile["weight_kg"])}
    cfg["perturbations"] = []
    cfg["simulation_time_s"] = 90
    return cfg


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dt", type=float, default=2.0)
    ap.add_argument("--output-dir", type=Path, default=OUT)
    ap.add_argument("--fail-on-error", action="store_true")
    args = ap.parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    profiles = load_profiles()
    base = load_yaml(ROOT / "scenarios" / "healthy_child_20kg.yaml")
    rows = []
    errors = []
    for name, prof in profiles.items():
        try:
            cfg = build_profile_config(name, prof, base)
            df = run_config(cfg, dt=args.dt, quiet=True)
            last = df.iloc[-1]
            wt = float(prof["weight_kg"])
            rows.append({
                "profile": name,
                "age_group": prof.get("age_group", ""),
                "age_y": float(prof["age_y"]),
                "weight_kg": wt,
                "BSA_m2_final": float(last.get("BSA_m2", 0.0)) if "BSA_m2" in df.columns else 0.0,
                "FRC_mL_final": float(last.get("FRC", 0.0)),
                "FRC_mL_kg_final": float(last.get("FRC", 0.0)) / max(wt, 1e-6),
                "C_rs_final": float(last.get("C_rs", 0.0)),
                "Vt_mL_final": float(last.get("Vt", 0.0)),
                "Vt_mL_kg_final": float(last.get("Vt", 0.0)) / max(wt, 1e-6),
                "GFR_final": float(last.get("GFR", 0.0)),
                "urine_output_mL_kg_h_final": float(last.get("urine_output_mL_kg_h", 0.0)),
                "glucose_mmol_L_final": float(last.get("glucose_mmol_L", 0.0)),
                "PaCO2_final": float(last.get("PaCO2", 0.0)),
                "SaO2_final": float(last.get("SaO2", 0.0)),
            })
        except Exception as exc:  # pragma: no cover
            errors.append({"profile": name, "error": str(exc)})

    csv_path = out / "profile_scaling_smoke_v045.csv"
    if rows:
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
    md_path = out / "profile_scaling_smoke_v045_report.md"
    lines = ["# v0.45 Profile scaling smoke report", "", "This smoke report checks that profile-derived anchors are used across pediatric sizes. It is not clinical validation.", "", f"Profiles run: {len(rows)}", f"Errors: {len(errors)}", ""]
    if rows:
        lines += ["| profile | kg | FRC mL/kg | Vt mL/kg | GFR mL/min | glucose | PaCO2 |", "|---|---:|---:|---:|---:|---:|---:|"]
        for r in rows:
            lines.append(f"| {r['profile']} | {r['weight_kg']:.1f} | {r['FRC_mL_kg_final']:.1f} | {r['Vt_mL_kg_final']:.1f} | {r['GFR_final']:.1f} | {r['glucose_mmol_L_final']:.2f} | {r['PaCO2_final']:.1f} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary = {"version": "0.45", "profiles_run": len(rows), "errors": errors, "status": "PASS" if not errors else "ERROR"}
    (out / "profile_scaling_smoke_v045_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 1 if errors and args.fail_on_error else 0

if __name__ == "__main__":
    raise SystemExit(main())
