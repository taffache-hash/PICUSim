#!/usr/bin/env python3
"""Public-clean alpha package sanity check."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "VERSION",
    "README.md",
    "DISCLAIMER_NOT_FOR_CLINICAL_USE.md",
    "LICENSE_PENDING.md",
    "CITATION.cff",
    "pyproject.toml",
    "requirements.txt",
    "run_simulation.py",
    "docs/QUICKSTART.md",
    "docs/MODEL_LIMITATIONS.md",
    "docs/EXPERT_REVIEW.md",
    "docs/PKPD_VANCOMYCIN_v1.12.md",
    "docs/PKPD_FUROSEMIDE_v1.13.md",
    "docs/PKPD_MORPHINE_v1.14.md",
    "docs/PKPD_CLONIDINE_v1.15.md",
    "docs/INSULIN_GLUCOSE_PD_v1.16.md",
    "docs/PKPD_PIPERACILLIN_TAZOBACTAM_v1.17.md",
    "data/crrt_drug_clearance_v1.10.yaml",
    "scenarios/picu_vancomycin_aki_crrt_v1_12.yaml",
    "tools/pkpd_vancomycin_audit_v1_12.py",
    "scenarios/picu_furosemide_fluid_overload_v1_13.yaml",
    "tools/pkpd_furosemide_audit_v1_13.py",
    "scenarios/picu_morphine_analgesia_aki_v1_14.yaml",
    "tools/pkpd_morphine_audit_v1_14.py",
    "scenarios/picu_clonidine_withdrawal_weaning_v1_15.yaml",
    "tools/pkpd_clonidine_audit_v1_15.py",
    "scenarios/picu_insulin_stress_hyperglycemia_v1_16.yaml",
    "tools/pkpd_insulin_audit_v1_16.py",
    "tests/test_v116_insulin_pkpd.py",
    "scenarios/picu_piperacillin_tazobactam_sepsis_v1_17.yaml",
    "tools/pkpd_piperacillin_tazobactam_audit_v1_17.py",
    "tests/test_v117_piperacillin_tazobactam_pkpd.py",
    "data/literature_benchmark_targets_v1.18.yaml",
    "tools/benchmark_matrix_v1_18.py",
    "docs/BENCHMARK_MATRIX_v1.18.md",
    "tests/test_v118_benchmark_matrix.py",
    "data/score_assumption_registry_v1.19.yaml",
    "data/score_assumption_audit_scenarios_v1.19.yaml",
    "tools/score_assumption_audit_v1_19.py",
    "docs/SCORE_ASSUMPTION_HARDENING_v1.19.md",
    "tests/test_v119_score_assumption_hardening.py",
    "docs/VQ_ADAPTIVE_DISPERSION_v1.20.md",
    "tools/vq_adaptive_dispersion_audit_v1_20.py",
    "tests/test_v120_vq_adaptive_dispersion.py",
    "data/sobol_full_specs_v1.21.yaml",
    "tools/sobol_full_runner_v1_21.py",
    "docs/SOBOL_FULL_RUNNER_v1.21.md",
    "tests/test_v121_sobol_full_runner.py",
    "data/epals_reversible_causes_v1.22.yaml",
    "data/epals_scenario_curriculum_v1.22.yaml",
    "tools/epals_scenario_audit_v1_22.py",
    "docs/EPALS_SCENARIO_ROADMAP_v1.22.md",
    "tests/test_v122_epals_taxonomy.py",
    "data/epals_5h_scenario_pack_v1.22.1.yaml",
    "scenarios/epals_hypoxia_airway_obstruction.yaml",
    "scenarios/epals_hypovolemia_hemorrhagic_shock.yaml",
    "scenarios/epals_acidosis_septic_shock.yaml",
    "scenarios/epals_hyperkalemia_aki.yaml",
    "scenarios/epals_hypothermia_rewarming.yaml",
    "tools/epals_5h_scenario_audit_v1_22_1.py",
    "docs/EPALS_5H_SCENARIO_PACK_v1.22.1.md",
    "tests/test_v1221_epals_5h_scenarios.py",
    "data/epals_5t_scenario_pack_v1.22.2.yaml",
    "scenarios/epals_tension_pneumothorax.yaml",
    "scenarios/epals_cardiac_tamponade.yaml",
    "scenarios/epals_toxicologic_opioid_benzodiazepine.yaml",
    "scenarios/epals_pulmonary_thrombosis_pe.yaml",
    "scenarios/epals_cardiac_thrombosis_myocarditis_low_output.yaml",
    "tools/epals_5t_scenario_audit_v1_22_2.py",
    "docs/EPALS_5T_SCENARIO_PACK_v1.22.2.md",
    "tests/test_v1222_epals_5t_scenarios.py",

    "data/epals_debrief_spec_v1.22.3.yaml",
    "tools/epals_debrief_scaffold_v1_22_3.py",
    "docs/EPALS_DEBRIEF_SCAFFOLD_v1.22.3.md",
    "tests/test_v1223_epals_debrief_scaffold.py",

    "data/airway_interface_spec_v1.23.yaml",
    "modules/respiratory/airway_interface.py",
    "scenarios/airway_unassisted_spontaneous_breathing_v1_23.yaml",
    "tools/airway_interface_audit_v1_23.py",
    "docs/AIRWAY_INTERFACE_BASE_v1.23.md",
    "tests/test_v123_airway_interface.py",

    "data/oxygen_delivery_hfnc_spec_v1.23.1.yaml",
    "scenarios/airway_low_flow_oxygen_v1_23_1.yaml",
    "scenarios/airway_hfnc_bronchiolitis_v1_23_1.yaml",
    "tools/oxygen_delivery_hfnc_audit_v1_23_1.py",
    "docs/OXYGEN_DELIVERY_HFNC_v1.23.1.md",
    "tests/test_v1231_oxygen_delivery_hfnc.py",

    "data/niv_cpap_bipap_spec_v1.23.2.yaml",
    "scenarios/airway_niv_cpap_bronchiolitis_v1_23_2.yaml",
    "scenarios/airway_niv_bipap_hypercapnia_v1_23_2.yaml",
    "tools/niv_cpap_bipap_audit_v1_23_2.py",
    "docs/NIV_CPAP_BIPAP_v1.23.2.md",
    "tests/test_v1232_niv_cpap_bipap.py",
    "data/artificial_airway_ett_spec_v1.23.3.yaml",
    "scenarios/airway_ett_tube_resistance_v1_23_3.yaml",
    "scenarios/airway_ett_partial_obstruction_v1_23_3.yaml",
    "tools/artificial_airway_ett_audit_v1_23_3.py",
    "docs/ARTIFICIAL_AIRWAY_ETT_v1.23.3.md",
    "tests/test_v1233_artificial_airway_ett.py",

    "data/airway_events_v1.24.yaml",
    "core/airway_events.py",
    "scenarios/airway_rsi_hypoxic_child_v1_24.yaml",
    "scenarios/airway_accidental_extubation_picu_v1_24.yaml",
    "tools/airway_event_audit_v1_24.py",
    "docs/AIRWAY_INTUBATION_EVENTS_v1.24.md",
    "tests/test_v124_airway_events.py",

    "data/airway_decision_scenario_pack_v1.25.yaml",
    "scenarios/airway_failed_intubation_cannot_oxygenate_v1_25.yaml",
    "scenarios/airway_extubation_failure_bronchiolitis_v1_25.yaml",
    "scenarios/airway_laryngospasm_post_extubation_v1_25.yaml",
    "scenarios/airway_aspiration_during_rsi_v1_25.yaml",
    "scenarios/airway_opioid_sedation_apnea_v1_25.yaml",
    "scenarios/airway_niv_failure_to_intubation_v1_25.yaml",
    "tools/airway_decision_scenario_audit_v1_25.py",
    "docs/AIRWAY_DECISION_SCENARIOS_v1.25.md",
    "tests/test_v125_airway_decision_scenarios.py",

    "data/emergency_debrief_spec_v1.26.yaml",
    "tools/emergency_debrief_engine_v1_26.py",
    "docs/EMERGENCY_DEBRIEF_ENGINE_v1.26.md",
    "tests/test_v126_emergency_debrief_engine.py",

    "api/__init__.py",
    "api/server.py",
    "api/session.py",
    "api/schemas.py",
    "api/state_profiles.py",
    "api/action_router.py",
    "start_pdt_api.py",
    "docs/API_SERVER_v2.0.md",
    "tests/test_v200_api_server.py",
    "CHANGELOG_v2.0-alpha.md",
    "ui/index.html",
    "ui/styles.css",
    "ui/app.js",
    "ui/canvas_waveforms.js",
    "docs/WEB_MONITOR_v2.1.md",
    "tests/test_v210_web_monitor.py",
    "CHANGELOG_v2.1-alpha.md",
    "api/debrief.py",
    "api/training.py",
    "docs/EMERGENCY_TRAINING_MODE_v2.2.md",
    "tests/test_v220_emergency_training_mode.py",
    "CHANGELOG_v2.2-alpha.md",
    "api/instructor.py",
    "docs/INSTRUCTOR_MODE_v2.3.md",
    "tests/test_v230_instructor_mode.py",
    "CHANGELOG_v2.3-alpha.md",

    "start_pdt_console.py",
    "api/performance.py",
    "tools/gui_performance_audit_v2_4.py",
    "docs/CONSOLE_PERFORMANCE_v2.4.md",
    "tests/test_v240_console_performance.py",
    "CHANGELOG_v2.4-alpha.md",
    "api/session_io.py",
    "tools/session_export_audit_v2_5.py",
    "docs/SESSION_SAVE_LOAD_EXPORT_v2.5.md",
    "tests/test_v250_session_save_load_export.py",
    "CHANGELOG_v2.5-alpha.md",
    "docs/WEB_UI_POLISH_v2.6.md",
    "tests/test_v260_ui_polish_tablet.py",
    "CHANGELOG_v2.6-alpha.md",
    "data/scenario_authoring_templates_v2.7.yaml",
    "api/scenario_authoring.py",
    "tools/scenario_authoring_audit_v2_7.py",
    "docs/SCENARIO_AUTHORING_ASSISTANT_v2.7.md",
    "tests/test_v270_scenario_authoring_assistant.py",
    "CHANGELOG_v2.7-alpha.md",
]

MANDATORY_README_PHRASES = [
    "not for clinical use",
    "not a medical device",
    "not a validated patient-specific digital twin",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail-on-error", action="store_true")
    args = parser.parse_args()

    rows = []
    for rel in REQUIRED:
        rows.append({"check": f"required:{rel}", "status": "PASS" if (ROOT / rel).exists() else "FAIL"})

    version = (ROOT / "VERSION").read_text().strip() if (ROOT / "VERSION").exists() else ""
    rows.append({"check": "version_is_alpha", "status": "PASS" if version.endswith("alpha") else "FAIL", "value": version})

    citation = (ROOT / "CITATION.cff").read_text(errors="ignore") if (ROOT / "CITATION.cff").exists() else ""
    rows.append({"check": "citation_matches_version", "status": "PASS" if f'version: "{version}"' in citation else "FAIL"})

    readme = (ROOT / "README.md").read_text(errors="ignore") if (ROOT / "README.md").exists() else ""
    low_readme = readme.lower()
    for phrase in MANDATORY_README_PHRASES:
        rows.append({"check": f"readme_disclaimer:{phrase}", "status": "PASS" if phrase in low_readme else "FAIL"})

    cache = [p for p in ROOT.rglob("*") if p.name in {"__pycache__", ".pytest_cache"}]
    rows.append({"check": "no_cache_dirs", "status": "PASS" if not cache else "REVIEW", "count": len(cache)})

    summary = {
        "release": version,
        "checks": len(rows),
        "pass": sum(r["status"] == "PASS" for r in rows),
        "review": sum(r["status"] == "REVIEW" for r in rows),
        "fail": sum(r["status"] == "FAIL" for r in rows),
        "rows": rows,
    }
    outdir = ROOT / "outputs" / "validation_pack"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "public_alpha_check_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: summary[k] for k in ["release", "checks", "pass", "review", "fail"]}, indent=2))
    if args.fail_on_error and summary["fail"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
