#!/usr/bin/env python3
"""Generate a curriculum/catalog report for scenario YAML files."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = ROOT / "data" / "scenario_curriculum_v1.04.yaml"
DEFAULT_OUT = ROOT / "outputs" / "curriculum"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def scenario_files() -> set[str]:
    return {f"scenarios/{p.name}" for p in (ROOT / "scenarios").glob("*.yaml")}


def validate_catalog(catalog: dict) -> list[str]:
    errors: list[str] = []
    scenarios = catalog.get("scenarios") or []
    files_in_catalog = {str(s.get("file")) for s in scenarios}
    files_on_disk = scenario_files()

    missing = sorted(files_on_disk - files_in_catalog)
    stale = sorted(files_in_catalog - files_on_disk)
    if missing:
        errors.append("missing_from_catalog: " + ", ".join(missing))
    if stale:
        errors.append("catalog_points_to_missing_files: " + ", ".join(stale))

    required = {"id", "file", "domain", "complexity", "age_group", "educational_goal", "suggested_use"}
    for entry in scenarios:
        missing_keys = sorted(k for k in required if not entry.get(k))
        if missing_keys:
            errors.append(f"{entry.get('id','<unknown>')}: missing {', '.join(missing_keys)}")

    return errors


def write_markdown(catalog: dict, errors: list[str], out_path: Path) -> None:
    scenarios = catalog.get("scenarios") or []
    by_domain = defaultdict(list)
    for s in scenarios:
        by_domain[str(s.get("domain", "unclassified"))].append(s)

    counts_complexity = Counter(str(s.get("complexity", "unknown")) for s in scenarios)
    counts_age = Counter(str(s.get("age_group", "unknown")) for s in scenarios)

    lines = [
        "# Scenario curriculum report — v1.04-alpha",
        "",
        f"Catalogued scenarios: **{len(scenarios)}**",
        "",
        "Safety status: educational/research alpha only; not for clinical use; not a medical device; not a validated patient-specific digital twin.",
        "",
        "## Validation status",
        "",
    ]
    if errors:
        lines.append("Status: **REVIEW**")
        lines.append("")
        for err in errors:
            lines.append(f"- {err}")
    else:
        lines.append("Status: **PASS** — every scenario YAML is represented in the curriculum catalog.")

    lines += ["", "## Complexity distribution", "", "| complexity | count |", "|---|---:|"]
    for k in sorted(counts_complexity):
        lines.append(f"| {k} | {counts_complexity[k]} |")

    lines += ["", "## Age-profile distribution", "", "| age group | count |", "|---|---:|"]
    for k in sorted(counts_age):
        lines.append(f"| {k} | {counts_age[k]} |")

    seq = catalog.get("curriculum_sequence") or []
    lines += ["", "## Suggested starter sequence", ""]
    for i, item in enumerate(seq, 1):
        match = next((s for s in scenarios if s.get("id") == item), None)
        if match:
            lines.append(f"{i}. `{item}` — {match.get('educational_goal')}")
        else:
            lines.append(f"{i}. `{item}` — not found in catalog")

    lines += ["", "## Scenarios by domain", ""]
    for domain in sorted(by_domain):
        lines.append(f"### {domain}")
        lines.append("")
        lines.append("| scenario | complexity | age group | educational goal |")
        lines.append("|---|---|---|---|")
        for s in sorted(by_domain[domain], key=lambda x: str(x.get("id"))):
            lines.append(
                f"| `{s.get('id')}` | {s.get('complexity')} | {s.get('age_group')} | {s.get('educational_goal')} |"
            )
        lines.append("")

    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_csv(catalog: dict, out_path: Path) -> None:
    scenarios = catalog.get("scenarios") or []
    fields = ["id", "file", "scenario_name", "domain", "complexity", "age_group", "weight_kg", "simulation_time_s", "educational_goal", "suggested_use"]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for s in scenarios:
            writer.writerow({k: s.get(k, "") for k in fields})


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate scenario curriculum reports.")
    parser.add_argument("--spec", default=str(DEFAULT_SPEC), help="Curriculum YAML file")
    parser.add_argument("--outdir", default=str(DEFAULT_OUT), help="Output directory")
    parser.add_argument("--fail-on-missing", action="store_true", help="Return non-zero if catalog is incomplete")
    args = parser.parse_args()

    spec = Path(args.spec)
    if not spec.is_absolute():
        spec = ROOT / spec
    outdir = Path(args.outdir)
    if not outdir.is_absolute():
        outdir = ROOT / outdir
    outdir.mkdir(parents=True, exist_ok=True)

    catalog = load_yaml(spec)
    errors = validate_catalog(catalog)

    md_path = outdir / "scenario_curriculum_report.md"
    csv_path = outdir / "scenario_curriculum_catalog.csv"
    json_path = outdir / "scenario_curriculum_summary.json"

    write_markdown(catalog, errors, md_path)
    write_csv(catalog, csv_path)

    summary = {
        "version": catalog.get("version"),
        "scenarios": len(catalog.get("scenarios") or []),
        "errors": errors,
        "status": "PASS" if not errors else "REVIEW",
        "markdown": str(md_path.relative_to(ROOT)),
        "csv": str(csv_path.relative_to(ROOT)),
    }
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

    if args.fail_on_missing and errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
