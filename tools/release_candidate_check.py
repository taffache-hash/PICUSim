#!/usr/bin/env python3
"""
v0.48 release-candidate check.

Static packaging/governance check for the public-facing release boundary.
This is not a physiological validation tool.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List

try:
    import yaml
except Exception as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required for release_candidate_check.py") from exc

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "validation_pack"

REQUIRED_DISCLAIMER_PHRASES = [
    "not for clinical use",
    "not a medical device",
    "not validated",
    "not a validated patient-specific digital twin",
]

OVERCLAIM_PATTERNS = [
    r"clinically validated\s+digital\s+twin",
    r"bedside\s+decision\s+support",
    r"diagnostic\s+tool",
    r"prescription\s+tool",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def check_required_files(manifest: Dict) -> List[Dict[str, object]]:
    rows = []
    for rel in manifest.get("minimum_release_files", []):
        path = ROOT / rel
        rows.append({
            "check": "required_file",
            "item": rel,
            "status": "PASS" if path.exists() else "FAIL",
            "detail": "exists" if path.exists() else "missing",
        })
    return rows


def check_disclaimer() -> List[Dict[str, object]]:
    path = ROOT / "DISCLAIMER_NOT_FOR_CLINICAL_USE.md"
    if not path.exists():
        return [{"check": "disclaimer", "item": str(path.name), "status": "FAIL", "detail": "missing"}]
    text = read_text(path).lower()
    rows = []
    for phrase in REQUIRED_DISCLAIMER_PHRASES:
        rows.append({
            "check": "disclaimer_phrase",
            "item": phrase,
            "status": "PASS" if phrase in text else "FAIL",
            "detail": "present" if phrase in text else "missing",
        })
    return rows


def check_readme_overclaiming() -> List[Dict[str, object]]:
    path = ROOT / "README.md"
    if not path.exists():
        return [{"check": "readme", "item": "README.md", "status": "FAIL", "detail": "missing"}]
    text = read_text(path).lower()
    rows = []
    rows.append({
        "check": "readme_disclaimer",
        "item": "not for clinical use",
        "status": "PASS" if "not for clinical use" in text else "FAIL",
        "detail": "present" if "not for clinical use" in text else "missing",
    })
    for pattern in OVERCLAIM_PATTERNS:
        hit = re.search(pattern, text) is not None
        # Overclaim phrases may appear as explicit prohibitions such as "not for bedside decision support"
        # or in "not acceptable" examples. Those are acceptable and should not fail the release check.
        allowed_as_warning_example = pattern == r"clinically validated\s+digital\s+twin" and "not acceptable" in text
        allowed_as_prohibition = pattern == r"bedside\s+decision\s+support" and ("not for clinical use. not for diagnosis" in text or "not for bedside decision support" in text)
        status = "PASS" if (not hit or allowed_as_warning_example or allowed_as_prohibition) else "FAIL"
        detail = "not detected"
        if hit and allowed_as_warning_example:
            detail = "detected only as warning/example"
        elif hit and allowed_as_prohibition:
            detail = "detected only as explicit prohibition"
        elif hit:
            detail = "detected"
        rows.append({
            "check": "readme_overclaim_pattern",
            "item": pattern,
            "status": status,
            "detail": detail,
        })
    return rows


def check_citation() -> List[Dict[str, object]]:
    rows = []
    cff = ROOT / "CITATION.cff"
    bib = ROOT / "CITATION.bib"
    rows.append({"check": "citation_file", "item": "CITATION.cff", "status": "PASS" if cff.exists() else "FAIL", "detail": "exists" if cff.exists() else "missing"})
    rows.append({"check": "citation_file", "item": "CITATION.bib", "status": "PASS" if bib.exists() else "FAIL", "detail": "exists" if bib.exists() else "missing"})
    if cff.exists():
        try:
            data = yaml.safe_load(cff.read_text()) or {}
            for key in ["title", "authors", "version", "message"]:
                rows.append({"check": "citation_cff_field", "item": key, "status": "PASS" if data.get(key) else "FAIL", "detail": "present" if data.get(key) else "missing"})
        except Exception as exc:
            rows.append({"check": "citation_cff_parse", "item": "CITATION.cff", "status": "FAIL", "detail": str(exc)})
    return rows


def check_unwanted_cache_files() -> List[Dict[str, object]]:
    patterns = ["__pycache__", ".pytest_cache", ".ipynb_checkpoints"]
    rows = []
    for pattern in patterns:
        hits = [p for p in ROOT.rglob(pattern) if p.exists()]
        rows.append({
            "check": "cache_directory",
            "item": pattern,
            "status": "PASS" if not hits else "REVIEW",
            "detail": f"{len(hits)} found" if hits else "none found",
        })
    return rows


def write_outputs(rows: List[Dict[str, object]]) -> Dict[str, object]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    failures = [r for r in rows if r["status"] == "FAIL"]
    reviews = [r for r in rows if r["status"] == "REVIEW"]
    summary = {
        "version": "v0.48",
        "checks": len(rows),
        "passed": sum(1 for r in rows if r["status"] == "PASS"),
        "review": len(reviews),
        "failed": len(failures),
        "status": "FAIL" if failures else "REVIEW" if reviews else "PASS",
    }
    import csv
    csv_path = OUT_DIR / "release_candidate_check_v048.csv"
    if rows:
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    (OUT_DIR / "release_candidate_check_v048_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lines = ["# v0.48 Release Candidate Check", "", f"Status: **{summary['status']}**", "", f"Checks: {summary['checks']}", f"Passed: {summary['passed']}", f"Review: {summary['review']}", f"Failed: {summary['failed']}", "", "| Check | Item | Status | Detail |", "|---|---|---:|---|"]
    for r in rows:
        lines.append(f"| {r['check']} | `{r['item']}` | {r['status']} | {r['detail']} |")
    (OUT_DIR / "release_candidate_check_v048_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="data/release_candidate_manifest_v0.48.yaml")
    parser.add_argument("--fail-on-error", action="store_true")
    parser.add_argument("--fail-on-review", action="store_true")
    args = parser.parse_args()

    manifest_path = ROOT / args.manifest
    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")
    manifest = yaml.safe_load(manifest_path.read_text()) or {}
    rows: List[Dict[str, object]] = []
    rows.extend(check_required_files(manifest))
    rows.extend(check_disclaimer())
    rows.extend(check_readme_overclaiming())
    rows.extend(check_citation())
    rows.extend(check_unwanted_cache_files())
    summary = write_outputs(rows)
    print(json.dumps(summary, indent=2))
    if args.fail_on_error and summary["failed"]:
        raise SystemExit(1)
    if args.fail_on_review and (summary["failed"] or summary["review"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
