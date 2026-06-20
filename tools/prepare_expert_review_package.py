#!/usr/bin/env python3
"""Prepare simplified expert-review package using benchmarks and limitations (v0.34)."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.scenario_limitations_report import build_rows  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmarks", default=str(ROOT / "data" / "literature_benchmark_targets_v0.34.yaml"))
    ap.add_argument("--limitations", default=str(ROOT / "data" / "scenario_limitations_v0.34.yaml"))
    ap.add_argument("--outdir", default=str(ROOT / "outputs" / "expert_review_package"))
    args = ap.parse_args()
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    bench = yaml.safe_load(Path(args.benchmarks).read_text())
    lim = yaml.safe_load(Path(args.limitations).read_text())
    lim_df = build_rows(lim)

    rows: List[Dict[str, Any]] = []
    for scenario, scfg in bench.get("scenarios", {}).items():
        targets = scfg.get("targets", {})
        variables = ", ".join(targets.keys())
        lim_text = " | ".join(lim_df.loc[lim_df["scenario"] == scenario, "limitation"].head(8).tolist())
        rows.append({
            "reviewer_name": "",
            "reviewer_role": "",
            "scenario": scenario,
            "scenario_description": scfg.get("description", ""),
            "variables_to_review": variables,
            "key_limitations": lim_text,
            "physiologic_plausibility_1_5": "",
            "educational_usefulness_1_5": "",
            "major_implausibility_yes_no": "",
            "free_text_notes": "",
            "recommendation_accept_minor_major_reject": "",
        })
    pd.DataFrame(rows).to_csv(outdir / "expert_review_v0.34_template.csv", index=False)

    instructions = """# PDT v0.34 Expert Review Package\n\nAsk each reviewer to complete one row per scenario. Suggested minimum: 3-5 PICU/anesthesia clinicians.\n\nScores:\n- 1 = not plausible/useful\n- 3 = acceptable with limitations\n- 5 = highly plausible/useful for educational simulation\n\nThe reviewer is not asked to validate clinical prediction. They are asked to judge face validity and educational plausibility.\n"""
    (outdir / "expert_review_v0.34_instructions.md").write_text(instructions)
    print(f"Expert-review package written to {outdir}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
