#!/usr/bin/env python3
"""Vancomycin PK/PD educational audit — v1.12-alpha.

Runs a small deterministic grid over pediatric profiles and renal/CRRT states.
Outputs are for regression and educational plausibility checks only.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.bus import PhysiologicalBus, BusState
from modules.pharmacology.pk_pd import PharmacologyModule


def run_case(name: str, weight_kg: float, age_y: float, age_group: str, gfr: float, gfr_base: float, crrt: bool, effluent: float, dose_mg_kg_h: float, duration_s: int = 900, dt: float = 5.0) -> dict:
    bus = PhysiologicalBus(BusState(
        weight_kg=weight_kg,
        age_y=age_y,
        GFR=gfr,
        GFR_baseline=gfr_base,
        CRRT_active=crrt,
        CRRT_effluent_mL_kg_h=effluent,
    ))
    bus.set("vancomycin_mg_kg_h", dose_mg_kg_h)
    mod = PharmacologyModule({"weight_kg": weight_kg, "age_y": age_y, "age_group": age_group})
    mod.initialize(bus)
    steps = int(duration_s / dt)
    for _ in range(steps):
        mod.step(bus, dt)
    return {
        "case": name,
        "weight_kg": weight_kg,
        "age_y": age_y,
        "age_group": age_group,
        "GFR": gfr,
        "GFR_baseline": gfr_base,
        "CRRT_active": bool(crrt),
        "CRRT_effluent_mL_kg_h": effluent,
        "dose_mg_kg_h": dose_mg_kg_h,
        "C_vancomycin_mg_L": round(float(bus.get("C_vancomycin_mg_L")), 5),
        "target_attainment": round(float(bus.get("vancomycin_target_attainment")), 5),
        "coverage_mod": round(float(bus.get("vancomycin_coverage_mod")), 5),
        "renal_clearance_factor": round(float(bus.get("vancomycin_renal_clearance_factor")), 5),
        "crrt_CL_L_min": round(float(bus.get("pk_crrt_vancomycin_CL_L_min")), 6),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default=str(ROOT / "outputs" / "pkpd_vancomycin_v1.12"))
    parser.add_argument("--fail-on-review", action="store_true")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    cases = [
        ("child_normal_renal", 20.0, 6.0, "child", 70.0, 70.0, False, 0.0),
        ("child_aki", 20.0, 6.0, "child", 15.0, 70.0, False, 0.0),
        ("child_aki_crrt", 20.0, 6.0, "child", 15.0, 70.0, True, 35.0),
        ("infant_normal_renal", 8.0, 0.7, "infant", 28.0, 28.0, False, 0.0),
        ("adolescent_normal_renal", 50.0, 14.0, "adolescent", 120.0, 120.0, False, 0.0),
    ]
    rows = [run_case(*c, dose_mg_kg_h=20.0) for c in cases]

    csv_path = outdir / "pkpd_vancomycin_audit_v112.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)

    review = []
    if not rows[1]["C_vancomycin_mg_L"] > rows[0]["C_vancomycin_mg_L"]:
        review.append("AKI should increase concentration vs normal renal function for same dose/duration.")
    if not rows[2]["crrt_CL_L_min"] > 0.0:
        review.append("CRRT active case should expose positive extracorporeal vancomycin clearance.")
    if not all(0.0 <= r["target_attainment"] <= 1.0 for r in rows):
        review.append("Target attainment outside [0, 1].")

    summary = {
        "release": "v1.12-alpha",
        "status": "PASS" if not review else "REVIEW",
        "rows": len(rows),
        "review_items": review,
        "csv": str(csv_path.relative_to(ROOT)),
    }
    (outdir / "pkpd_vancomycin_audit_v112_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    if args.fail_on_review and review:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
