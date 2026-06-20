#!/usr/bin/env python3
"""Audit PDT scalability assets.

This tool does not validate clinical accuracy. It checks whether the project has
explicit reference anchors, model registry entries, a credibility plan and a
future module backlog. It can generate a Markdown audit report for publication
planning.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

REQUIRED_FILES = {
    "literature_reference_values": DATA / "literature_reference_values.yaml",
    "model_registry": DATA / "model_registry.yaml",
    "validation_credibility_plan": DATA / "validation_credibility_plan.yaml",
    "future_modules_backlog": DATA / "future_modules_backlog.yaml",
}


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    obj = yaml.safe_load(path.read_text())
    if not isinstance(obj, dict):
        raise ValueError(f"{path} did not parse to a dictionary")
    return obj


def audit() -> dict[str, Any]:
    assets = {name: load_yaml(path) for name, path in REQUIRED_FILES.items()}
    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    refs = assets["literature_reference_values"]
    add("reference values include vital signs", "vital_signs" in refs, "age-stratified vital signs present")
    add("reference values include respiratory anchors", "respiratory" in refs, "Vt/dead space/PARDS anchors present")
    add("reference values include blood/renal anchors", "circulation_and_blood" in refs and "renal" in refs, "blood volume and eGFR anchors present")

    registry = assets["model_registry"]
    frameworks = registry.get("frameworks", {})
    credibility = registry.get("credibility_frameworks", {})
    add("external frameworks registered", len(frameworks) >= 4, f"{len(frameworks)} frameworks")
    add("credibility frameworks registered", len(credibility) >= 2, f"{len(credibility)} credibility frameworks")

    plan = assets["validation_credibility_plan"]
    add("context of use defined", "context_of_use" in plan, "intended and non-intended uses")
    add("quantities of interest defined", "quantities_of_interest" in plan, "module QOIs listed")
    add("release gate checklist defined", "release_gate_checklist" in plan, "future release gates listed")

    backlog = assets["future_modules_backlog"]
    add("near-term backlog defined", "priority_1_near_term" in backlog, "acid-base/AKI/endocrine tier")
    add("mid-term backlog defined", "priority_2_mid_term" in backlog, "ECMO/antimicrobial/nutrition tier")

    ok = all(c["ok"] for c in checks)
    return {"ok": ok, "checks": checks, "asset_files": {k: str(v.relative_to(ROOT)) for k, v in REQUIRED_FILES.items()}}


def to_markdown(result: dict[str, Any]) -> str:
    lines = ["# PDT scalability audit", "", f"Overall status: **{'PASS' if result['ok'] else 'FAIL'}**", ""]
    lines.append("## Asset files")
    for name, path in result["asset_files"].items():
        lines.append(f"- `{name}`: `{path}`")
    lines.append("")
    lines.append("## Checks")
    for c in result["checks"]:
        mark = "PASS" if c["ok"] else "FAIL"
        lines.append(f"- **{mark}** — {c['check']}: {c['detail']}")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("This audit confirms that the package contains the metadata needed for controlled expansion: reference anchors, external framework mapping, credibility planning and a prioritized module backlog. It does not certify clinical validity.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown")
    parser.add_argument("--write", action="store_true", help="Write Markdown report to outputs/scalability_audit.md")
    args = parser.parse_args()

    result = audit()
    if args.write:
        out_dir = ROOT / "outputs"
        out_dir.mkdir(exist_ok=True)
        out_path = out_dir / "scalability_audit.md"
        out_path.write_text(to_markdown(result))
        print(f"Wrote {out_path}")
    elif args.json:
        print(json.dumps(result, indent=2))
    else:
        print(to_markdown(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
