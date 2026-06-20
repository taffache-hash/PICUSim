#!/usr/bin/env python3
"""Generate a source-to-target matrix for PDT literature benchmarks (v0.39)."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_spec(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text())


def build_matrix(spec: Dict[str, Any]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for scenario, scfg in spec.get("scenarios", {}).items():
        for variable, tcfg in scfg.get("targets", {}).items():
            for source in tcfg.get("source", []):
                rows.append({
                    "scenario": scenario,
                    "age_band": scfg.get("age_band", ""),
                    "scenario_severity": scfg.get("severity_band", ""),
                    "variable": variable,
                    "low": tcfg.get("range", [None, None])[0],
                    "high": tcfg.get("range", [None, None])[1],
                    "target_type": tcfg.get("target_type", ""),
                    "target_severity": tcfg.get("severity_band", ""),
                    "source_id": source,
                    "source_title": spec.get("sources", {}).get(source, {}).get("title", ""),
                    "source_url": spec.get("sources", {}).get(source, {}).get("url", ""),
                    "rationale": tcfg.get("rationale", ""),
                    "derived_from": tcfg.get("derived_from", ""),
                })
    return pd.DataFrame(rows)


def write_markdown(df: pd.DataFrame, spec: Dict[str, Any], path: Path) -> None:
    lines = [
        "# PDT v0.39 Literature Source Matrix",
        "",
        "This file maps every benchmark target to source identifiers, target type, age band and severity band.",
        "It is a traceability artifact, not external clinical validation.",
        "",
        f"Spec version: **{spec.get('version','')}**",
        "",
        "## Sources",
        "",
    ]
    for sid, src in spec.get("sources", {}).items():
        lines.append(f"- **{sid}** — {src.get('title','')} — {src.get('url','')}")
    lines += ["", "## Target matrix", ""]
    if df.empty:
        lines.append("No targets found.")
    else:
        lines.append("| Scenario | Variable | Range | Type | Severity | Source |")
        lines.append("|---|---|---:|---|---|---|")
        for _, r in df.iterrows():
            lines.append(f"| {r['scenario']} | {r['variable']} | {r['low']}–{r['high']} | {r['target_type']} | {r['target_severity']} | {r['source_id']} |")
    path.write_text("\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default=str(ROOT / "data" / "literature_benchmark_targets_v0.39.yaml"))
    ap.add_argument("--outdir", default=str(ROOT / "outputs" / "validation_pack"))
    args = ap.parse_args()
    spec = load_spec(Path(args.spec))
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    df = build_matrix(spec)
    df.to_csv(outdir / "literature_source_matrix.csv", index=False)
    write_markdown(df, spec, outdir / "literature_source_matrix.md")
    summary = {
        "spec": Path(args.spec).name,
        "sources": len(spec.get("sources", {})),
        "scenarios": len(spec.get("scenarios", {})),
        "target_rows": len(df),
        "unique_target_variables": int(df["variable"].nunique()) if not df.empty else 0,
    }
    (outdir / "literature_source_matrix_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
