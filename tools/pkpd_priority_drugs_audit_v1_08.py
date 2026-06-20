#!/usr/bin/env python3
"""Priority PICU drug PK/PD audit — v1.08-alpha.

Runs a small isolated PharmacologyModule simulation for adrenaline, dopamine,
fentanyl and dexmedetomidine across the five pediatric profiles. This is a
numerical smoke/plausibility audit, not external validation and not dosing
advice.
"""
from __future__ import annotations

import argparse, csv, json, sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bus import BusState, PhysiologicalBus  # noqa: E402
from core.profiles import load_profiles  # noqa: E402
from modules.pharmacology.pk_pd import PharmacologyModule  # noqa: E402

OUTDIR_DEFAULT = ROOT / "outputs" / "pkpd_priority_drugs_v1.08"

@dataclass(frozen=True)
class DrugSpec:
    name: str
    input_key: str
    output_key: str
    dose_value: float
    dose_unit: str
    expected_modifier: str
    direction: str

DRUGS = (
    DrugSpec("adrenaline", "adrenaline_mcg_kg_min", "C_adrenaline_ng_mL", 0.05, "mcg/kg/min", "drug_HR_mod", "increase"),
    DrugSpec("dopamine", "dopamine_mcg_kg_min", "C_dopamine_ng_mL", 5.0, "mcg/kg/min", "drug_HR_mod", "increase"),
    DrugSpec("fentanyl", "fentanyl_mcg_kg_h", "C_fentanyl_ng_mL", 2.0, "mcg/kg/h", "drug_drive_mod", "decrease"),
    DrugSpec("dexmedetomidine", "dexmedetomidine_mcg_kg_h", "C_dexmedetomidine_ng_mL", 0.7, "mcg/kg/h", "drug_drive_mod", "decrease"),
)


def _f(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def simulate(drug: DrugSpec, profile_name: str, profile: dict[str, Any], dt: float = 5.0, T: float = 900.0) -> dict[str, Any]:
    wt = _f(profile.get("weight_kg"), 20.0)
    age_y = _f(profile.get("age_y"), 6.0)
    age_group = str(profile.get("age_group", "child"))
    bus = PhysiologicalBus(BusState(weight_kg=wt, age_y=age_y))
    mod = PharmacologyModule({"weight_kg": wt, "age_y": age_y, "age_group": age_group, "patient_profile": profile_name})
    mod.initialize(bus)

    n = int(T / dt)
    concs = []
    mods = []
    for _ in range(n):
        bus.set(drug.input_key, drug.dose_value)
        mod.step(bus, dt)
        concs.append(float(bus.get(drug.output_key)))
        mods.append(float(bus.get(drug.expected_modifier)))

    c = np.asarray(concs, dtype=float)
    m = np.asarray(mods, dtype=float)
    final_mod = float(m[-1])
    baseline = 1.0
    if drug.direction == "increase":
        direction_ok = final_mod > baseline + 1e-4
    else:
        direction_ok = final_mod < baseline - 1e-4
    return {
        "drug": drug.name,
        "profile": profile_name,
        "weight_kg": wt,
        "dose": drug.dose_value,
        "dose_unit": drug.dose_unit,
        "output_key": drug.output_key,
        "c_final": float(c[-1]),
        "c_peak": float(np.max(c)),
        "modifier": drug.expected_modifier,
        "modifier_final": final_mod,
        "direction": drug.direction,
        "direction_ok": bool(direction_ok),
        "finite_nonnegative": bool(np.isfinite(c).all() and np.min(c) >= -1e-12),
        "pk_supported_drug_count": int(bus.get("pk_supported_drug_count")),
        "pk_extension_revision": int(bus.get("pk_extension_revision")),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=str(OUTDIR_DEFAULT))
    ap.add_argument("--dt", type=float, default=5.0)
    ap.add_argument("--fail-on-review", action="store_true")
    args = ap.parse_args()
    outdir = Path(args.outdir)
    if not outdir.is_absolute():
        outdir = ROOT / outdir
    outdir.mkdir(parents=True, exist_ok=True)

    profiles = load_profiles()
    rows = [simulate(drug, pname, pdata, args.dt) for drug in DRUGS for pname, pdata in profiles.items()]
    status = "PASS" if all(r["finite_nonnegative"] and r["direction_ok"] and r["pk_extension_revision"] == 108 for r in rows) else "REVIEW"

    csv_path = outdir / "pkpd_priority_drugs_v108_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    md = ["# Priority PICU drug audit — v1.08-alpha", "", f"Status: **{status}**", "", f"Rows: {len(rows)}", "", "Not for clinical use. Not a dosing model.", "", "| drug | profile | peak concentration | final modifier | status |", "|---|---|---:|---:|---|"]
    for r in rows:
        md.append(f"| {r['drug']} | {r['profile']} | {r['c_peak']:.4g} | {r['modifier_final']:.3f} | {'PASS' if r['direction_ok'] else 'REVIEW'} |")
    (outdir / "pkpd_priority_drugs_v108_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    payload = {"release": "v1.08-alpha", "status": status, "rows": rows, "csv": str(csv_path)}
    (outdir / "pkpd_priority_drugs_v108_summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"release": payload["release"], "status": status, "rows": len(rows)}, indent=2))
    return 1 if status != "PASS" and args.fail_on_review else 0

if __name__ == "__main__":
    raise SystemExit(main())
