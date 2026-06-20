#!/usr/bin/env python3
"""Generate score/proxy/modifier registry reports (v0.41).

This is a transparency tool: it lists every qualitative score, proxy,
risk index, and modifier declared in data/score_assumption_registry_v0.41.yaml.
It is not a validation tool and does not turn heuristic variables into
clinically validated endpoints.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

try:
    import yaml
except Exception as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required to run score_registry_report.py") from exc

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "data" / "score_assumption_registry_v0.41.yaml"
DEFAULT_OUTDIR = ROOT / "outputs" / "validation_pack"


def load_registry(path: Path = DEFAULT_REGISTRY) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if "entries" not in data or not isinstance(data["entries"], list):
        raise ValueError(f"Registry {path} has no entries list")
    return data


def write_reports(data: dict, outdir: Path = DEFAULT_OUTDIR) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    entries = data["entries"]
    required = data.get("required_fields", [])

    rows = []
    missing_rows = []
    for e in entries:
        missing = [k for k in required if k not in e or e[k] in (None, "", [])]
        if missing:
            missing_rows.append({"variable": e.get("variable", "<unknown>"), "missing": ",".join(missing)})
        rng = e.get("range", {}) or {}
        rows.append({
            "variable": e.get("variable", ""),
            "module": e.get("module", ""),
            "kind": e.get("kind", ""),
            "typical_range": rng.get("typical", ""),
            "hard_range": rng.get("hard", ""),
            "formula_status": e.get("formula_status", ""),
            "assumption_level": e.get("assumption_level", ""),
            "validation_status": e.get("validation_status", ""),
            "interpretation": e.get("interpretation", ""),
        })

    csv_path = outdir / "score_assumption_registry_v041.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader(); writer.writerows(rows)

    by_kind = Counter(e.get("kind", "unknown") for e in entries)
    by_module = Counter(e.get("module", "unknown") for e in entries)
    by_assumption = Counter(e.get("assumption_level", "unknown") for e in entries)
    summary = {
        "registry_version": data.get("version"),
        "entries": len(entries),
        "missing_required_entries": len(missing_rows),
        "by_kind": dict(by_kind),
        "by_module": dict(by_module),
        "by_assumption_level": dict(by_assumption),
        "status": "PASS" if not missing_rows else "REVIEW",
    }

    json_path = outdir / "score_assumption_registry_v041_summary.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    md_path = outdir / "score_assumption_registry_v041_report.md"
    with md_path.open("w", encoding="utf-8") as f:
        f.write("# Score / Proxy / Modifier Registry — v0.41\n\n")
        f.write("This report documents qualitative scores, proxies, risk indices and modifiers used internally by PDT.\n\n")
        f.write("These variables are **not clinically validated endpoints** and must not be interpreted as bedside scores.\n\n")
        f.write(f"Status: **{summary['status']}**\n\n")
        f.write(f"Total entries: **{len(entries)}**\n\n")
        f.write("## Entries by kind\n\n")
        for k, v in sorted(by_kind.items()):
            f.write(f"- {k}: {v}\n")
        f.write("\n## Entries by module\n\n")
        for k, v in sorted(by_module.items()):
            f.write(f"- {k}: {v}\n")
        if missing_rows:
            f.write("\n## Missing required fields\n\n")
            for r in missing_rows:
                f.write(f"- {r['variable']}: {r['missing']}\n")
        f.write("\n## Registry table\n\n")
        f.write("| Variable | Module | Kind | Assumption | Interpretation |\n")
        f.write("|---|---|---|---|---|\n")
        for e in entries:
            interp = str(e.get("interpretation", "")).replace("|", "/")
            f.write(f"| {e.get('variable','')} | {e.get('module','')} | {e.get('kind','')} | {e.get('assumption_level','')} | {interp} |\n")

    return {"csv": str(csv_path), "json": str(json_path), "md": str(md_path), "summary": summary}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    p.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    p.add_argument("--fail-on-review", action="store_true")
    args = p.parse_args()
    data = load_registry(args.registry)
    result = write_reports(data, args.outdir)
    print(json.dumps(result["summary"], indent=2))
    if args.fail_on_review and result["summary"]["status"] != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
