#!/usr/bin/env python3
"""
PK/PD internal validation harness — v1.02-alpha
================================================

Runs isolated PharmacologyModule simulations across the five pediatric
reference profiles and compares the v1.01 allometric PK scaling against a
legacy-linear reference (volume ∝ W, clearance ∝ W, no maturation factor).

This is an internal numerical plausibility audit. It is not external clinical
validation and must not be used for dosing or bedside inference.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
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

OUTDIR_DEFAULT = ROOT / "outputs" / "pkpd_validation_v1.02"


@dataclass(frozen=True)
class DrugAuditSpec:
    name: str
    input_key: str
    output_key: str
    dose_value: float
    dose_unit: str
    concentration_unit: str
    on_duration_s: float = 3600.0
    washout_s: float = 1800.0


DRUGS: tuple[DrugAuditSpec, ...] = (
    DrugAuditSpec(
        name="ketamine",
        input_key="ketamine_mg_kg_h",
        output_key="C_ketamine_mg_L",
        dose_value=1.0,
        dose_unit="mg/kg/h",
        concentration_unit="mg/L",
    ),
    DrugAuditSpec(
        name="midazolam",
        input_key="midazolam_mcg_kg_h",
        output_key="C_midazolam_ng_mL",
        dose_value=100.0,
        dose_unit="mcg/kg/h",
        concentration_unit="ng/mL",
    ),
    DrugAuditSpec(
        name="propofol",
        input_key="propofol_mg_kg_h",
        output_key="C_propofol_mg_L",
        dose_value=4.0,
        dose_unit="mg/kg/h",
        concentration_unit="mg/L",
    ),
    DrugAuditSpec(
        name="rocuronium",
        input_key="rocuronium_mg_kg_h",
        output_key="C_rocuronium_ng_mL",
        dose_value=0.6,
        dose_unit="mg/kg/h",
        concentration_unit="ng/mL",
    ),
    DrugAuditSpec(
        name="noradrenaline",
        input_key="norad_mcg_kg_min",
        output_key="C_norad_ng_mL",
        dose_value=0.10,
        dose_unit="mcg/kg/min",
        concentration_unit="ng/mL",
    ),
)


MODEL_PRESETS: dict[str, dict[str, Any]] = {
    "allometric_v1.01": {
        "pk_volume_exponent": 1.0,
        "pk_clearance_exponent": 0.75,
        "pk_intercompartment_exponent": 0.75,
        "pk_apply_maturation": True,
    },
    "legacy_linear_reference": {
        "pk_volume_exponent": 1.0,
        "pk_clearance_exponent": 1.0,
        "pk_intercompartment_exponent": 1.0,
        "pk_apply_maturation": False,
    },
}


def _safe_float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")


def _index_at(times: np.ndarray, target_s: float) -> int:
    return int(np.argmin(np.abs(times - target_s)))


def simulate_drug_profile(
    drug: DrugAuditSpec,
    profile_name: str,
    profile: dict[str, Any],
    preset_name: str,
    preset_params: dict[str, Any],
    dt: float,
) -> dict[str, Any]:
    """Run one isolated PK/PD simulation and return timeseries + summary."""
    weight_kg = _safe_float(profile.get("weight_kg", 20.0))
    age_y = _safe_float(profile.get("age_y", 6.0))
    age_group = str(profile.get("age_group", "child"))

    bus = PhysiologicalBus(BusState(weight_kg=weight_kg, age_y=age_y))
    module = PharmacologyModule(
        {
            "weight_kg": weight_kg,
            "age_y": age_y,
            "age_group": age_group,
            "patient_profile": profile_name,
            **preset_params,
        }
    )
    module.initialize(bus)

    total_s = drug.on_duration_s + drug.washout_s
    steps = int(total_s / dt)
    times: list[float] = []
    concs: list[float] = []
    doses: list[float] = []

    for step in range(steps + 1):
        t = step * dt
        dose = drug.dose_value if t <= drug.on_duration_s else 0.0
        bus.set(drug.input_key, dose)
        module.step(bus, dt)
        bus.set("t", t)
        times.append(t)
        concs.append(float(bus.get(drug.output_key)))
        doses.append(dose)

    t_arr = np.asarray(times, dtype=float)
    c_arr = np.asarray(concs, dtype=float)
    on_mask = t_arr <= drug.on_duration_s
    washout_mask = t_arr > drug.on_duration_s

    idx_15m = _index_at(t_arr, 900.0)
    idx_30m = _index_at(t_arr, 1800.0)
    idx_60m = _index_at(t_arr, drug.on_duration_s)
    idx_washout_30m = _index_at(t_arr, drug.on_duration_s + 1800.0)

    auc_on = float(np.trapezoid(c_arr[on_mask], t_arr[on_mask]) / 60.0)  # conc * min
    c_end = float(c_arr[idx_60m])
    c_washout_30m = float(c_arr[idx_washout_30m])
    washout_drop_fraction = float((c_end - c_washout_30m) / c_end) if c_end > 0 else float("nan")

    finite_nonnegative = bool(np.isfinite(c_arr).all() and np.min(c_arr) >= -1e-12)
    rises_during_infusion = bool(c_arr[idx_60m] >= c_arr[idx_15m] >= -1e-12)
    decreases_after_stop = bool(c_washout_30m < c_end) if c_end > 0 else False

    summary = {
        "drug": drug.name,
        "model": preset_name,
        "profile": profile_name,
        "age_group": age_group,
        "age_y": age_y,
        "weight_kg": weight_kg,
        "dose_value": drug.dose_value,
        "dose_unit": drug.dose_unit,
        "concentration_unit": drug.concentration_unit,
        "maturation_factor": float(bus.get("pk_scaling_maturation_factor")),
        "c_15min": float(c_arr[idx_15m]),
        "c_30min": float(c_arr[idx_30m]),
        "c_60min": c_end,
        "auc_0_60min": auc_on,
        "c_30min_after_stop": c_washout_30m,
        "washout_drop_fraction": washout_drop_fraction,
        "finite_nonnegative": finite_nonnegative,
        "rises_during_infusion": rises_during_infusion,
        "decreases_after_stop": decreases_after_stop,
        "status": "PASS" if finite_nonnegative and rises_during_infusion and decreases_after_stop else "REVIEW",
    }

    rows = [
        {
            "drug": drug.name,
            "model": preset_name,
            "profile": profile_name,
            "t_s": float(t),
            "dose": float(d),
            "concentration": float(c),
            "concentration_unit": drug.concentration_unit,
        }
        for t, d, c in zip(times, doses, concs)
    ]
    return {"summary": summary, "timeseries": rows}


def build_cross_model_ratios(summary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compare allometric_v1.01 vs legacy_linear_reference for each drug/profile."""
    by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in summary_rows:
        by_key[(row["drug"], row["profile"], row["model"])] = row

    ratio_rows: list[dict[str, Any]] = []
    for drug in sorted({r["drug"] for r in summary_rows}):
        for profile in sorted({r["profile"] for r in summary_rows}):
            allo = by_key.get((drug, profile, "allometric_v1.01"))
            lin = by_key.get((drug, profile, "legacy_linear_reference"))
            if not allo or not lin:
                continue
            c_ratio = float(allo["c_60min"] / lin["c_60min"]) if lin["c_60min"] else float("nan")
            auc_ratio = float(allo["auc_0_60min"] / lin["auc_0_60min"]) if lin["auc_0_60min"] else float("nan")
            ratio_rows.append(
                {
                    "drug": drug,
                    "profile": profile,
                    "age_group": allo["age_group"],
                    "weight_kg": allo["weight_kg"],
                    "maturation_factor": allo["maturation_factor"],
                    "c60_allometric_over_linear": c_ratio,
                    "auc_allometric_over_linear": auc_ratio,
                    "status": "PASS" if math.isfinite(c_ratio) and math.isfinite(auc_ratio) else "REVIEW",
                }
            )
    return ratio_rows


