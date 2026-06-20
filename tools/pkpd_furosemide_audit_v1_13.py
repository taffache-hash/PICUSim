#!/usr/bin/env python3
"""Furosemide PK/PD educational audit — v1.13-alpha.

Runs isolated PharmacologyModule cases to verify that the public furosemide
scaffold exposes concentration, renal-function-dependent clearance, qualitative
PD signal and CRRT audit fields. Not for clinical dosing.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.bus import BusState, PhysiologicalBus  # noqa: E402
from modules.pharmacology.pk_pd import PharmacologyModule  # noqa: E402


def run_case(name: str, weight_kg: float, age_y: float, gfr: float, gfr_baseline: float,
             aki_stage: int, infusion_mg_kg_h: float = 0.0, bolus_mg_kg: float = 0.0,
             crrt: bool = False, effluent: float = 0.0) -> dict:
    bus = PhysiologicalBus(BusState(
        weight_kg=weight_kg,
        age_y=age_y,
        GFR=gfr,
        GFR_baseline=gfr_baseline,
        AKI_stage=aki_stage,
        CRRT_active=crrt,
        CRRT_effluent_mL_kg_h=effluent,
    ))
    bus.set("furosemide_mg_kg", bolus_mg_kg)
    bus.set("furosemide_mg_kg_h", infusion_mg_kg_h)
    age_group = "infant" if age_y < 1 else ("adolescent" if age_y >= 12 else "child")
    mod = PharmacologyModule({"weight_kg": weight_kg, "age_y": age_y, "age_group": age_group})
    mod.initialize(bus)
    for _ in range(240):
        mod.step(bus, 1.0)
    return {
        "case": name,
        "weight_kg": weight_kg,
        "age_y": age_y,
        "GFR": gfr,
        "GFR_baseline": gfr_baseline,
        "AKI_stage": aki_stage,
        "bolus_mg_kg": bolus_mg_kg,
        "infusion_mg_kg_h": infusion_mg_kg_h,
        "CRRT_active": crrt,
        "C_furosemide_mg_L": round(float(bus.get("C_furosemide_mg_L")), 5),
        "effect_signal": round(float(bus.get("furosemide_effect_signal")), 5),
        "renal_clearance_factor": round(float(bus.get("furosemide_renal_clearance_factor")), 5),
        "crrt_CL_L_min": round(float(bus.get("pk_crrt_furosemide_CL_L_min")), 6),
        "pk_supported_drug_count": int(bus.get("pk_supported_drug_count")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default=str(ROOT / "outputs" / "pkpd_furosemide_v1.13"))
    parser.add_argument("--fail-on-review", action="store_true")
    args = parser.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    rows = [
        run_case("child_normal_bolus", 20, 6.0, 70, 70, 0, bolus_mg_kg=1.0),
        run_case("child_normal_infusion", 20, 6.0, 70, 70, 0, infusion_mg_kg_h=0.2),
        run_case("child_aki_infusion", 20, 6.0, 14, 70, 2, infusion_mg_kg_h=0.2),
        run_case("infant_infusion", 8, 0.7, 28, 28, 0, infusion_mg_kg_h=0.2),
        run_case("child_aki_crrt", 20, 6.0, 18, 70, 2, infusion_mg_kg_h=0.2, crrt=True, effluent=35),
    ]

    csv_path = outdir / "pkpd_furosemide_audit_v113.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)

    review = []
    if rows[0]["pk_supported_drug_count"] < 11:
        review.append("Expected pk_supported_drug_count >= 11.")
    if rows[0]["C_furosemide_mg_L"] <= 0.1 or rows[0]["effect_signal"] <= 0.0:
        review.append("Bolus case should generate furosemide concentration and effect signal.")
    if rows[2]["renal_clearance_factor"] >= rows[1]["renal_clearance_factor"]:
        review.append("AKI case should reduce furosemide renal clearance/effect factor.")
    if rows[4]["crrt_CL_L_min"] <= 0.0:
        review.append("CRRT active case should expose positive extracorporeal furosemide clearance.")

    summary = {
        "release": "v1.13-alpha",
        "status": "PASS" if not review else "REVIEW",
        "rows": len(rows),
        "review_items": review,
        "csv": str(csv_path.relative_to(ROOT)),
    }
    (outdir / "pkpd_furosemide_audit_v113_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    if args.fail_on_review and review:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
