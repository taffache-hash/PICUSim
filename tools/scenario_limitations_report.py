#!/usr/bin/env python3
"""Generate scenario limitations report from v0.36 limitation registry."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.simtools import write_json  # noqa: E402


def build_rows(spec: Dict[str, Any]) -> pd.DataFrame:
    global_lims = spec.get("global_limitations", [])
    by_domain = spec.get("common_by_domain", {})
    tags = spec.get("scenario_tags", {})
    specific = spec.get("scenario_specific", {})
    rows: List[Dict[str, Any]] = []
    for scenario, domains in tags.items():
        for lim in global_lims:
            rows.append({"scenario": scenario, "level": "global", "domain": "all", "limitation": lim})
        for domain in domains:
            for lim in by_domain.get(domain, []):
                rows.append({"scenario": scenario, "level": "domain", "domain": domain, "limitation": lim})
        for lim in specific.get(scenario, []):
            rows.append({"scenario": scenario, "level": "scenario", "domain": "specific", "limitation": lim})
    return pd.DataFrame(rows)


def write_markdown(df: pd.DataFrame, path: Path) -> None:
    lines = [
        "# PDT v0.36 Scenario Limitations Report",
        "",
        "These limitations should be shown with scenario outputs, expert-review sheets and future GUI views.",
        "",
    ]
    if not df.empty:
        for scenario, sub in df.groupby("scenario"):
            lines += [f"## {scenario}", ""]
            for _, r in sub.iterrows():
                lines.append(f"- **{r['level']} / {r['domain']}**: {r['limitation']}")
            lines.append("")
    path.write_text("\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default=str(ROOT / "data" / "scenario_limitations_v0.36.yaml"))
    ap.add_argument("--outdir", default=str(ROOT / "outputs" / "validation_pack"))
    args = ap.parse_args()
    spec = yaml.safe_load(Path(args.spec).read_text())
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    df = build_rows(spec)
    df.to_csv(outdir / "scenario_limitations_report.csv", index=False)
    write_markdown(df, outdir / "scenario_limitations_report.md")
    summary = {"scenarios": int(df["scenario"].nunique()) if len(df) else 0, "limitations": int(len(df))}
    write_json(summary, outdir / "scenario_limitations_summary.json")
    print(json.dumps(summary, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
