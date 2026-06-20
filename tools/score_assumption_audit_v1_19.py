#!/usr/bin/env python3
"""v1.19 score/assumption registry hardening audit.

This tool turns the qualitative score registry into a reproducible transparency layer:
- checks score-like BusState variables are registered;
- exports a machine-readable registry table;
- optionally runs a scenario subset and checks numeric hard ranges;
- produces a reviewer-oriented markdown report.

It is not clinical validation. It only detects missing documentation and obvious
software-range regressions for heuristic scores/proxies/modifiers.
"""
from __future__ import annotations

import argparse
import ast
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.simtools import run_scenario, write_json  # noqa: E402

BUS_PATH = ROOT / "core" / "bus.py"
DEFAULT_REGISTRY = ROOT / "data" / "score_assumption_registry_v1.19.yaml"
DEFAULT_SCENARIOS = ROOT / "data" / "score_assumption_audit_scenarios_v1.19.yaml"
PATTERNS = ("index", "score", "risk", "proxy", "mod", "alert", "effect", "tone", "drive", "burden", "frac", "severity", "readiness")
EXCLUDE = {"vent_mode", "owner_modifier_revision", "residual_owner_modifier_revision", "GRC_units_given", "FFP_mL_given", "PLT_units_given"}


def bus_fields() -> list[str]:
    tree = ast.parse(BUS_PATH.read_text(encoding="utf-8-sig"))
    fields: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "BusState":
            for stmt in node.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    fields.append(stmt.target.id)
    return fields


def score_like(fields: list[str]) -> set[str]:
    out: set[str] = set()
    for f in fields:
        fl = f.lower()
        if f not in EXCLUDE and (any(p in fl for p in PATTERNS) or fl.endswith("_add")):
            out.add(f)
    return out


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def registry_entries(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(e.get("variable")): e for e in registry.get("entries", []) if e.get("variable")}


