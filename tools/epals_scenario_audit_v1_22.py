#!/usr/bin/env python3
"""v1.22 EPALS reversible-cause taxonomy audit.

This tool validates the educational H/T taxonomy scaffold and writes a small
planning dashboard for later scenario implementation. It does not run patient
simulations in v1.22 because the actual EPALS scenarios are intentionally added
in v1.22.1 and v1.22.2.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text())


def audit_taxonomy(spec: Dict[str, Any]) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    causes = spec.get("causes", []) or []
    source_ids = set((spec.get("sources", {}) or {}).keys())
    seen_ids = set()
    seen_scenarios = set()

    for c in causes:
        cid = c.get("id", "")
        sid = c.get("planned_scenario_id", "")
        refs = c.get("source", []) or []
        missing_refs = [r for r in refs if r not in source_ids]
        required_ok = bool(
            cid and
            c.get("group") in {"H", "T"} and
            sid and
            c.get("clinical_frame") and
            len(c.get("primary_modules", []) or []) >= 2 and
            len(c.get("key_bus_variables", []) or []) >= 5 and
            len(c.get("deterioration_markers", []) or []) >= 2 and
            len(c.get("expected_interventions", []) or []) >= 2 and
            len(c.get("expected_response", []) or []) >= 1 and
            len(c.get("debrief_questions", []) or []) >= 2 and
            refs and
            not missing_refs
        )
        duplicate = cid in seen_ids or sid in seen_scenarios
        seen_ids.add(cid)
        seen_scenarios.add(sid)
        status = "PASS" if required_ok and not duplicate else "REVIEW"
        rows.append({
            "cause_id": cid,
            "group": c.get("group", ""),
            "display_name": c.get("display_name", ""),
            "planned_scenario_id": sid,
            "module_count": len(c.get("primary_modules", []) or []),
            "variable_count": len(c.get("key_bus_variables", []) or []),
            "intervention_count": len(c.get("expected_interventions", []) or []),
            "question_count": len(c.get("debrief_questions", []) or []),
            "missing_sources": ";".join(missing_refs),
            "duplicate_id_or_scenario": duplicate,
            "status": status,
        })

    h_count = sum(1 for r in rows if r["group"] == "H")
    t_count = sum(1 for r in rows if r["group"] == "T")
    review = sum(1 for r in rows if r["status"] != "PASS")
    summary = {
        "release": "v1.22-alpha",
        "status": "PASS" if len(rows) == 10 and h_count == 5 and t_count == 5 and review == 0 else "REVIEW",
        "cause_count": len(rows),
        "H_count": h_count,
        "T_count": t_count,
        "planned_scenario_count": len(seen_scenarios),
        "source_count": len(source_ids),
        "review_items": review,
        "rows": rows,
    }
    return summary


def write_outputs(summary: Dict[str, Any], spec: Dict[str, Any], outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "epals_taxonomy_summary_v122.json").write_text(json.dumps(summary, indent=2))

    rows = summary["rows"]
    with (outdir / "epals_cause_matrix_v122.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["empty"])
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# PDT v1.22 EPALS Reversible-Cause Taxonomy Audit",
        "",
        "This is an educational planning scaffold. It is not clinical guidance and it does not validate the simulator for clinical use.",
        "",
        f"Status: **{summary['status']}**",
        f"Causes: **{summary['cause_count']}** (H={summary['H_count']}, T={summary['T_count']})",
        f"Planned scenarios: **{summary['planned_scenario_count']}**",
        "",
        "## Cause matrix",
        "",
        "| Group | Cause | Planned scenario | Variables | Interventions | Status |",
        "|---|---|---|---:|---:|---|",
    ]
    for r in rows:
        lines.append(f"| {r['group']} | {r['display_name']} | `{r['planned_scenario_id']}` | {r['variable_count']} | {r['intervention_count']} | {r['status']} |")
    lines += ["", "## Source inventory", ""]
    for sid, src in (spec.get("sources", {}) or {}).items():
        lines.append(f"- **{sid}** — {src.get('title','')} — {src.get('scope','')}")
    (outdir / "epals_taxonomy_report_v122.md").write_text("\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default=str(ROOT / "data" / "epals_reversible_causes_v1.22.yaml"))
    ap.add_argument("--outdir", default=str(ROOT / "outputs" / "epals_taxonomy_v1.22"))
    ap.add_argument("--fail-on-review", action="store_true")
    args = ap.parse_args()

    spec = load_yaml(Path(args.spec))
    summary = audit_taxonomy(spec)
    write_outputs(summary, spec, Path(args.outdir))
    print(json.dumps({k: summary[k] for k in ["release", "status", "cause_count", "H_count", "T_count", "review_items"]}, indent=2))
    if args.fail_on_review and summary["status"] != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
