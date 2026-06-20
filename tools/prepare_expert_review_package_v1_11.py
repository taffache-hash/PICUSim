#!/usr/bin/env python3
"""Prepare v1.11 structured expert-review package for PDT.

The generated package supports independent face-validity, educational-usefulness
and model-transparency review. It is deliberately framed as expert review, not
clinical validation.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.simtools import load_yaml, run_config  # noqa: E402

OUTPUT_KEYS_FALLBACK = [
    "HR", "MAP", "CO", "SaO2", "PaO2", "PaCO2", "pH_a", "Vt", "PEEP", "FiO2",
    "Pplat", "Pdriving", "MP", "R_rs", "C_rs", "recruited_frac", "vq_shunt_frac",
    "vq_deadspace_frac", "lactate", "vasoplegia_index", "sepsis_severity_score",
    "fluid_responsiveness", "ICP_mmHg", "CPP_mmHg", "GCS_proxy", "sedation_score",
    "pain_score", "C_midazolam_ng_mL", "C_ketamine_ng_mL", "C_rocuronium_ng_mL",
    "pk_crrt_effluent_L_min", "pk_crrt_total_extra_clearance_L_min",
]

SCENARIO_COLUMNS = [
    "review_id", "reviewer_role", "reviewer_expertise_years", "scenario",
    "clinical_domain", "complexity", "primary_objective",
    "physiologic_plausibility_1_5", "trajectory_plausibility_1_5",
    "intervention_response_1_5", "educational_usefulness_1_5",
    "safety_misinterpretation_risk_1_5", "transparency_of_assumptions_1_5",
    "major_implausibility_yes_no", "major_implausibility_details",
    "recommended_action_accept_minor_major_reject", "free_text_notes",
]

MODULE_COLUMNS = [
    "review_id", "reviewer_role", "reviewer_expertise_years", "module", "focus",
    "formulation_transparency_1_5", "face_validity_1_5", "educational_value_1_5",
    "missing_feature_priority_low_medium_high", "evidence_needed_before_publication",
    "recommended_action_accept_minor_major_reject", "free_text_notes",
]

REVIEWER_COLUMNS = [
    "review_id", "reviewer_role", "clinical_or_modeling_expertise_years",
    "institution_or_context_optional", "conflict_of_interest_yes_no",
    "conflict_details_optional", "review_date", "permission_to_acknowledge_yes_no",
]


def read_protocol(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text())


def scenario_config_summary(scenario: str) -> Dict[str, Any]:
    path = ROOT / "scenarios" / f"{scenario}.yaml"
    cfg = load_yaml(path)
    patient = cfg.get("patient", {}) or {}
    resp = cfg.get("respiratory", {}) or {}
    cv = cfg.get("cardiovascular", {}) or {}
    return {
        "scenario": scenario,
        "path": str(path.relative_to(ROOT)),
        "description": str(cfg.get("description", "")),
        "simulation_time_s": cfg.get("simulation_time_s", ""),
        "patient_profile": patient.get("profile", ""),
        "weight_kg": patient.get("weight_kg", ""),
        "age_y": patient.get("age_y", ""),
        "resp_mode": resp.get("mode", cfg.get("ventilator", {}).get("mode", "")),
        "FiO2": resp.get("FiO2", ""),
        "PEEP": resp.get("PEEP", ""),
        "HR": cv.get("HR", ""),
        "MAP": cv.get("MAP", ""),
    }


def run_snapshot(scenario: str, keys: Iterable[str], dt: float, max_seconds: float | None) -> List[Dict[str, Any]]:
    cfg = load_yaml(ROOT / "scenarios" / f"{scenario}.yaml")
    if max_seconds is not None:
        cfg["simulation_time_s"] = min(float(cfg.get("simulation_time_s", max_seconds)), float(max_seconds))
    df = run_config(cfg, dt=dt, quiet=True)
    rows: List[Dict[str, Any]] = []
    for key in keys:
        if key not in df.columns:
            continue
        series = pd.to_numeric(df[key], errors="coerce").dropna()
        if series.empty:
            continue
        rows.append({
            "scenario": scenario,
            "variable": key,
            "initial": float(series.iloc[0]),
            "final": float(series.iloc[-1]),
            "minimum": float(series.min()),
            "maximum": float(series.max()),
        })
    return rows


def write_instructions(protocol: Dict[str, Any], outdir: Path) -> None:
    lines = [
        "# PDT v1.11 Expert Review Package", "",
        "## Purpose", "",
        "This package is for structured independent expert review of face validity, educational usefulness, and model transparency.",
        "It is not patient-level validation, not clinical decision support, and not a medical-device evaluation.", "",
        "## Requested reviewer panel", "",
    ]
    for role, n in protocol.get("minimum_reviewer_panel", {}).items():
        lines.append(f"- {role}: minimum {n}")
    lines += [
        "", "## Rating scale", "",
    ]
    for score, label in protocol.get("rating_scale", {}).items():
        lines.append(f"- {score}: {label}")
    lines += [
        "", "## How to complete", "",
        "1. Fill `reviewer_metadata_template.csv` once per reviewer.",
        "2. Fill `scenario_review_template.csv` for all scenarios within the reviewer expertise domain.",
        "3. Fill `module_review_template.csv` only for modules within the reviewer expertise domain.",
        "4. Use the Markdown sheets in `scenario_sheets/` for printable per-scenario review.",
        "5. Place completed CSV files in `completed_reviews/` and run `tools/aggregate_expert_reviews_v1_11.py`.", "",
        "## Decision rule", "",
        "A low score or any major-implausibility flag is a triage trigger, not a definitive rejection. The purpose is to identify what must be fixed before a publication-grade release.",
    ]
    (outdir / "00_INSTRUCTIONS.md").write_text("\n".join(lines))


def write_model_disclosure(protocol: Dict[str, Any], outdir: Path) -> None:
    lines = [
        "# Model Disclosure Statement — PDT v1.11", "",
        "This framework is an exploratory pediatric critical-care physiology simulation framework for education, in-silico model development, and hypothesis generation.",
        "It is not a validated patient-specific digital twin and must not be used for clinical decisions, dosing, ventilator settings, prognostication, triage, or treatment selection.", "",
        "## What expert reviewers are asked to judge", "",
        "- Whether scenario trajectories are physiologically plausible at face-validity level.",
        "- Whether the selected variables are educationally useful and interpretable.",
        "- Whether assumptions and limitations are transparent enough for a public alpha release.",
        "- Whether any output could create a safety-misinterpretation risk if shown to learners without debriefing.", "",
        "## Known limitations to consider", "",
        "- Many modules remain educational scaffolds rather than calibrated patient-specific models.",
        "- The respiratory mechanics module uses a public lumped formulation, not regional mechanics.",
        "- The V/Q module is a three-zone qualitative scaffold and not MIGET-level validation.",
        "- PK/PD models use allometry and broad literature envelopes; they are not dosing tools.",
        "- CRRT drug clearance is deliberately conservative and does not model membrane adsorption, downtime, dynamic protein binding, therapeutic drug monitoring, or metabolites.",
        "- Congenital heart disease, ECMO, pericardial constraints, and detailed ventricular interaction are not yet implemented.", "",
        "## Output interpretation", "",
        "Scores and flags from expert review should be reported as external face-validity evidence, not as proof of clinical predictive accuracy.",
    ]
    (outdir / "01_MODEL_DISCLOSURE_STATEMENT.md").write_text("\n".join(lines))


def write_templates(protocol: Dict[str, Any], outdir: Path) -> None:
    scenario_rows: List[Dict[str, Any]] = []
    for item in protocol.get("scenario_set", []):
        row = {c: "" for c in SCENARIO_COLUMNS}
        row.update({
            "scenario": item.get("scenario", ""),
            "clinical_domain": item.get("clinical_domain", ""),
            "complexity": item.get("complexity", ""),
            "primary_objective": item.get("primary_objective", ""),
        })
        scenario_rows.append(row)
    pd.DataFrame(scenario_rows, columns=SCENARIO_COLUMNS).to_csv(outdir / "scenario_review_template.csv", index=False)

    module_rows: List[Dict[str, Any]] = []
    for item in protocol.get("module_set", []):
        row = {c: "" for c in MODULE_COLUMNS}
        row.update({
            "module": item.get("module", ""),
            "reviewer_role": item.get("reviewer_role", ""),
            "focus": item.get("focus", ""),
        })
        module_rows.append(row)
    pd.DataFrame(module_rows, columns=MODULE_COLUMNS).to_csv(outdir / "module_review_template.csv", index=False)
    pd.DataFrame([{c: "" for c in REVIEWER_COLUMNS}], columns=REVIEWER_COLUMNS).to_csv(outdir / "reviewer_metadata_template.csv", index=False)


def write_scenario_sheets(protocol: Dict[str, Any], outdir: Path, snapshot_df: pd.DataFrame) -> None:
    sheet_dir = outdir / "scenario_sheets"
    sheet_dir.mkdir(parents=True, exist_ok=True)
    index_lines = ["# Scenario review sheets", ""]
    summaries = {r["scenario"]: r for r in (scenario_config_summary(x["scenario"]) for x in protocol.get("scenario_set", []))}
    for item in protocol.get("scenario_set", []):
        scenario = item["scenario"]
        summary = summaries.get(scenario, {})
        sub = snapshot_df[snapshot_df["scenario"] == scenario] if len(snapshot_df) else pd.DataFrame()
        lines = [
            f"# Expert Review Sheet — {scenario}", "",
            f"**Clinical domain:** {item.get('clinical_domain', '')}",
            f"**Complexity:** {item.get('complexity', '')}",
            f"**Primary objective:** {item.get('primary_objective', '')}", "",
            "## Scenario configuration summary", "",
            f"- Description: {summary.get('description', '') or 'not provided'}",
            f"- Patient profile: {summary.get('patient_profile', '')}",
            f"- Weight: {summary.get('weight_kg', '')} kg",
            f"- Age: {summary.get('age_y', '')} years",
            f"- Simulation time: {summary.get('simulation_time_s', '')} s", "",
            "## Variables requested for review", "",
            ", ".join(item.get("variables_to_review", [])), "",
        ]
        if len(sub):
            lines += ["## Optional simulated snapshot", "", "| Variable | Initial | Final | Minimum | Maximum |", "|---|---:|---:|---:|---:|"]
            for _, r in sub.iterrows():
                lines.append(f"| {r['variable']} | {r['initial']:.4g} | {r['final']:.4g} | {r['minimum']:.4g} | {r['maximum']:.4g} |")
            lines.append("")
        lines += [
            "## Reviewer judgement", "",
            "Physiologic plausibility 1–5: ____", "",
            "Trajectory plausibility 1–5: ____", "",
            "Intervention response 1–5: ____", "",
            "Educational usefulness 1–5: ____", "",
            "Safety-misinterpretation risk 1–5: ____", "",
            "Major implausibility?  yes / no", "",
            "Notes:", "", "................................................................................", "", "................................................................................", "",
            "Recommendation: accept / minor revision / major revision / reject", "",
        ]
        p = sheet_dir / f"{scenario}_expert_review.md"
        p.write_text("\n".join(lines))
        index_lines.append(f"- [{scenario}]({p.name})")
    (sheet_dir / "INDEX.md").write_text("\n".join(index_lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--protocol", default=str(ROOT / "data" / "expert_review_protocol_v1.11.yaml"))
    ap.add_argument("--outdir", default=str(ROOT / "outputs" / "expert_review_v1.11"))
    ap.add_argument("--dt", type=float, default=1.0)
    ap.add_argument("--run-scenarios", action="store_true", help="Run selected scenarios and export initial/final/min/max snapshots.")
    ap.add_argument("--max-seconds", type=float, default=None, help="Optional cap for scenario run snapshots.")
    args = ap.parse_args()

    protocol = read_protocol(Path(args.protocol))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "completed_reviews").mkdir(exist_ok=True)

    write_instructions(protocol, outdir)
    write_model_disclosure(protocol, outdir)
    write_templates(protocol, outdir)

    scenario_rows = [scenario_config_summary(item["scenario"]) for item in protocol.get("scenario_set", [])]
    pd.DataFrame(scenario_rows).to_csv(outdir / "scenario_configuration_summary.csv", index=False)

    snapshot_rows: List[Dict[str, Any]] = []
    if args.run_scenarios:
        for item in protocol.get("scenario_set", []):
            keys = item.get("variables_to_review", OUTPUT_KEYS_FALLBACK)
            try:
                snapshot_rows.extend(run_snapshot(item["scenario"], keys, dt=args.dt, max_seconds=args.max_seconds))
            except Exception as exc:
                snapshot_rows.append({
                    "scenario": item["scenario"], "variable": "RUN_ERROR", "initial": None,
                    "final": None, "minimum": None, "maximum": None, "error": str(exc),
                })
    snapshot_df = pd.DataFrame(snapshot_rows)
    if len(snapshot_df):
        snapshot_df.to_csv(outdir / "scenario_variable_snapshots.csv", index=False)
    else:
        snapshot_df = pd.DataFrame(columns=["scenario", "variable", "initial", "final", "minimum", "maximum"])
        snapshot_df.to_csv(outdir / "scenario_variable_snapshots.csv", index=False)

    write_scenario_sheets(protocol, outdir, snapshot_df)

    manifest = {
        "release": protocol.get("release", "v1.11-alpha"),
        "status": "PASS",
        "scenario_count": len(protocol.get("scenario_set", [])),
        "module_count": len(protocol.get("module_set", [])),
        "run_scenarios": bool(args.run_scenarios),
        "snapshot_rows": int(len(snapshot_df)),
        "required_files": [
            "00_INSTRUCTIONS.md", "01_MODEL_DISCLOSURE_STATEMENT.md",
            "scenario_review_template.csv", "module_review_template.csv",
            "reviewer_metadata_template.csv", "scenario_configuration_summary.csv",
            "scenario_variable_snapshots.csv", "scenario_sheets/INDEX.md",
        ],
    }
    (outdir / "expert_review_package_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Expert-review package written to {outdir}")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
