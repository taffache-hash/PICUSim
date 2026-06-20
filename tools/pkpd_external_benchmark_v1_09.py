#!/usr/bin/env python3
"""
PK/PD external benchmark scaffold — v1.09-alpha
================================================

Preliminary literature-parameter benchmark harness for the PDT pharmacology module.
It compares selected parent-drug PK parameters against broad literature-derived
anchors and generates concentration-time curves for the source-like regimens.

This is not formal clinical validation and is not a dosing tool.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bus import BusState, PhysiologicalBus  # noqa: E402
from core.profiles import load_profiles  # noqa: E402
from modules.pharmacology.pk_pd import PharmacologyModule  # noqa: E402

SPEC_DEFAULT = ROOT / "data" / "pkpd_external_benchmarks_v1.09.yaml"
OUTDIR_DEFAULT = ROOT / "outputs" / "pkpd_external_benchmark_v1.09"


def _safe_float(x: Any, default: float = float("nan")) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _new_module(profile_name: str, profile: dict[str, Any]) -> tuple[PharmacologyModule, PhysiologicalBus]:
    weight_kg = _safe_float(profile.get("weight_kg", 20.0), 20.0)
    age_y = _safe_float(profile.get("age_y", 6.0), 6.0)
    age_group = str(profile.get("age_group", "child"))
    bus = PhysiologicalBus(BusState(weight_kg=weight_kg, age_y=age_y))
    module = PharmacologyModule(
        {
            "weight_kg": weight_kg,
            "age_y": age_y,
            "age_group": age_group,
            "patient_profile": profile_name,
        }
    )
    module.initialize(bus)
    return module, bus


def _pk_metrics(module: PharmacologyModule, drug: str, weight_kg: float) -> dict[str, float]:
    """Extract transparent parent-drug PK metrics from module instances."""
    wt = max(float(weight_kg), 0.5)
    if drug == "midazolam":
        pk = module._pk_mid
    elif drug == "ketamine":
        pk = module._pk_ket
    else:
        raise ValueError(f"Unsupported v1.09 external benchmark drug: {drug}")

    metrics: dict[str, float] = {}
    if hasattr(pk, "Vd1") and hasattr(pk, "Vd2"):
        CL_L_min = float(pk.k10) * float(pk.Vd1) * 60.0
        Q12_L_min = float(pk.k12) * float(pk.Vd1) * 60.0
        Q21_L_min = float(pk.k21) * float(pk.Vd2) * 60.0
        metrics.update(
            {
                "CL_L_min": CL_L_min,
                "CL_mL_kg_min": CL_L_min * 1000.0 / wt,
                "V1_L": float(pk.Vd1),
                "V2_L": float(pk.Vd2),
                "V1_L_kg": float(pk.Vd1) / wt,
                "V2_L_kg": float(pk.Vd2) / wt,
                "V_total_L": float(pk.Vd1) + float(pk.Vd2),
                "V_total_L_kg": (float(pk.Vd1) + float(pk.Vd2)) / wt,
                "Q12_L_min": Q12_L_min,
                "Q21_L_min": Q21_L_min,
                "k10_s": float(pk.k10),
                "k12_s": float(pk.k12),
                "k21_s": float(pk.k21),
            }
        )
    else:
        CL_L_min = float(pk.k_elim) * float(pk.Vd) * 60.0
        metrics.update(
            {
                "CL_L_min": CL_L_min,
                "CL_mL_kg_min": CL_L_min * 1000.0 / wt,
                "Vd_L": float(pk.Vd),
                "Vd_L_kg": float(pk.Vd) / wt,
                "k_elim_s": float(pk.k_elim),
            }
        )
    return metrics


def _evaluate_parameter_targets(
    benchmark_id: str,
    benchmark: dict[str, Any],
    profile_name: str,
    profile: dict[str, Any],
    metrics: dict[str, float],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    supported = set(benchmark.get("supported_profiles") or [])
    profile_supported = (not supported) or profile_name in supported
    for metric_name, target in (benchmark.get("parameter_targets") or {}).items():
        lo, hi = target.get("range", [None, None])
        value = _safe_float(metrics.get(metric_name))
        if not profile_supported:
            status = "SKIP_UNSUPPORTED_PROFILE"
        elif math.isfinite(value) and lo is not None and hi is not None and float(lo) <= value <= float(hi):
            status = "PASS"
        else:
            status = "REVIEW"
        rows.append(
            {
                "benchmark_id": benchmark_id,
                "drug": benchmark.get("drug"),
                "source_id": benchmark.get("source_id"),
                "profile": profile_name,
                "age_group": profile.get("age_group"),
                "age_y": profile.get("age_y"),
                "weight_kg": profile.get("weight_kg"),
                "metric": metric_name,
                "value": value,
                "target_low": lo,
                "target_high": hi,
                "target_type": target.get("target_type", ""),
                "status": status,
                "note": target.get("note", ""),
            }
        )
    return rows


def _simulate_regimen(
    benchmark_id: str,
    benchmark: dict[str, Any],
    regimen_id: str,
    regimen: dict[str, Any],
    profile_name: str,
    profile: dict[str, Any],
    dt: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    module, bus = _new_module(profile_name, profile)
    dose_key = str(regimen["dose_key"])
    dose_value = float(regimen["dose_value"])
    duration_s = float(regimen.get("duration_s", 3600.0))
    washout_s = float(regimen.get("washout_s", 3600.0))
    output_key = str(benchmark["output_key"])
    total_s = duration_s + washout_s
    steps = int(total_s / dt)
    rows: list[dict[str, Any]] = []
    peak = 0.0
    c_end = 0.0
    c_washout_end = 0.0
    auc = 0.0
    prev_t = 0.0
    prev_c = 0.0

    for step in range(steps + 1):
        t = step * dt
        dose = dose_value if t <= duration_s else 0.0
        bus.set(dose_key, dose)
        module.step(bus, dt)
        bus.set("t", t)
        c = float(bus.get(output_key))
        peak = max(peak, c)
        if abs(t - duration_s) <= dt / 2:
            c_end = c
        if step > 0 and prev_t <= duration_s:
            auc += 0.5 * (prev_c + c) * (t - prev_t) / 60.0
        prev_t, prev_c = t, c
        c_washout_end = c
        rows.append(
            {
                "benchmark_id": benchmark_id,
                "regimen_id": regimen_id,
                "drug": benchmark.get("drug"),
                "profile": profile_name,
                "t_s": round(float(t), 6),
                "dose_key": dose_key,
                "dose_value": dose,
                "dose_unit": regimen.get("dose_unit", ""),
                "output_key": output_key,
                "concentration": c,
            }
        )

    finite = all(math.isfinite(float(r["concentration"])) and float(r["concentration"]) >= -1e-12 for r in rows)
    rises = c_end > 0 and peak >= c_end * 0.95
    falls = c_washout_end < c_end if c_end > 0 else False
    status = "PASS" if finite and rises and falls else "REVIEW"
    summary = {
        "benchmark_id": benchmark_id,
        "regimen_id": regimen_id,
        "drug": benchmark.get("drug"),
        "profile": profile_name,
        "dose_value": dose_value,
        "dose_unit": regimen.get("dose_unit", ""),
        "duration_s": duration_s,
        "washout_s": washout_s,
        "output_key": output_key,
        "c_end_infusion": c_end,
        "c_peak": peak,
        "auc_during_infusion_conc_min": auc,
        "c_end_washout": c_washout_end,
        "finite_nonnegative": finite,
        "rises_during_infusion": rises,
        "decreases_after_stop": falls,
        "status": status,
    }
    return rows, summary


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_benchmark(spec_path: Path, outdir: Path, dt: float) -> dict[str, Any]:
    spec = yaml.safe_load(spec_path.read_text())
    profiles = load_profiles()
    outdir.mkdir(parents=True, exist_ok=True)

    parameter_rows: list[dict[str, Any]] = []
    regimen_rows: list[dict[str, Any]] = []
    regimen_summary_rows: list[dict[str, Any]] = []
    metric_snapshot_rows: list[dict[str, Any]] = []

    for benchmark_id, benchmark in (spec.get("benchmarks") or {}).items():
        drug = str(benchmark.get("drug"))
        for profile_name, profile in profiles.items():
            module, _bus = _new_module(profile_name, profile)
            metrics = _pk_metrics(module, drug, float(profile.get("weight_kg", 20.0)))
            snapshot = {
                "benchmark_id": benchmark_id,
                "drug": drug,
                "profile": profile_name,
                "age_group": profile.get("age_group"),
                "age_y": profile.get("age_y"),
                "weight_kg": profile.get("weight_kg"),
                **metrics,
            }
            metric_snapshot_rows.append(snapshot)
            parameter_rows.extend(_evaluate_parameter_targets(benchmark_id, benchmark, profile_name, profile, metrics))

            supported = set(benchmark.get("supported_profiles") or [])
            if supported and profile_name not in supported:
                continue
            for regimen_id, regimen in (benchmark.get("regimen_checks") or {}).items():
                rows, summary = _simulate_regimen(benchmark_id, benchmark, regimen_id, regimen, profile_name, profile, dt)
                regimen_rows.extend(rows)
                regimen_summary_rows.append(summary)

    review_parameter = [r for r in parameter_rows if r["status"] == "REVIEW"]
    review_regimen = [r for r in regimen_summary_rows if r["status"] == "REVIEW"]
    status = "PASS" if not review_parameter and not review_regimen else "REVIEW"
    payload = {
        "release": "v1.09-alpha",
        "status": status,
        "spec_file": str(spec_path.relative_to(ROOT) if spec_path.is_relative_to(ROOT) else spec_path),
        "dt_s": dt,
        "sources": spec.get("sources", {}),
        "parameter_rows": parameter_rows,
        "metric_snapshot_rows": metric_snapshot_rows,
        "regimen_summary_rows": regimen_summary_rows,
        "counts": {
            "parameter_rows": len(parameter_rows),
            "metric_snapshot_rows": len(metric_snapshot_rows),
            "regimen_summary_rows": len(regimen_summary_rows),
            "regimen_timeseries_rows": len(regimen_rows),
            "review_parameter_rows": len(review_parameter),
            "review_regimen_rows": len(review_regimen),
        },
    }

    _write_csv(outdir / "pkpd_external_parameter_checks.csv", parameter_rows)
    _write_csv(outdir / "pkpd_external_parameter_snapshots.csv", metric_snapshot_rows)
    _write_csv(outdir / "pkpd_external_regimen_summary.csv", regimen_summary_rows)
    _write_csv(outdir / "pkpd_external_regimen_timeseries.csv", regimen_rows)
    (outdir / "pkpd_external_benchmark_summary.json").write_text(json.dumps(payload, indent=2))

    report_lines = [
        "# PK/PD external benchmark scaffold — v1.09-alpha",
        "",
        f"Status: **{status}**",
        "",
        "This is a preliminary parameter-envelope benchmark, not formal clinical validation and not a dosing tool.",
        "",
        "## Counts",
    ]
    for key, value in payload["counts"].items():
        report_lines.append(f"- {key}: {value}")
    report_lines.extend(["", "## Sources"])
    for sid, source in (spec.get("sources") or {}).items():
        report_lines.append(f"- `{sid}`: {source.get('title')} ({source.get('year')}); PMID {source.get('pmid')}; DOI {source.get('doi')}")
    report_lines.extend(["", "## Parameter checks"])
    for row in parameter_rows:
        if row["status"] != "SKIP_UNSUPPORTED_PROFILE":
            report_lines.append(
                f"- {row['benchmark_id']} / {row['profile']} / {row['metric']}: "
                f"{float(row['value']):.4g} within [{row['target_low']}, {row['target_high']}] → {row['status']}"
            )
    (outdir / "pkpd_external_benchmark_report.md").write_text("\n".join(report_lines) + "\n")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=SPEC_DEFAULT)
    parser.add_argument("--outdir", type=Path, default=OUTDIR_DEFAULT)
    parser.add_argument("--dt", type=float, default=60.0)
    parser.add_argument("--fail-on-review", action="store_true")
    args = parser.parse_args(argv)
    payload = run_benchmark(args.spec, args.outdir, args.dt)
    print(json.dumps({"release": payload["release"], "status": payload["status"], "counts": payload["counts"]}, indent=2))
    if args.fail_on_review and payload["status"] != "PASS":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
