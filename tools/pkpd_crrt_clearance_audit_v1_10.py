#!/usr/bin/env python3
"""CRRT-lite PK clearance audit — v1.10-alpha.

Compares isolated PharmacologyModule concentration-time curves with CRRT off/on
for selected PICU drugs. This is a numerical smoke/plausibility audit, not a
clinical dosing model.
"""
from __future__ import annotations

import argparse, csv, json, sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bus import BusState, PhysiologicalBus  # noqa: E402
from modules.pharmacology.pk_pd import PharmacologyModule  # noqa: E402

OUTDIR_DEFAULT = ROOT / "outputs" / "pkpd_crrt_clearance_v1.10"

@dataclass(frozen=True)
class DrugSpec:
    name: str
    input_key: str
    output_key: str
    dose_value: float

DRUGS = (
    DrugSpec("midazolam", "midazolam_mcg_kg_h", "C_midazolam_ng_mL", 120.0),
    DrugSpec("rocuronium", "rocuronium_mg_kg_h", "C_rocuronium_ng_mL", 0.6),
    DrugSpec("fentanyl", "fentanyl_mcg_kg_h", "C_fentanyl_ng_mL", 2.0),
    DrugSpec("dexmedetomidine", "dexmedetomidine_mcg_kg_h", "C_dexmedetomidine_ng_mL", 0.5),
)

def simulate(drug: DrugSpec, crrt_active: bool, effluent: float, dt: float, T: float) -> dict[str, Any]:
    bus = PhysiologicalBus(BusState(weight_kg=20.0, age_y=6.0, age_group="child", patient_profile="child_20kg"))
    bus.set("CRRT_active", bool(crrt_active))
    bus.set("CRRT_effluent_mL_kg_h", float(effluent if crrt_active else 0.0))
    mod = PharmacologyModule({"weight_kg": 20.0, "age_y": 6.0, "age_group": "child", "patient_profile": "child_20kg"})
    mod.initialize(bus)
    n = int(T / dt)
    rows = []
    for i in range(n):
        bus.set(drug.input_key, drug.dose_value)
        mod.step(bus, dt)
        rows.append({
            "t_s": (i + 1) * dt,
            "drug": drug.name,
            "crrt_active": bool(crrt_active),
            "concentration": float(bus.get(drug.output_key)),
            "pk_crrt_extra_CL_L_min": float(bus.get("pk_crrt_total_extra_clearance_L_min")),
            "pk_crrt_midazolam_CL_L_min": float(bus.get("pk_crrt_midazolam_CL_L_min")),
            "pk_crrt_rocuronium_CL_L_min": float(bus.get("pk_crrt_rocuronium_CL_L_min")),
        })
    return {
        "drug": drug.name,
        "active": bool(crrt_active),
        "effluent_mL_kg_h": float(effluent if crrt_active else 0.0),
        "final_concentration": rows[-1]["concentration"],
        "peak_concentration": max(r["concentration"] for r in rows),
        "pk_crrt_active": bool(bus.get("pk_crrt_active")),
        "pk_crrt_effluent_L_min": float(bus.get("pk_crrt_effluent_L_min")),
        "pk_crrt_total_extra_clearance_L_min": float(bus.get("pk_crrt_total_extra_clearance_L_min")),
        "pk_crrt_midazolam_CL_L_min": float(bus.get("pk_crrt_midazolam_CL_L_min")),
        "pk_crrt_rocuronium_CL_L_min": float(bus.get("pk_crrt_rocuronium_CL_L_min")),
        "timeseries": rows,
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=str(OUTDIR_DEFAULT))
    ap.add_argument("--dt", type=float, default=10.0)
    ap.add_argument("--T", type=float, default=3600.0)
    ap.add_argument("--effluent", type=float, default=35.0)
    ap.add_argument("--fail-on-review", action="store_true")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    if not outdir.is_absolute():
        outdir = ROOT / outdir
    outdir.mkdir(parents=True, exist_ok=True)

    summaries = []
    timeseries = []
    paired = []
    status = "PASS"
    for drug in DRUGS:
        off = simulate(drug, False, 0.0, args.dt, args.T)
        on = simulate(drug, True, args.effluent, args.dt, args.T)
        summaries.extend([{k: v for k, v in off.items() if k != "timeseries"}, {k: v for k, v in on.items() if k != "timeseries"}])
        timeseries.extend(off["timeseries"]); timeseries.extend(on["timeseries"])
        reduction = 1.0 - (on["final_concentration"] / max(off["final_concentration"], 1e-12))
        expected_reduction = drug.name in {"midazolam", "rocuronium", "fentanyl", "dexmedetomidine"}
        ok = on["pk_crrt_active"] and on["pk_crrt_effluent_L_min"] > 0 and on["final_concentration"] <= off["final_concentration"] + 1e-9
        if not ok:
            status = "REVIEW"
        paired.append({
            "drug": drug.name,
            "off_final": off["final_concentration"],
            "on_final": on["final_concentration"],
            "relative_reduction": reduction,
            "direction_ok": ok,
            "expected_reduction": expected_reduction,
        })

    for name, rows in [("pkpd_crrt_clearance_v110_summary.csv", summaries), ("pkpd_crrt_clearance_v110_paired.csv", paired), ("pkpd_crrt_clearance_v110_timeseries.csv", timeseries)]:
        with (outdir / name).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)

    md = ["# CRRT-lite PK clearance audit — v1.10-alpha", "", f"Status: **{status}**", "", "Not for clinical use. Not a dosing model.", "", "| drug | off final | on final | relative reduction | status |", "|---|---:|---:|---:|---|"]
    for r in paired:
        md.append(f"| {r['drug']} | {r['off_final']:.4g} | {r['on_final']:.4g} | {100*r['relative_reduction']:.2f}% | {'PASS' if r['direction_ok'] else 'REVIEW'} |")
    (outdir / "pkpd_crrt_clearance_v110_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    payload = {
        "release": "v1.10-alpha",
        "status": status,
        "counts": {"summary_rows": len(summaries), "paired_rows": len(paired), "timeseries_rows": len(timeseries)},
        "paired": paired,
    }
    (outdir / "pkpd_crrt_clearance_v110_summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"release": payload["release"], "status": status, **payload["counts"]}, indent=2))
    return 1 if status != "PASS" and args.fail_on_review else 0

if __name__ == "__main__":
    raise SystemExit(main())
