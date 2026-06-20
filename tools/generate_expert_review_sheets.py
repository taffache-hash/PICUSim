#!/usr/bin/env python3
"""Generate clinician-facing expert review sheets for PDT benchmark scenarios."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import pandas as pd
import yaml
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.benchmark_report import evaluate_benchmarks  # noqa: E402


def scenario_description(name: str) -> str:
    p = ROOT / "scenarios" / f"{name}.yaml"
    if not p.exists():
        return ""
    cfg = yaml.safe_load(p.read_text())
    return str(cfg.get("description", "")).strip()


def write_sheets(df: pd.DataFrame, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    index_lines = ["# PDT Expert Review Sheets", "", "Printable forms for structured clinical face-validity review.", ""]
    for scenario, sub in df.groupby("scenario"):
        desc = scenario_description(scenario)
        path = outdir / f"{scenario}_expert_review.md"
        lines = [
            f"# Expert Review Sheet — {scenario}", "",
            "**Purpose:** structured face-validity review of one simulated scenario.", "",
            f"**Scenario description:** {desc or 'Not provided.'}", "",
            "Reviewer: ______________________    Date: __________", "",
            "## Quantitative anchors", "",
            "| Variable | Simulated value | Expected range | Clinician rating | Notes |",
            "|---|---:|---:|---|---|",
        ]
        for _, r in sub.iterrows():
            lines.append(f"| {r['variable']} | {float(r['value']):.3g} | {float(r['low']):.3g}–{float(r['high']):.3g} | plausible / borderline / implausible |  |")
        lines += [
            "", "## Scenario trajectory", "",
            "Does the clinical trajectory evolve in the expected direction after each intervention?", "",
            "☐ Yes  ☐ Partly  ☐ No", "",
            "Notes:", "", "................................................................................", "", "................................................................................", "",
            "## Overall face validity", "", "☐ Accept  ☐ Accept with minor changes  ☐ Major revision  ☐ Reject", "",
        ]
        path.write_text("\n".join(lines))
        index_lines.append(f"- [{scenario}]({path.name})")
    (outdir / "INDEX.md").write_text("\n".join(index_lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default=str(ROOT / "benchmarks" / "expected_ranges.yaml"))
    ap.add_argument("--dt", type=float, default=1.0)
    ap.add_argument("--outdir", default=str(ROOT / "outputs" / "validation_pack" / "expert_review_sheets"))
    ap.add_argument("--benchmark-csv", default=str(ROOT / "outputs" / "validation_pack" / "benchmark_report.csv"))
    args = ap.parse_args()
    csv_path = Path(args.benchmark_csv)
    if csv_path.exists():
        df = pd.read_csv(csv_path)
    else:
        df = evaluate_benchmarks(Path(args.spec), dt=args.dt)
    write_sheets(df, Path(args.outdir))
    print(f"Expert review sheets written to {args.outdir}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
