#!/usr/bin/env python3
"""Representative scenario audit for v1.06 public three-zone V/Q gas exchange."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import ScenarioLoader
from run_simulation import build_twin

SCENARIOS = [
    "healthy_child_20kg.yaml",
    "ards_mild.yaml",
    "status_asthmaticus.yaml",
    "neonatal_rds_3kg.yaml",
]

FIELDS = [
    "SaO2", "PaO2", "PaCO2", "vq_shunt_frac", "vq_deadspace_frac",
    "vq_exchange_frac", "vq_logsd", "vq_low_vq_burden", "vq_high_vq_burden",
    "alveolar_ventilation_L_min", "recruited_frac", "Vt", "RR",
]


def run_scenario(scenario: str, until_s: float, dt: float) -> dict:
    loader = ScenarioLoader.from_yaml(str(ROOT / "scenarios" / scenario))
    bus = loader.build_bus()
    engine = build_twin(bus, loader.config, dt=dt)
    engine.verbose = False
    engine.add_perturbations(loader.build_perturbations())
    df = engine.run(until_s)
    last = df.iloc[-1]
    row = {"scenario": scenario, "until_s": until_s, "dt": dt}
    for f in FIELDS:
        if f in df.columns:
            row[f] = float(last[f])
    row["status"] = "PASS" if 0.0 <= row.get("vq_shunt_frac", -1) <= 0.85 and 0.0 <= row.get("vq_deadspace_frac", -1) <= 0.90 else "FAIL"
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=str(ROOT / "outputs" / "vq_audit_v1.06"))
    ap.add_argument("--until-s", type=float, default=60.0)
    ap.add_argument("--dt", type=float, default=1.0)
    args = ap.parse_args()

    rows = [run_scenario(s, args.until_s, args.dt) for s in SCENARIOS]
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(outdir / "vq_three_zone_audit_summary.csv", index=False)
    (outdir / "vq_three_zone_audit_summary.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")

    lines = ["# v1.06 three-zone V/Q audit", "", "| scenario | SaO2 | PaO2 | PaCO2 | shunt | dead space | sigma | VA L/min | status |", "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in rows:
        lines.append(
            f"| {r['scenario']} | {r.get('SaO2', float('nan')):.3f} | {r.get('PaO2', float('nan')):.1f} | "
            f"{r.get('PaCO2', float('nan')):.1f} | {r.get('vq_shunt_frac', float('nan')):.3f} | "
            f"{r.get('vq_deadspace_frac', float('nan')):.3f} | {r.get('vq_logsd', float('nan')):.3f} | "
            f"{r.get('alveolar_ventilation_L_min', float('nan')):.2f} | {r['status']} |"
        )
    (outdir / "vq_three_zone_audit_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    failed = [r for r in rows if r["status"] != "PASS"]
    print(json.dumps({"rows": len(rows), "failed": len(failed), "outdir": str(outdir)}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