def build_profile_gradient(summary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Summarize profile-level C60 relative to child_20kg for the allometric model."""
    allometric = [r for r in summary_rows if r["model"] == "allometric_v1.01"]
    child_by_drug = {r["drug"]: r for r in allometric if r["profile"] == "child_20kg"}
    rows: list[dict[str, Any]] = []
    for row in allometric:
        child = child_by_drug.get(row["drug"])
        if not child or child["c_60min"] <= 0:
            rel = float("nan")
        else:
            rel = float(row["c_60min"] / child["c_60min"])
        rows.append(
            {
                "drug": row["drug"],
                "profile": row["profile"],
                "age_group": row["age_group"],
                "weight_kg": row["weight_kg"],
                "maturation_factor": row["maturation_factor"],
                "c60_relative_to_child_20kg": rel,
                "auc_relative_to_child_20kg": float(row["auc_0_60min"] / child["auc_0_60min"]) if child and child["auc_0_60min"] > 0 else float("nan"),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _fmt(x: Any, digits: int = 3) -> str:
    try:
        val = float(x)
    except Exception:
        return str(x)
    if not math.isfinite(val):
        return "NA"
    if abs(val) >= 1000:
        return f"{val:.1f}"
    if abs(val) >= 10:
        return f"{val:.2f}"
    return f"{val:.{digits}f}"


def write_markdown_report(
    path: Path,
    summary_rows: list[dict[str, Any]],
    ratio_rows: list[dict[str, Any]],
    gradient_rows: list[dict[str, Any]],
) -> None:
    pass_count = sum(1 for r in summary_rows if r["status"] == "PASS")
    review_count = sum(1 for r in summary_rows if r["status"] != "PASS")

    lines: list[str] = []
    lines += [
        "# PK/PD internal validation — v1.02-alpha",
        "",
        "This report is an internal numerical plausibility audit for the v1.01 PK/PD allometric scaling patch.",
        "It is not external clinical validation and is not suitable for dosing, patient-specific inference, or bedside decision support.",
        "",
        "## Scope",
        "",
        "The harness runs each core drug in isolation across the five pediatric reference profiles and compares two parameterizations:",
        "",
        "- `allometric_v1.01`: volumes scale approximately with W^1.0; clearances and inter-compartmental flows scale with W^0.75 and a transparent maturation factor.",
        "- `legacy_linear_reference`: volumes and clearances scale linearly with weight; no maturation factor.",
        "",
        f"Summary rows: {len(summary_rows)}. PASS: {pass_count}. REVIEW: {review_count}.",
        "",
    ]

    lines += [
        "## Numerical safety checks",
        "",
        "| drug | model | profile | C60 | unit | AUC 0-60 min | washout drop | status |",
        "|---|---|---:|---:|---|---:|---:|---|",
    ]
    for r in sorted(summary_rows, key=lambda x: (x["drug"], x["model"], x["weight_kg"])):
        lines.append(
            f"| {r['drug']} | {r['model']} | {r['profile']} | {_fmt(r['c_60min'])} | {r['concentration_unit']} | "
            f"{_fmt(r['auc_0_60min'])} | {_fmt(r['washout_drop_fraction'])} | {r['status']} |"
        )

    lines += [
        "",
        "## Allometric vs legacy-linear ratios",
        "",
        "Values above 1.0 mean that the allometric/maturation model produces higher exposure than the legacy-linear reference for the same weight-normalized infusion.",
        "",
        "| drug | profile | weight kg | maturation | C60 ratio | AUC ratio |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in sorted(ratio_rows, key=lambda x: (x["drug"], x["weight_kg"])):
        lines.append(
            f"| {r['drug']} | {r['profile']} | {_fmt(r['weight_kg'])} | {_fmt(r['maturation_factor'])} | "
            f"{_fmt(r['c60_allometric_over_linear'])} | {_fmt(r['auc_allometric_over_linear'])} |"
        )

    lines += [
        "",
        "## Allometric profile gradient relative to child_20kg",
        "",
        "| drug | profile | weight kg | maturation | C60 / child_20kg | AUC / child_20kg |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in sorted(gradient_rows, key=lambda x: (x["drug"], x["weight_kg"])):
        lines.append(
            f"| {r['drug']} | {r['profile']} | {_fmt(r['weight_kg'])} | {_fmt(r['maturation_factor'])} | "
            f"{_fmt(r['c60_relative_to_child_20kg'])} | {_fmt(r['auc_relative_to_child_20kg'])} |"
        )

    lines += [
        "",
        "## Interpretation",
        "",
        "- The audit checks numerical behavior only: non-negative finite concentrations, concentration rise during infusion, and concentration fall after stopping infusion.",
        "- The profile-gradient tables are designed to expose the consequence of the allometric choice rather than to claim clinical correctness.",
        "- The next required step is external benchmarking against published pediatric PK concentration-time data for at least midazolam and ketamine.",
        "",
    ]
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dt", type=float, default=1.0, help="Time step in seconds.")
    parser.add_argument("--outdir", type=Path, default=OUTDIR_DEFAULT)
    parser.add_argument("--fail-on-review", action="store_true")
    args = parser.parse_args()

    if args.dt <= 0 or args.dt > 10:
        raise ValueError("dt must be >0 and <=10 s for this audit")

    profiles = load_profiles()
    outdir = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    summary_rows: list[dict[str, Any]] = []
    timeseries_rows: list[dict[str, Any]] = []

    for drug in DRUGS:
        for profile_name, profile in profiles.items():
            for preset_name, preset_params in MODEL_PRESETS.items():
                result = simulate_drug_profile(drug, profile_name, profile, preset_name, preset_params, args.dt)
                summary_rows.append(result["summary"])
                timeseries_rows.extend(result["timeseries"])

    ratio_rows = build_cross_model_ratios(summary_rows)
    gradient_rows = build_profile_gradient(summary_rows)

    write_csv(outdir / "pkpd_internal_validation_summary.csv", summary_rows)
    write_csv(outdir / "pkpd_internal_validation_ratios.csv", ratio_rows)
    write_csv(outdir / "pkpd_internal_validation_profile_gradient.csv", gradient_rows)
    write_csv(outdir / "pkpd_internal_validation_timeseries.csv", timeseries_rows)

    payload = {
        "release": "v1.02-alpha",
        "purpose": "internal PK/PD numerical plausibility audit",
        "disclaimer": "not external clinical validation; not for dosing or clinical use",
        "dt_s": args.dt,
        "drugs": [d.__dict__ for d in DRUGS],
        "models": MODEL_PRESETS,
        "summary": summary_rows,
        "ratios": ratio_rows,
        "profile_gradient": gradient_rows,
        "status": "PASS" if all(r["status"] == "PASS" for r in summary_rows) else "REVIEW",
    }
    (outdir / "pkpd_internal_validation_summary.json").write_text(json.dumps(payload, indent=2))
    write_markdown_report(outdir / "pkpd_internal_validation_report.md", summary_rows, ratio_rows, gradient_rows)

    print(json.dumps({
        "release": payload["release"],
        "status": payload["status"],
        "summary_rows": len(summary_rows),
        "ratio_rows": len(ratio_rows),
        "outdir": str(outdir),
    }, indent=2))

    if args.fail_on_review and payload["status"] != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
