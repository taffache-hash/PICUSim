#!/usr/bin/env python3
"""v1.20 adaptive V/Q dispersion audit.

Runs a compact set of respiratory/sepsis scenarios and checks that the public
three-zone gas-exchange model exposes transparent pathology drivers:
- ARDS/derecruitment should increase shunt and sigma;
- obstructive disease should increase dead-space and high V/Q burden;
- sepsis/shock should contribute perfusion heterogeneity;
- neonatal/RDS-like scenarios should expose the neonatal driver.

This is a software/educational plausibility audit, not external validation.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.simtools import run_scenario, write_json  # noqa: E402

DEFAULT_SCENARIOS = [
    "healthy_child_20kg",
    "ards_mild",
    "status_asthmaticus",
    "infant_bronchiolitis",
    "neonatal_rds_3kg",
    "septic_shock",
]

KEYS = [
    "vq_shunt_frac", "vq_deadspace_frac", "vq_exchange_frac", "vq_logsd",
    "vq_adaptive_sigma", "vq_ards_weight", "vq_obstruction_weight",
    "vq_shock_weight", "vq_neonatal_weight", "vq_pathology_driver",
    "vq_low_vq_burden", "vq_high_vq_burden", "PaO2", "PaCO2", "SaO2",
]


def final_row(df: pd.DataFrame, scenario: str) -> dict[str, Any]:
    last = df.iloc[-1]
    row: dict[str, Any] = {"scenario": scenario}
    for key in KEYS:
        if key in df.columns:
            val = last[key]
            try:
                row[key] = float(val)
            except Exception:
                row[key] = str(val)
        else:
            row[key] = None
    return row


def evaluate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by = {r["scenario"]: r for r in rows}
    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, value: Any = None, comparator: str = "") -> None:
        checks.append({"check": name, "status": "PASS" if ok else "REVIEW", "value": value, "comparator": comparator})

    healthy = by.get("healthy_child_20kg", {})
    ards = by.get("ards_mild", {})
    asthma = by.get("status_asthmaticus", {})
    bronchio = by.get("infant_bronchiolitis", {})
    neonatal = by.get("neonatal_rds_3kg", {})
    septic = by.get("septic_shock", {})

    h_sigma = float(healthy.get("vq_adaptive_sigma") or 0.0)
    h_shunt = float(healthy.get("vq_shunt_frac") or 0.0)
    h_dead = float(healthy.get("vq_deadspace_frac") or 0.0)

    add("ards_sigma_above_healthy", float(ards.get("vq_adaptive_sigma") or 0.0) > h_sigma, ards.get("vq_adaptive_sigma"), f"> {h_sigma:.3f}")
    add("ards_shunt_above_healthy", float(ards.get("vq_shunt_frac") or 0.0) > h_shunt, ards.get("vq_shunt_frac"), f"> {h_shunt:.3f}")
    add("ards_driver_present", float(ards.get("vq_ards_weight") or 0.0) >= 0.25, ards.get("vq_ards_weight"), ">= 0.25")

    add("asthma_deadspace_above_healthy", float(asthma.get("vq_deadspace_frac") or 0.0) > h_dead, asthma.get("vq_deadspace_frac"), f"> {h_dead:.3f}")
    add("asthma_obstruction_driver_present", float(asthma.get("vq_obstruction_weight") or 0.0) >= 0.25, asthma.get("vq_obstruction_weight"), ">= 0.25")
    add("bronchiolitis_obstruction_driver_present", float(bronchio.get("vq_obstruction_weight") or 0.0) >= 0.25, bronchio.get("vq_obstruction_weight"), ">= 0.25")

    add("neonatal_driver_present", float(neonatal.get("vq_neonatal_weight") or 0.0) >= 0.25, neonatal.get("vq_neonatal_weight"), ">= 0.25")
    add("septic_shock_driver_present", float(septic.get("vq_shock_weight") or 0.0) >= 0.15, septic.get("vq_shock_weight"), ">= 0.15")
    add("adaptive_revision_written", all(float(r.get("vq_adaptive_sigma") or 0.0) > 0 for r in rows), "all rows", "> 0")
    return checks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", nargs="*", default=DEFAULT_SCENARIOS)
    ap.add_argument("--dt", type=float, default=10.0)
    ap.add_argument("--outdir", default=str(ROOT / "outputs" / "vq_adaptive_dispersion_v1.20"))
    ap.add_argument("--fail-on-review", action="store_true")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for scenario in args.scenarios:
        try:
            _, df = run_scenario(scenario, dt=args.dt, quiet=True)
            rows.append(final_row(df, scenario))
        except Exception as exc:  # represented in outputs
            errors.append({"scenario": scenario, "error": repr(exc)})

    checks = evaluate(rows) if not errors else []
    pd.DataFrame(rows).to_csv(outdir / "vq_adaptive_dispersion_summary_v120.csv", index=False)
    pd.DataFrame(checks).to_csv(outdir / "vq_adaptive_dispersion_checks_v120.csv", index=False)
    if errors:
        pd.DataFrame(errors).to_csv(outdir / "vq_adaptive_dispersion_errors_v120.csv", index=False)

    status = "PASS" if not errors and all(c["status"] == "PASS" for c in checks) else "REVIEW"
    summary = {
        "release": "v1.20-alpha",
        "status": status,
        "scenarios": len(rows),
        "checks": len(checks),
        "review_items": sum(c["status"] == "REVIEW" for c in checks),
        "errors": len(errors),
    }
    write_json(summary, outdir / "vq_adaptive_dispersion_summary_v120.json")
    report = [
        "# PDT v1.20 Adaptive V/Q Dispersion Audit", "",
        "This is a software plausibility audit, not clinical validation.", "",
        f"Status: **{status}**", "",
        "## Scenario final values", "",
        pd.DataFrame(rows).to_markdown(index=False) if rows else "No rows.", "",
        "## Checks", "",
        pd.DataFrame(checks).to_markdown(index=False) if checks else "No checks.", "",
    ]
    (outdir / "vq_adaptive_dispersion_report_v120.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if args.fail_on_review and status != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