def build_registry_table(registry: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for e in registry.get("entries", []):
        nr = e.get("numeric_range", {}) or {}
        hard = nr.get("hard", [None, None]) or [None, None]
        expected = nr.get("expected", [None, None]) or [None, None]
        rg = e.get("range", {}) or {}
        reviewer = e.get("reviewer_guidance", {}) or {}
        rows.append({
            "variable": e.get("variable", ""),
            "module": e.get("module", ""),
            "kind": e.get("kind", ""),
            "assumption_level": e.get("assumption_level", ""),
            "formula_status": e.get("formula_status", ""),
            "validation_status": e.get("validation_status", ""),
            "hard_low": hard[0], "hard_high": hard[1],
            "expected_low": expected[0], "expected_high": expected[1],
            "range_note": nr.get("note", rg.get("typical", "")),
            "review_priority": reviewer.get("priority", ""),
            "parameterizable_in_future": reviewer.get("parameterizable_in_future", False),
            "interpretation": e.get("interpretation", ""),
        })
    return pd.DataFrame(rows)


def completeness(registry: dict[str, Any]) -> dict[str, Any]:
    expected = score_like(bus_fields())
    registered = set(registry_entries(registry).keys())
    missing = sorted(expected - registered)
    extra = sorted(registered - expected)
    numeric_registered = [v for v, e in registry_entries(registry).items() if e.get("numeric_range")]
    return {
        "expected_score_like": len(expected),
        "registered": len(registered),
        "missing": missing,
        "extra_non_score_like": extra,
        "numeric_range_entries": len(numeric_registered),
        "status": "PASS" if not missing else "REVIEW",
    }


def _to_float(x: Any) -> float:
    try:
        if isinstance(x, bool):
            return float(int(x))
        return float(x)
    except Exception:
        return float("nan")


def audit_scenarios(registry: dict[str, Any], scenario_names: list[str], dt: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    entries = registry_entries(registry)
    numeric_vars = {v: e for v, e in entries.items() if e.get("numeric_range")}
    rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for scenario in scenario_names:
        try:
            _, df = run_scenario(scenario, dt=dt, quiet=True)
            run_error = ""
        except Exception as exc:  # pragma: no cover - represented in CSV/JSON
            df = pd.DataFrame()
            run_error = repr(exc)
        present = set(df.columns) if not df.empty else set()
        fail_count = 0
        review_count = 0
        pass_count = 0
        not_present_count = 0
        for var, e in numeric_vars.items():
            nr = e.get("numeric_range", {}) or {}
            hard = nr.get("hard", [None, None]) or [None, None]
            expected = nr.get("expected", [None, None]) or [None, None]
            if run_error:
                status = "RUN_ERROR"
                min_v = max_v = final_v = float("nan")
            elif var not in present:
                status = "NOT_PRESENT"
                min_v = max_v = final_v = float("nan")
            else:
                series = pd.to_numeric(df[var], errors="coerce").dropna()
                if series.empty:
                    status = "REVIEW"
                    min_v = max_v = final_v = float("nan")
                else:
                    min_v = float(series.min()); max_v = float(series.max()); final_v = float(series.iloc[-1])
                    hlo, hhi = _to_float(hard[0]), _to_float(hard[1])
                    elo, ehi = _to_float(expected[0]), _to_float(expected[1])
                    hard_ok = (math.isnan(hlo) or min_v >= hlo - 1e-9) and (math.isnan(hhi) or max_v <= hhi + 1e-9)
                    expected_ok = (math.isnan(elo) or min_v >= elo - 1e-9) and (math.isnan(ehi) or max_v <= ehi + 1e-9)
                    if not hard_ok:
                        status = "FAIL"
                    elif not expected_ok:
                        status = "REVIEW"
                    else:
                        status = "PASS"
            if status == "FAIL": fail_count += 1
            elif status == "REVIEW": review_count += 1
            elif status == "PASS": pass_count += 1
            elif status == "NOT_PRESENT": not_present_count += 1
            rows.append({
                "scenario": scenario,
                "variable": var,
                "module": e.get("module", ""),
                "kind": e.get("kind", ""),
                "min": min_v, "max": max_v, "final": final_v,
                "hard_low": hard[0], "hard_high": hard[1],
                "expected_low": expected[0], "expected_high": expected[1],
                "status": status,
                "run_error": run_error,
            })
        summary_rows.append({
            "scenario": scenario,
            "run_error": run_error,
            "pass": pass_count,
            "review": review_count,
            "fail": fail_count,
            "not_present": not_present_count,
        })
    return pd.DataFrame(rows), pd.DataFrame(summary_rows)


def write_report(path: Path, registry: dict[str, Any], comp: dict[str, Any], table: pd.DataFrame, audit: pd.DataFrame | None, scen_summary: pd.DataFrame | None) -> None:
    lines = [
        "# PDT v1.19 Score Assumption Registry Hardening",
        "",
        "This report audits qualitative scores, proxies, risk indices and modifiers.",
        "It is a transparency and software-range check, **not clinical validation**.",
        "",
        f"Registry version: **{registry.get('version', '')}**",
        "",
        "## Registry completeness",
        "",
        f"Score-like BusState variables: **{comp['expected_score_like']}**",
        f"Registered variables: **{comp['registered']}**",
        f"Entries with numeric ranges: **{comp['numeric_range_entries']}**",
        f"Missing score-like variables: **{len(comp['missing'])}**",
        "",
    ]
    if comp["missing"]:
        lines += ["### Missing variables", ""] + [f"- {m}" for m in comp["missing"]] + [""]
    high = table[table.get("review_priority", "") == "high"] if not table.empty else pd.DataFrame()
    lines += ["## High-priority heuristic variables", "", "| Variable | Module | Hard range | Validation status |", "|---|---|---:|---|"]
    for _, r in high.iterrows():
        lines.append(f"| {r['variable']} | {r['module']} | {r['hard_low']}–{r['hard_high']} | {str(r['validation_status']).replace('|','/')} |")
    if scen_summary is not None and not scen_summary.empty:
        total_fail = int(scen_summary["fail"].sum())
        total_review = int(scen_summary["review"].sum())
        total_pass = int(scen_summary["pass"].sum())
        lines += [
            "", "## Scenario range audit", "",
            f"PASS cells: **{total_pass}**  ",
            f"REVIEW cells: **{total_review}**  ",
            f"FAIL cells: **{total_fail}**  ",
            "", "| Scenario | PASS | REVIEW | FAIL | NOT_PRESENT |", "|---|---:|---:|---:|---:|"
        ]
        for _, r in scen_summary.iterrows():
            lines.append(f"| {r['scenario']} | {int(r['pass'])} | {int(r['review'])} | {int(r['fail'])} | {int(r['not_present'])} |")
        if audit is not None and not audit.empty:
            bad = audit[audit["status"].isin(["FAIL", "REVIEW"])].head(50)
            if not bad.empty:
                lines += ["", "### First REVIEW/FAIL cells", "", "| Scenario | Variable | Min | Max | Expected | Hard | Status |", "|---|---|---:|---:|---:|---:|---|"]
                for _, r in bad.iterrows():
                    lines.append(f"| {r['scenario']} | {r['variable']} | {r['min']:.4g} | {r['max']:.4g} | {r['expected_low']}–{r['expected_high']} | {r['hard_low']}–{r['hard_high']} | {r['status']} |")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    ap.add_argument("--scenario-spec", default=str(DEFAULT_SCENARIOS))
    ap.add_argument("--outdir", default=str(ROOT / "outputs" / "score_assumption_audit_v1.19"))
    ap.add_argument("--dt", type=float, default=None)
    ap.add_argument("--scenarios", nargs="*", default=None)
    ap.add_argument("--no-run", action="store_true")
    ap.add_argument("--fail-on-fail", action="store_true")
    args = ap.parse_args()

    registry = load_yaml(Path(args.registry))
    scenario_spec = load_yaml(Path(args.scenario_spec)) if Path(args.scenario_spec).exists() else {}
    dt = float(args.dt if args.dt is not None else scenario_spec.get("default_dt_s", 10.0))
    scenarios = args.scenarios if args.scenarios else list(scenario_spec.get("scenarios", []))
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)

    comp = completeness(registry)
    table = build_registry_table(registry)
    table.to_csv(outdir / "score_assumption_registry_v119.csv", index=False)
    (outdir / "score_assumption_completeness_v119.json").write_text(json.dumps(comp, indent=2), encoding="utf-8")

    audit_df = None; scen_summary = None
    if not args.no_run:
        audit_df, scen_summary = audit_scenarios(registry, scenarios, dt=dt)
        audit_df.to_csv(outdir / "score_assumption_range_audit_v119.csv", index=False)
        scen_summary.to_csv(outdir / "score_assumption_scenario_summary_v119.csv", index=False)

    write_report(outdir / "score_assumption_audit_report_v119.md", registry, comp, table, audit_df, scen_summary)

    fail = int(scen_summary["fail"].sum()) if scen_summary is not None and not scen_summary.empty else 0
    review = int(scen_summary["review"].sum()) if scen_summary is not None and not scen_summary.empty else 0
    summary = {
        "release": "v1.19-alpha",
        "registry": Path(args.registry).name,
        "registered": comp["registered"],
        "expected_score_like": comp["expected_score_like"],
        "missing": len(comp["missing"]),
        "numeric_range_entries": comp["numeric_range_entries"],
        "scenarios_evaluated": len(scenarios) if not args.no_run else 0,
        "range_pass": int(scen_summary["pass"].sum()) if scen_summary is not None and not scen_summary.empty else 0,
        "range_review": review,
        "range_fail": fail,
        "status": "PASS" if not comp["missing"] and fail == 0 else "REVIEW",
    }
    write_json(summary, outdir / "score_assumption_audit_summary_v119.json")
    print(json.dumps(summary, indent=2))
    if args.fail_on_fail and (summary["missing"] or summary["range_fail"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
