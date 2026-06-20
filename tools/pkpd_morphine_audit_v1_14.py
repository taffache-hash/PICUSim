#!/usr/bin/env python3
"""Morphine PK/PD audit for v1.14-alpha."""
from __future__ import annotations
import argparse, csv, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bus import PhysiologicalBus
from modules.pharmacology.pk_pd import PharmacologyModule
from modules.analgosedation.pain_stress_sedation import PainStressSedationModule


def run_case(name: str, weight: float = 20.0, age: float = 6.0, group: str = "child", infusion: float = 20.0,
             creatinine: float = 0.35, baseline: float = 0.35, crrt: bool = False, seconds: int = 900):
    bus = PhysiologicalBus()
    bus.set("morphine_mcg_kg_h", infusion)
    bus.set("creatinine_baseline_mg_dL", baseline)
    bus.set("creatinine_mg_dL", creatinine)
    bus.set("GFR_baseline", 70.0 if weight >= 20 else 35.0)
    bus.set("GFR", 70.0 if creatinine <= baseline * 1.2 else 28.0)
    bus.set("AKI_stage", 0 if creatinine <= baseline * 1.5 else 2)
    bus.set("CRRT_active", bool(crrt))
    bus.set("CRRT_effluent_mL_kg_h", 35.0 if crrt else 0.0)
    ph = PharmacologyModule({"weight_kg": weight, "age_y": age, "age_group": group})
    ps = PainStressSedationModule({"weight_kg": weight})
    ph.initialize(bus)
    ps.initialize(bus)
    for _ in range(int(seconds // 5)):
        ph.step(bus, 5.0)
        ps.step(bus, 5.0)
    return {
        "case": name,
        "weight_kg": weight,
        "infusion_mcg_kg_h": infusion,
        "creatinine_mg_dL": creatinine,
        "crrt": bool(crrt),
        "C_morphine_ng_mL": round(float(bus.get("C_morphine_ng_mL")), 5),
        "analgesia_signal": round(float(bus.get("morphine_analgesia_signal")), 5),
        "resp_depression_signal": round(float(bus.get("morphine_resp_depression_signal")), 5),
        "renal_accumulation_risk": round(float(bus.get("morphine_renal_accumulation_risk")), 5),
        "M6G_proxy": round(float(bus.get("M6G_accumulation_proxy")), 5),
        "pk_crrt_morphine_CL_L_min": round(float(bus.get("pk_crrt_morphine_CL_L_min")), 7),
        "analgesia_score": round(float(bus.get("analgesia_score")), 5),
        "opioid_resp_depression": round(float(bus.get("opioid_resp_depression")), 5),
        "pk_supported_drug_count": int(bus.get("pk_supported_drug_count")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default=str(ROOT / "outputs" / "pkpd_morphine_v1.14"))
    parser.add_argument("--fail-on-review", action="store_true")
    args = parser.parse_args()
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    rows = [
        run_case("child_standard"),
        run_case("child_higher_infusion", infusion=35.0),
        run_case("child_AKI", infusion=20.0, creatinine=0.95),
        run_case("child_AKI_CRRT", infusion=20.0, creatinine=0.95, crrt=True),
        run_case("infant", weight=8.0, age=0.7, group="infant", infusion=15.0, baseline=0.25, creatinine=0.25),
    ]
    csv_path = outdir / "pkpd_morphine_audit_v114.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    review = []
    if rows[0]["C_morphine_ng_mL"] <= 0.1 or rows[0]["analgesia_signal"] <= 0.0:
        review.append("Standard morphine case should generate concentration and analgesia signal.")
    if rows[1]["C_morphine_ng_mL"] <= rows[0]["C_morphine_ng_mL"]:
        review.append("Higher infusion should produce higher concentration.")
    if rows[2]["renal_accumulation_risk"] <= rows[0]["renal_accumulation_risk"]:
        review.append("AKI case should increase morphine metabolite accumulation risk.")
    if rows[3]["pk_crrt_morphine_CL_L_min"] <= 0.0:
        review.append("CRRT active case should expose positive extracorporeal morphine clearance.")
    if any(r["pk_supported_drug_count"] < 12 for r in rows):
        review.append("PharmacologyModule should report 12 supported drugs.")
    summary = {"release": "v1.14-alpha", "status": "PASS" if not review else "REVIEW", "rows": len(rows), "review_items": review, "csv": str(csv_path)}
    (outdir / "pkpd_morphine_audit_v114_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: summary[k] for k in ["release", "status", "rows", "review_items"]}, indent=2))
    return 1 if args.fail_on_review and review else 0

if __name__ == "__main__":
    raise SystemExit(main())
