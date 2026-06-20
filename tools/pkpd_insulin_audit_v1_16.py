#!/usr/bin/env python3
"""Insulin PK/PD audit for v1.16-alpha."""
from __future__ import annotations
import argparse, csv, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bus import PhysiologicalBus
from modules.pharmacology.pk_pd import PharmacologyModule
from modules.nutrition.glucose import GlucoseModule
from modules.acidbase.electrolytes import AcidBaseElectrolyteModule


def run_case(name: str, infusion_U_h: float, glucose0: float = 12.0, GIR: float = 6.0,
             weight: float = 20.0, age: float = 6.0, group: str = "child", seconds: int = 900):
    bus = PhysiologicalBus()
    bus.set("insulin_UI_h", infusion_U_h)
    bus.set("glucose_mmol_L", glucose0)
    bus.set("GIR_mg_kg_min", GIR)
    bus.set("K_mmol_L", 4.8)
    bus.set("VO2", 120.0)
    bus.set("MAP", 70.0)
    bus.set("T_core", 37.5)
    ph = PharmacologyModule({"weight_kg": weight, "age_y": age, "age_group": group})
    gl = GlucoseModule({"weight_kg": weight, "glucose_baseline_mmol_L": glucose0, "GIR_mg_kg_min": GIR})
    ab = AcidBaseElectrolyteModule({})
    ph.initialize(bus); gl.initialize(bus); ab.initialize(bus)
    start_glucose = float(bus.get("glucose_mmol_L"))
    for _ in range(int(seconds // 5)):
        ph.step(bus, 5.0)
        gl.step(bus, 5.0)
        ab.step(bus, 5.0)
    return {
        "case": name,
        "infusion_U_h": infusion_U_h,
        "weight_kg": weight,
        "start_glucose_mmol_L": round(start_glucose, 4),
        "end_glucose_mmol_L": round(float(bus.get("glucose_mmol_L")), 4),
        "C_insulin_mU_L": round(float(bus.get("C_insulin_mU_L")), 4),
        "glucose_clearance_signal": round(float(bus.get("insulin_glucose_clearance_signal")), 5),
        "potassium_shift_signal": round(float(bus.get("insulin_potassium_shift_signal")), 5),
        "hypoglycemia_risk": round(float(bus.get("insulin_hypoglycemia_risk")), 5),
        "effective_clearance_mmol_L_h": round(float(bus.get("insulin_effective_clearance_mmol_L_h")), 5),
        "K_mmol_L": round(float(bus.get("K_mmol_L")), 4),
        "pk_supported_drug_count": int(bus.get("pk_supported_drug_count")),
        "pk_extension_revision": int(bus.get("pk_extension_revision")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default=str(ROOT / "outputs" / "pkpd_insulin_v1.16"))
    parser.add_argument("--fail-on-review", action="store_true")
    args = parser.parse_args()
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    rows = [
        run_case("no_insulin", 0.0),
        run_case("low_insulin", 0.5),
        run_case("standard_insulin", 1.0),
        run_case("higher_insulin", 2.0),
        run_case("infant", 0.3, glucose0=10.0, GIR=5.0, weight=8.0, age=0.7, group="infant"),
    ]
    csv_path = outdir / "pkpd_insulin_audit_v116.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    review = []
    if rows[0]["C_insulin_mU_L"] != 0.0 or rows[0]["glucose_clearance_signal"] != 0.0:
        review.append("No-insulin case should have zero insulin concentration and effect signal.")
    if rows[2]["C_insulin_mU_L"] <= rows[1]["C_insulin_mU_L"]:
        review.append("Higher infusion should increase insulin concentration.")
    if rows[3]["glucose_clearance_signal"] < rows[1]["glucose_clearance_signal"]:
        review.append("Higher infusion should not reduce insulin glucose signal.")
    if rows[2]["end_glucose_mmol_L"] >= rows[0]["end_glucose_mmol_L"]:
        review.append("Insulin case should lower glucose compared with no-insulin case.")
    if any(r["pk_supported_drug_count"] < 14 for r in rows):
        review.append("PharmacologyModule should report at least 14 supported drugs.")
    if any(r["pk_extension_revision"] < 116 for r in rows):
        review.append("PharmacologyModule should report at least v1.16 extension revision.")
    summary = {"release": "v1.16-alpha", "status": "PASS" if not review else "REVIEW", "rows": len(rows), "review_items": review, "csv": str(csv_path)}
    (outdir / "pkpd_insulin_audit_v116_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: summary[k] for k in ["release", "status", "rows", "review_items"]}, indent=2))
    return 1 if args.fail_on_review and review else 0

if __name__ == "__main__":
    raise SystemExit(main())
