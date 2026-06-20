#!/usr/bin/env python3
"""Create an inventory of available PDT scenarios and metadata."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import pandas as pd
import yaml
ROOT = Path(__file__).resolve().parents[1]


def classify(cfg: dict) -> str:
    keys = set(cfg.keys())
    if "airway" in keys: return "respiratory/airway"
    if "infection" in keys or "sepsis" in keys: return "infection/sepsis"
    if "neurology" in keys or "neurofunctional" in keys: return "neurology"
    if "renal" in keys: return "renal"
    if "hepatic" in keys: return "hepatic"
    if "nutrition" in keys: return "nutrition"
    if "hematology" in keys: return "hematology"
    return "general"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=str(ROOT / "outputs" / "validation_pack"))
    args = ap.parse_args()
    rows = []
    for path in sorted((ROOT / "scenarios").glob("*.yaml")):
        cfg = yaml.safe_load(path.read_text())
        patient = cfg.get("patient", {}) or {}
        rows.append({
            "scenario": path.stem,
            "version": cfg.get("version", ""),
            "domain": classify(cfg),
            "age_y": patient.get("age_y", ""),
            "weight_kg": patient.get("weight_kg", ""),
            "profile": patient.get("profile", ""),
            "diagnosis": patient.get("diagnosis", ""),
            "simulation_time_s": cfg.get("simulation_time_s", ""),
            "description": str(cfg.get("description", "")).strip().replace("\n", " ")[:220],
        })
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(outdir / "scenario_inventory.csv", index=False)
    lines = ["# PDT Scenario Inventory", "", "| Scenario | Domain | Patient | Duration | Description |", "|---|---|---|---:|---|"]
    for _, r in df.iterrows():
        patient = f"{r['age_y']}y / {r['weight_kg']}kg" if r['age_y'] != "" else ""
        lines.append(f"| {r['scenario']} | {r['domain']} | {patient} | {r['simulation_time_s']} | {r['description']} |")
    (outdir / "scenario_inventory.md").write_text("\n".join(lines))
    print(f"scenario inventory written to {outdir}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
