#!/usr/bin/env python3
"""PDT v5.0C plausibility guardrail audit.

Checks benchmark/Monte Carlo outputs for impossible or suspicious states.
This is an audit gate, not clinical validation and not medical guidance.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_yaml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _isfinite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except Exception:
        return False


def _value(row: Mapping[str, Any], key: str, default: float = math.nan) -> float:
    try:
        return float(row.get(key, default))
    except Exception:
        return default


def check_bounds(row: Mapping[str, Any], bounds: Mapping[str, Any], severity: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for key, interval in bounds.items():
        if key not in row:
            continue
        val = _value(row, key)
        lo, hi = float(interval[0]), float(interval[1])
        if not math.isfinite(val):
            out.append({"severity": "critical", "rule": f"{key}:non_finite", "metric": key, "value": str(row.get(key, ""))})
        elif val < lo or val > hi:
            out.append({"severity": severity, "rule": f"{key}:outside_{lo:g}_{hi:g}", "metric": key, "value": val})
    return out


def check_logic(row: Mapping[str, Any], rules: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    env: Dict[str, Any] = {k: _value(row, k) for k in row.keys()}
    env["isfinite"] = _isfinite
    out: List[Dict[str, Any]] = []
    for rule in rules:
        expr = str(rule.get("expression", "True"))
        try:
            ok = bool(eval(expr, {"__builtins__": {}}, env))
        except Exception as exc:
            out.append({"severity": "critical", "rule": f"{rule.get('id')}:eval_error", "metric": "logical_rule", "value": repr(exc)})
            continue
        if not ok:
            out.append({"severity": "critical", "rule": str(rule.get("id")), "metric": "logical_rule", "value": expr})
    return out


def audit_frame(df: pd.DataFrame, spec: Mapping[str, Any]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    critical = spec.get("critical_bounds", {}) or {}
    soft_by_scenario = spec.get("soft_bounds", {}) or {}
    rules = spec.get("logical_rules", []) or []
    for idx, row in df.iterrows():
        base = row.to_dict()
        scenario = str(base.get("scenario", ""))
        findings = []
        findings.extend(check_bounds(base, critical, "critical"))
        findings.extend(check_bounds(base, soft_by_scenario.get(scenario, {}) or {}, "review"))
        findings.extend(check_logic(base, rules))
        for finding in findings:
            rows.append({
                "row_index": int(idx),
                "scenario": scenario,
                "run": base.get("run", ""),
                **finding,
            })
    return pd.DataFrame(rows, columns=["row_index", "scenario", "run", "severity", "rule", "metric", "value"])


def write_report(path: Path, summary: Mapping[str, Any], findings: pd.DataFrame, spec: Mapping[str, Any]) -> None:
    lines = [
        "# Step 5.0C — Plausibility Guardrails Report",
        "",
        "Scope: audit-only guardrails over benchmark and Monte Carlo outputs.",
        "",
        "This is **not** clinical validation and **not** medical decision support.",
        "",
        f"Spec version: **{spec.get('version', '')}**",
        f"Rows audited: **{summary.get('rows_audited', 0)}**",
        f"Critical findings: **{summary.get('critical_findings', 0)}**",
        f"Review findings: **{summary.get('review_findings', 0)}**",
        f"Pass guardrails: **{summary.get('pass_guardrails', False)}**",
        "",
        "## Finding categories",
        "",
        "| Severity | Count |",
        "|---|---:|",
        f"| critical | {summary.get('critical_findings', 0)} |",
        f"| review | {summary.get('review_findings', 0)} |",
        "",
        "## Interpretation",
        "",
    ]
    if int(summary.get("critical_findings", 0)) == 0:
        lines.append("No biologically impossible or numerically non-finite states were detected by the critical guardrails.")
    else:
        lines.append("Critical findings require correction before promotion to the next validation stage.")
    if int(summary.get("review_findings", 0)):
        lines.append("Review findings are scenario-specific plausibility warnings and should be interpreted manually.")
    lines.append("")
    if not findings.empty:
        lines += ["## Top findings", "", "| Scenario | Run | Severity | Rule | Value |", "|---|---:|---|---|---:|"]
        for _, r in findings.head(30).iterrows():
            lines.append(f"| {r['scenario']} | {r['run']} | {r['severity']} | {r['rule']} | {r['value']} |")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default=str(ROOT / "data" / "plausibility_guardrails_v5.0C.yaml"))
    ap.add_argument("--input", default=str(ROOT / "outputs" / "monte_carlo_v5.0B" / "monte_carlo_results_v50B.csv"))
    ap.add_argument("--outdir", default=str(ROOT / "outputs" / "plausibility_guardrails_v5.0C"))
    ap.add_argument("--fail-on-critical", action="store_true")
    args = ap.parse_args()

    spec = load_yaml(Path(args.spec))
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(args.input)
    findings = audit_frame(df, spec)
    findings.to_csv(outdir / "plausibility_guardrail_findings_v50C.csv", index=False)
    critical = int((findings.get("severity", pd.Series(dtype=str)) == "critical").sum()) if not findings.empty else 0
    review = int((findings.get("severity", pd.Series(dtype=str)) == "review").sum()) if not findings.empty else 0
    summary = {
        "release_step": "5.0C",
        "rows_audited": int(len(df)),
        "findings": int(len(findings)),
        "critical_findings": critical,
        "review_findings": review,
        "pass_guardrails": critical == 0,
        "input": str(args.input),
        "spec": str(args.spec),
    }
    (outdir / "plausibility_guardrail_summary_v50C.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_report(outdir / "plausibility_guardrail_report_v50C.md", summary, findings, spec)
    print(json.dumps(summary, indent=2))
    if args.fail_on_critical and critical:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
