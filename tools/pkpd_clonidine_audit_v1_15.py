#!/usr/bin/env python3
"""Clonidine PK/PD audit for v1.15-alpha."""
from __future__ import annotations
import argparse, csv, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bus import PhysiologicalBus
from modules.pharmacology.pk_pd import PharmacologyModule
from modules.analgosedation.pain_stress_sedation import PainStressSedationModule


def run_case(name: str, weight: float = 20.0, age: float = 6.0, group: str = "child", infusion: float = 0.6,
             baseline_morphine: float = 20.0, crrt: bool = False, seconds: int = 1200):
    bus = PhysiologicalBus()
    bus.set("clonidine_mcg_kg_h", infusion)
    bus.set("morphine_mcg_kg_h", baseline_morphine)
    bus.set("midazolam_mcg_kg_h", 60.0)
    bus.set("MAP", 70.0)
    bus.set("HR", 125.0)
    bus.set("GFR_baseline", 70.0 if weight >= 20 else 35.0)
    bus.set("GFR", 70.0 if weight >= 20 else 35.0)
    bus.set("CRRT_active", bool(crrt))
    bus.set("CRRT_effluent_mL_kg_h", 35.0 if crrt else 0.0)
    ph = PharmacologyModule({"weight_kg": weight, "age_y": age, "age_group": group})
    ps = PainStressSedationModule({"weight_kg": weight})
    ph.initialize(bus); ps.initialize(bus)
    for i in range(int(seconds // 5)):
        # create a simple weaning drop halfway through to exercise withdrawal modulation
        if i == int(seconds // 10):
            bus.set("morphine_mcg_kg_h", max(baseline_morphine * 0.35, 0.0))
            bus.set("midazolam_mcg_kg_h", 20.0)
        ph.step(bus, 5.0); ps.step(bus, 5.0)
    return {
        "case": name,
        "weight_kg": weight,
        "infusion_mcg_kg_h": infusion,
        "crrt": bool(crrt),
        "C_clonidine_ng_mL": round(float(bus.get("C_clonidine_ng_mL")), 5),
        "sedation_signal": round(float(bus.get("clonidine_sedation_signal")), 5),
        "sympatholysis_signal": round(float(bus.get("clonidine_sympatholysis_signal")), 5),
        "bradycardia_risk": round(float(bus.get("clonidine_bradycardia_risk")), 5),
        "hypotension_risk": round(float(bus.get("clonidine_hypotension_risk")), 5),
        "withdrawal_mod": round(float(bus.get("clonidine_withdrawal_mod")), 5),
        "withdrawal_risk": round(float(bus.get("withdrawal_risk")), 5),
        "sedation_score": round(float(bus.get("sedation_score")), 5),
        "pk_crrt_clonidine_CL_L_min": round(float(bus.get("pk_crrt_clonidine_CL_L_min")), 7),
        "pk_supported_drug_count": int(bus.get("pk_supported_drug_count")),
        "pk_extension_revision": int(bus.get("pk_extension_revision")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default=str(ROOT / "outputs" / "pkpd_clonidine_v1.15"))
    parser.add_argument("--fail-on-review", action="store_true")
    args = parser.parse_args()
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    rows = [
        run_case("child_low", infusion=0.3),
        run_case("child_standard", infusion=0.6),
        run_case("child_higher", infusion=1.2),
        run_case("child_crrt", infusion=0.8, crrt=True),
        run_case("infant", weight=8.0, age=0.7, group="infant", infusion=0.4, baseline_morphine=12.0),
    ]
    csv_path = outdir / "pkpd_clonidine_audit_v115.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    review = []
    if rows[1]["C_clonidine_ng_mL"] <= 0.0 or rows[1]["sedation_signal"] <= 0.0:
        review.append("Standard clonidine case should generate concentration and sedation signal.")
    if rows[2]["C_clonidine_ng_mL"] <= rows[0]["C_clonidine_ng_mL"]:
        review.append("Higher infusion should produce higher clonidine concentration.")
    if rows[2]["sympatholysis_signal"] < rows[0]["sympatholysis_signal"]:
        review.append("Higher infusion should not reduce sympatholysis signal.")
    if rows[3]["pk_crrt_clonidine_CL_L_min"] <= 0.0:
        review.append("CRRT active case should expose positive extracorporeal clonidine clearance field.")
    if any(r["pk_supported_drug_count"] < 14 for r in rows):
        review.append("PharmacologyModule should report at least 14 supported drugs.")
    if any(r["pk_extension_revision"] < 116 for r in rows):
        review.append("PharmacologyModule should report at least v1.16 extension revision.")
    summary = {"release": "v1.15-alpha", "status": "PASS" if not review else "REVIEW", "rows": len(rows), "review_items": review, "csv": str(csv_path)}
    (outdir / "pkpd_clonidine_audit_v115_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: summary[k] for k in ["release", "status", "rows", "review_items"]}, indent=2))
    return 1 if args.fail_on_review and review else 0

if __name__ == "__main__":
    raise SystemExit(main())
