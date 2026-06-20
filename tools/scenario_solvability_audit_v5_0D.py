#!/usr/bin/env python3
"""PDT v5.0D scenario solvability audit.

Audit gate for curated scenario-engine v2 cases. This is a structural and
semi-structured validation step: it does not prove clinical accuracy, but it
checks whether scenarios are playable, recoverable, fail-able and debriable.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_yaml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _nested_keys(obj: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(obj, Mapping):
        for k, v in obj.items():
            keys.add(str(k))
            keys |= _nested_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            keys |= _nested_keys(v)
    return keys


def _perturbation_actions(perturbations: Sequence[Any]) -> List[str]:
    out: List[str] = []
    for p in perturbations:
        if isinstance(p, Mapping):
            out.append(str(p.get("action", "")))
    return [x for x in out if x]


def _perturbation_labels(perturbations: Sequence[Any]) -> List[str]:
    out: List[str] = []
    for p in perturbations:
        if isinstance(p, Mapping):
            out.append(str(p.get("label", "")).lower())
    return [x for x in out if x]


def _find_manifest_entries(manifest: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    entries = manifest.get("scenarios", []) or []
    return [e for e in entries if isinstance(e, Mapping)]


def _bool_text(value: bool) -> str:
    return "yes" if value else "no"


def audit_one(entry: Mapping[str, Any], spec: Mapping[str, Any], root: Path) -> Dict[str, Any]:
    criteria = spec.get("criteria", {}) or {}
    sid = str(entry.get("id") or entry.get("name") or "")
    rel_path = str(entry.get("path", ""))
    findings: List[str] = []
    severity = "pass"

    if not rel_path:
        return {"scenario_id": sid, "status": "critical", "critical_findings": 1, "review_findings": 0, "findings": "missing manifest path"}
    path = root / rel_path
    if not path.exists():
        return {"scenario_id": sid, "status": "critical", "critical_findings": 1, "review_findings": 0, "findings": f"unreadable scenario: {rel_path}"}

    scenario = load_yaml(path)
    nested = _nested_keys(scenario)
    perturbations = _as_list(scenario.get("perturbations"))
    actions = _perturbation_actions(perturbations)
    labels = _perturbation_labels(perturbations)
    expected_actions = _as_list(entry.get("expected_actions"))
    outputs = _as_list(scenario.get("outputs") or entry.get("key_outputs"))
    debrief_qs = _as_list(entry.get("debrief_questions") or scenario.get("debrief_questions"))
    sim_time = int(scenario.get("simulation_time_s") or scenario.get("duration_s") or 0)

    critical = 0
    review = 0

    def add(level: str, text: str) -> None:
        nonlocal critical, review, severity
        findings.append(text)
        if level == "critical":
            critical += 1
            severity = "critical"
        elif level == "review" and severity != "critical":
            review += 1
            severity = "review"

    if criteria.get("require_patient", True) and "patient" not in scenario:
        add("critical", "missing patient block")
    if sim_time < int(criteria.get("minimum_simulation_time_s", 240)):
        add("critical", f"simulation_time_s below minimum: {sim_time}")
    if len(expected_actions) < int(criteria.get("minimum_expected_actions", 2)):
        add("critical", f"too few expected actions: {len(expected_actions)}")
    if len(perturbations) < int(criteria.get("minimum_perturbations", 2)):
        add("review", f"few perturbations/intervention steps: {len(perturbations)}")
    if len(outputs) < int(criteria.get("minimum_outputs", 4)):
        add("review", f"limited outputs: {len(outputs)}")
    if criteria.get("require_debrief_questions", True) and not debrief_qs:
        add("review", "missing debrief questions")

    recovery_spec = spec.get("recovery_markers", {}) or {}
    recovery_actions = set(str(x) for x in recovery_spec.get("actions", []) or [])
    recovery_labels = [str(x).lower() for x in recovery_spec.get("labels_any", []) or []]
    recovery_marker = bool(set(actions) & recovery_actions) or any(any(token in lab for token in recovery_labels) for lab in labels)
    if criteria.get("require_recovery_marker", True) and not recovery_marker:
        add("review", "weak recovery marker")

    failure_spec = spec.get("failure_markers", {}) or {}
    failure_state = bool(set(str(x) for x in failure_spec.get("state_keys", []) or []) & nested)
    failure_output = bool(set(str(x) for x in failure_spec.get("output_keys", []) or []) & set(str(x) for x in outputs))
    failure_marker = failure_state and failure_output
    if criteria.get("require_failure_marker", True) and not failure_marker:
        add("review", "weak failure marker")

    non_det_marker = len(set(actions)) >= 2 and len(perturbations) >= 3 and len(outputs) >= 3
    if criteria.get("require_non_determinism_marker", True) and not non_det_marker:
        add("review", "weak non-determinism marker")

    playable = critical == 0
    recoverable = recovery_marker and playable
    failable = failure_marker and playable
    non_deterministic = non_det_marker and playable
    solvable = playable and recoverable and failable and non_deterministic and review == 0

    return {
        "scenario_id": sid,
        "path": rel_path,
        "phenotype": entry.get("phenotype", ""),
        "complexity": entry.get("complexity", ""),
        "simulation_time_s": sim_time,
        "expected_actions": len(expected_actions),
        "perturbations": len(perturbations),
        "outputs": len(outputs),
        "playable": _bool_text(playable),
        "recoverable": _bool_text(recoverable),
        "failable": _bool_text(failable),
        "non_deterministic": _bool_text(non_deterministic),
        "solvable": _bool_text(solvable),
        "status": severity,
        "critical_findings": critical,
        "review_findings": review,
        "findings": "; ".join(findings) if findings else "none",
    }


def write_csv(path: Path, rows: List[Mapping[str, Any]]) -> None:
    fields = [
        "scenario_id", "path", "phenotype", "complexity", "simulation_time_s",
        "expected_actions", "perturbations", "outputs", "playable", "recoverable",
        "failable", "non_deterministic", "solvable", "status", "critical_findings",
        "review_findings", "findings",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def write_report(path: Path, rows: List[Mapping[str, Any]], summary: Mapping[str, Any]) -> None:
    lines = [
        "# Step 5.0D — Scenario Solvability Audit Report",
        "",
        "Scope: scenario-engine v2 structural solvability audit before deeper validation.",
        "",
        "This is **not** clinical validation and **not** medical decision support.",
        "",
        f"Scenarios audited: **{summary['scenarios_audited']}**",
        f"Solvable: **{summary['solvable']}**",
        f"Playable: **{summary['playable']}**",
        f"Recoverable: **{summary['recoverable']}**",
        f"Fail-able: **{summary['failable']}**",
        f"Non-deterministic/playable: **{summary['non_deterministic']}**",
        f"Critical findings: **{summary['critical_findings']}**",
        f"Review findings: **{summary['review_findings']}**",
        f"Pass audit: **{summary['pass_audit']}**",
        "",
        "## Scenario table",
        "",
        "| Scenario | Time s | Playable | Recoverable | Fail-able | Non-deterministic | Status | Findings |",
        "|---|---:|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r.get('scenario_id')} | {r.get('simulation_time_s')} | {r.get('playable')} | "
            f"{r.get('recoverable')} | {r.get('failable')} | {r.get('non_deterministic')} | "
            f"{r.get('status')} | {r.get('findings')} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
    ]
    if summary["critical_findings"] == 0:
        lines.append("No critical structural blockers were detected. All audited scenarios are playable by the defined gate.")
    else:
        lines.append("Critical blockers remain and must be corrected before promotion.")
    if summary["review_findings"] == 0:
        lines.append("No review-level solvability warnings were detected in the curated v2 pack.")
    else:
        lines.append("Review-level warnings indicate scenarios that may still be usable but need manual educator review.")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default=str(ROOT / "data" / "scenario_solvability_audit_v5.0D.yaml"))
    ap.add_argument("--manifest", default=str(ROOT / "data" / "scenario_engine_v2_step4.44.yaml"))
    ap.add_argument("--outdir", default=str(ROOT / "outputs" / "scenario_solvability_v5.0D"))
    ap.add_argument("--fail-on-critical", action="store_true")
    args = ap.parse_args()

    spec = load_yaml(Path(args.spec))
    manifest = load_yaml(Path(args.manifest))
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)

    entries = _find_manifest_entries(manifest)
    rows = [audit_one(e, spec, ROOT) for e in entries]
    critical = sum(int(r.get("critical_findings", 0)) for r in rows)
    review = sum(int(r.get("review_findings", 0)) for r in rows)
    summary = {
        "release_step": "5.0D",
        "scenarios_audited": len(rows),
        "solvable": sum(1 for r in rows if r.get("solvable") == "yes"),
        "playable": sum(1 for r in rows if r.get("playable") == "yes"),
        "recoverable": sum(1 for r in rows if r.get("recoverable") == "yes"),
        "failable": sum(1 for r in rows if r.get("failable") == "yes"),
        "non_deterministic": sum(1 for r in rows if r.get("non_deterministic") == "yes"),
        "critical_findings": critical,
        "review_findings": review,
        "pass_audit": critical == 0,
        "manifest": str(args.manifest),
        "spec": str(args.spec),
    }
    write_csv(outdir / "scenario_solvability_audit_v50D.csv", rows)
    (outdir / "scenario_solvability_summary_v50D.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_report(outdir / "scenario_solvability_report_v50D.md", rows, summary)
    print(json.dumps(summary, indent=2))
    if args.fail_on_critical and critical:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
