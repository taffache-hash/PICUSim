#!/usr/bin/env python3
"""Audit BusState score/proxy/modifier-like variables against the v0.41 registry."""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

try:
    import yaml
except Exception as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required") from exc

ROOT = Path(__file__).resolve().parents[1]
BUS_PATH = ROOT / "core" / "bus.py"
REGISTRY_PATH = ROOT / "data" / "score_assumption_registry_v1.19.yaml"
OUTDIR = ROOT / "outputs" / "validation_pack"
PATTERNS = ("index", "score", "risk", "proxy", "mod", "alert", "effect", "tone", "drive", "burden", "frac", "severity", "readiness")
EXCLUDE = {"vent_mode", "owner_modifier_revision", "residual_owner_modifier_revision", "GRC_units_given", "FFP_mL_given", "PLT_units_given"}


def bus_fields() -> list[str]:
    tree = ast.parse(BUS_PATH.read_text(encoding="utf-8"))
    fields = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "BusState":
            for stmt in node.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    fields.append(stmt.target.id)
    return fields


def score_like(fields: list[str]) -> set[str]:
    out = set()
    for f in fields:
        fl = f.lower()
        if f not in EXCLUDE and (any(p in fl for p in PATTERNS) or fl.endswith("_add")):
            out.add(f)
    return out


def load_registry() -> set[str]:
    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8")) or {}
    return {e.get("variable") for e in data.get("entries", []) if e.get("variable")}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--fail-on-error", action="store_true")
    args = p.parse_args()
    expected = score_like(bus_fields())
    registered = load_registry()
    missing = sorted(expected - registered)
    extra = sorted(registered - expected)
    status = "PASS" if not missing else "REVIEW"
    summary = {"status": status, "expected_score_like": len(expected), "registered": len(registered), "missing": missing, "extra_non_score_like": extra}
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "score_registry_audit_v119_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with (OUTDIR / "score_registry_audit_v119.md").open("w", encoding="utf-8") as f:
        f.write("# Score Registry Audit — v1.19\n\n")
        f.write(f"Status: **{status}**\n\n")
        f.write(f"Score-like BusState variables: {len(expected)}\n\nRegistered entries: {len(registered)}\n\n")
        if missing:
            f.write("## Missing registry entries\n\n")
            for m in missing: f.write(f"- {m}\n")
        if extra:
            f.write("\n## Extra registry entries not currently detected as score-like\n\n")
            for e in extra: f.write(f"- {e}\n")
    print(json.dumps(summary, indent=2))
    return 1 if args.fail_on_error and status != "PASS" else 0

if __name__ == "__main__":
    raise SystemExit(main())
