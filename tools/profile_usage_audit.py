#!/usr/bin/env python3
"""
v0.44 Profile / age-scaling usage audit.

Static audit of how strongly modules use pediatric profile information.
This is not a physiological validation tool. It identifies whether modules are:
  - profile-aware (age_group / patient_profile / profile fields)
  - weight-scaled only
  - mostly fixed-constant / 20 kg centric

Outputs are intended for model governance and refactoring prioritization.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Dict, List

try:
    import yaml
except Exception as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required for this audit") from exc

ROOT = Path(__file__).resolve().parents[1]
MODULES_DIR = ROOT / "modules"
CORE_DIR = ROOT / "core"
SCENARIOS_DIR = ROOT / "scenarios"
OUT_DIR = ROOT / "outputs" / "validation_pack"

PROFILE_KEYS = [
    "age_y",
    "weight_kg",
    "age_group",
    "HR",
    "RR",
    "MAP",
    "Vt_ml_kg",
    "FRC_ml_kg",
    "blood_volume_ml_kg",
    "Hb",
    "VO2_ml_kg_min",
    "GFR_ml_min_1_73m2",
    "C_rs_ml_cmH2O_kg",
    "Vd_Vt",
]

AGE_CRITICAL_PATTERNS = {
    "modules/pharmacology/pk_pd.py": "PK/PD allometry and age-dependent clearance remain high priority.",
    "modules/pharmacology/steroids.py": "Steroid exposure and stress-axis effects should be age/profile aware.",
    "modules/pharmacology/transfusion.py": "Product volumes are weight-based; age/profile thresholds need explicit governance.",
    "modules/respiratory/mechanics.py": "Respiratory mechanics should use profile-derived FRC, Vt/kg, compliance and dead-space anchors.",
    "modules/respiratory/gas_exchange.py": "Gas exchange should be checked for age/profile assumptions and dead-space scaling.",
    "modules/ventilator/ventilator.py": "Ventilator settings should remain weight/protective-ventilation scaled and profile documented.",
    "modules/cardiovascular/circulation.py": "Hemodynamics should be checked against age-specific HR/MAP/SVR/CO anchors.",
    "modules/renal/aki_crrt.py": "AKI/CRRT requires weight and age/GFR scaling.",
    "modules/renal/fluid_balance.py": "Fluid/diuretic response should be profile and weight scaled.",
    "modules/metabolism/metabolism.py": "VO2/VCO2 and lactate kinetics should scale by weight and age/metabolic profile.",
    "modules/nutrition/catabolism.py": "Nutrition targets should use age/profile requirements, not only weight.",
    "modules/nutrition/glucose.py": "GIR/insulin/glucose handling is strongly age dependent.",
    "modules/endocrine/stress_axis.py": "Endocrine stress responses need age/profile documentation.",
    "modules/hematology/oxygen_transport.py": "Hb and oxygen transport should remain age/profile aware.",
}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def count_regex(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text))


def classify_module(rel: str, text: str) -> Dict[str, object]:
    uses_weight = "weight_kg" in text or re.search(r"\bwt\b", text) is not None
    uses_age_y = "age_y" in text
    uses_age_group = "age_group" in text
    uses_patient_profile = "patient_profile" in text or "pediatric_profiles" in text or "get_profile" in text
    uses_profile_fields = any(k in text for k in PROFILE_KEYS if k not in {"weight_kg", "age_y", "age_group"})
    fixed_20 = count_regex(text, r"20\.0|20\b")
    fixed_default_weight = count_regex(text, r"['\"]weight_kg['\"]\s*:\s*20\.0")
    profile_field_hits = ";".join([k for k in PROFILE_KEYS if k in text])

    # Strict classification: merely mentioning generic variables such as HR/MAP/RR
    # is not enough to call a module profile-aware. Direct age/profile hooks
    # are required. Profile-field hits are retained as separate evidence.
    if uses_patient_profile or uses_age_group or uses_age_y:
        profile_awareness = "profile_or_age_aware"
    elif uses_weight:
        profile_awareness = "weight_scaled_only"
    else:
        profile_awareness = "profile_blind_or_fixed_constant"

    if profile_awareness == "profile_blind_or_fixed_constant":
        risk = "HIGH" if rel in AGE_CRITICAL_PATTERNS else "MEDIUM"
    elif profile_awareness == "weight_scaled_only":
        risk = "MEDIUM" if rel in AGE_CRITICAL_PATTERNS else "LOW_MEDIUM"
    else:
        risk = "LOW_MEDIUM" if rel in AGE_CRITICAL_PATTERNS else "LOW"

    if fixed_default_weight and not (uses_age_y or uses_age_group or uses_patient_profile):
        risk = "HIGH" if rel in AGE_CRITICAL_PATTERNS else "MEDIUM"

    recommendation = AGE_CRITICAL_PATTERNS.get(rel, "Document assumptions; add profile hooks if module becomes clinically central.")
    if profile_awareness == "weight_scaled_only":
        recommendation = "Add age_group/profile hooks; replace 20 kg defaults with profile-derived anchors where clinically relevant. " + recommendation
    elif profile_awareness == "profile_blind_or_fixed_constant":
        recommendation = "Review for hidden 20 kg centric constants and add explicit assumptions or profile scaling. " + recommendation

    return {
        "file": rel,
        "domain": rel.split("/")[1] if rel.startswith("modules/") else "core",
        "uses_weight_kg": bool(uses_weight),
        "uses_age_y": bool(uses_age_y),
        "uses_age_group": bool(uses_age_group),
        "uses_patient_profile_or_loader": bool(uses_patient_profile),
        "uses_profile_field_names": bool(uses_profile_fields),
        "profile_field_hits": profile_field_hits,
        "fixed_20_hits": fixed_20,
        "fixed_default_weight_20kg_hits": fixed_default_weight,
        "classification": profile_awareness,
        "risk": risk,
        "recommendation": recommendation,
    }


def audit_modules() -> List[Dict[str, object]]:
    files = sorted(list(MODULES_DIR.rglob("*.py")) + [CORE_DIR / "scenario.py", CORE_DIR / "profiles.py"])
    rows = []
    for path in files:
        if path.name == "__init__.py":
            continue
        rel = path.relative_to(ROOT).as_posix()
        rows.append(classify_module(rel, read_text(path)))
    return rows


def audit_scenarios() -> List[Dict[str, object]]:
    rows = []
    for path in sorted(SCENARIOS_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text()) or {}
        patient = data.get("patient") or {}
        rows.append({
            "scenario": path.stem,
            "profile": patient.get("profile", ""),
            "age_y": patient.get("age_y", ""),
            "weight_kg": patient.get("weight_kg", ""),
            "has_profile": bool(patient.get("profile")),
            "has_age_y": "age_y" in patient,
            "has_weight_kg": "weight_kg" in patient,
        })
    return rows


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def render_report(module_rows: List[Dict[str, object]], scenario_rows: List[Dict[str, object]], summary: Dict[str, object]) -> str:
    lines = []
    lines.append("# v0.44 Profile / age-scaling usage audit")
    lines.append("")
    lines.append("This is a static governance audit. It does not prove physiological validity. It identifies whether modules use pediatric profile information, weight only, or mostly fixed constants.")
    lines.append("")
    lines.append("## Summary")
    for k, v in summary.items():
        if isinstance(v, (dict, list)):
            continue
        lines.append(f"- **{k}**: {v}")
    lines.append("")
    lines.append("## Classification counts")
    for k, v in summary["classification_counts"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Risk counts")
    for k, v in summary["risk_counts"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## High-priority modules")
    high = [r for r in module_rows if r["risk"] == "HIGH"]
    if not high:
        lines.append("No HIGH-risk modules were detected by the static audit.")
    else:
        lines.append("| module | classification | recommendation |")
        lines.append("|---|---|---|")
        for r in high:
            rec = str(r["recommendation"]).replace("|", "/")
            lines.append(f"| `{r['file']}` | {r['classification']} | {rec} |")
    lines.append("")
    lines.append("## Weight-only modules to prioritize")
    weight_only = [r for r in module_rows if r["classification"] == "weight_scaled_only"]
    lines.append("| module | risk | fixed 20 kg defaults | recommendation |")
    lines.append("|---|---:|---:|---|")
    for r in weight_only:
        rec = str(r["recommendation"]).replace("|", "/")
        lines.append(f"| `{r['file']}` | {r['risk']} | {r['fixed_default_weight_20kg_hits']} | {rec} |")
    lines.append("")
    lines.append("## Scenario patient metadata")
    lines.append(f"- scenarios audited: {len(scenario_rows)}")
    lines.append(f"- scenarios with explicit profile: {sum(1 for r in scenario_rows if r['has_profile'])}")
    lines.append(f"- scenarios with age_y: {sum(1 for r in scenario_rows if r['has_age_y'])}")
    lines.append(f"- scenarios with weight_kg: {sum(1 for r in scenario_rows if r['has_weight_kg'])}")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("The model is not purely 20 kg centric because scenarios and several modules use weight and some profile/age fields. However, many modules still use weight-only scaling or 20 kg defaults. The next refactor should prioritize PK/PD, respiratory mechanics/gas exchange, cardiovascular baselines, renal/CRRT, glucose/insulin and nutrition.")
    lines.append("")
    lines.append("## Limitation")
    lines.append("This audit is intentionally conservative and static. A module may use age indirectly through initialized BusState values even if the module itself does not contain age-related strings. Conversely, mentioning a profile field does not guarantee a clinically validated age-scaling equation.")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=str(OUT_DIR))
    ap.add_argument("--fail-on-high", action="store_true", help="Exit non-zero if HIGH-risk modules are found. Usually not used yet; v0.44 is an audit.")
    args = ap.parse_args()

    out = Path(args.output_dir)
    module_rows = audit_modules()
    scenario_rows = audit_scenarios()

    classification_counts: Dict[str, int] = {}
    risk_counts: Dict[str, int] = {}
    for r in module_rows:
        classification_counts[str(r["classification"])] = classification_counts.get(str(r["classification"]), 0) + 1
        risk_counts[str(r["risk"])] = risk_counts.get(str(r["risk"]), 0) + 1

    summary = {
        "version": "0.44",
        "modules_audited": len(module_rows),
        "scenarios_audited": len(scenario_rows),
        "scenarios_with_profile": sum(1 for r in scenario_rows if r["has_profile"]),
        "scenarios_with_age_y": sum(1 for r in scenario_rows if r["has_age_y"]),
        "scenarios_with_weight_kg": sum(1 for r in scenario_rows if r["has_weight_kg"]),
        "classification_counts": classification_counts,
        "risk_counts": risk_counts,
        "high_risk_modules": [r["file"] for r in module_rows if r["risk"] == "HIGH"],
        "weight_only_modules": [r["file"] for r in module_rows if r["classification"] == "weight_scaled_only"],
    }

    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "profile_usage_audit_v044_modules.csv", module_rows)
    write_csv(out / "profile_usage_audit_v044_scenarios.csv", scenario_rows)
    (out / "profile_usage_audit_v044_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out / "profile_usage_audit_v044_report.md").write_text(render_report(module_rows, scenario_rows, summary), encoding="utf-8")

    print("Profile usage audit v0.44")
    print(f"modules audited: {summary['modules_audited']}")
    print(f"scenarios audited: {summary['scenarios_audited']}")
    print(f"classification counts: {classification_counts}")
    print(f"risk counts: {risk_counts}")
    print(f"report: {out / 'profile_usage_audit_v044_report.md'}")

    if args.fail_on_high and summary["high_risk_modules"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
