"""Scenario authoring assistant for PDT v2.7.

Creates conservative YAML drafts from curated templates, validates them against the
existing scenario loader, and optionally saves them as loadable scenarios.
"""
from __future__ import annotations

import copy
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from core import ScenarioLoader

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "data" / "scenario_authoring_templates_v2.7.yaml"
SCENARIO_DIR = ROOT / "scenarios"
AUTHORING_DIR = ROOT / "outputs" / "authored_scenarios_v2.7"

BASE_OUTPUTS = [
    "SaO2", "PaO2", "PaCO2", "HR", "MAP", "Paw", "PEEP", "FiO2", "FiO2_delivered",
    "RR_total", "Vt", "lactate", "airway_interface", "oxygen_interface", "vent_mode",
    "airway_event_type", "airway_rescue_state", "intubation_attempt_count",
    "failed_intubation_count", "intubation_success_time_s", "manual_ventilation_active",
    "bag_mask_ventilation_active",
]


def _slug(text: str, fallback: str = "authored_scenario") -> str:
    text = (text or fallback).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    text = re.sub(r"_+", "_", text)
    return text[:70] or fallback


def _deep_update(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in (src or {}).items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_update(dst[k], v)
        else:
            dst[k] = v
    return dst


def load_authoring_templates() -> Dict[str, Any]:
    data = yaml.safe_load(TEMPLATE_PATH.read_text()) or {}
    templates = data.get("templates") or []
    by_id = {str(t.get("id")): t for t in templates if t.get("id")}
    return {"release": data.get("release", "v2.7-alpha"), "schema": data.get("schema"), "templates": templates, "by_id": by_id}


def list_templates() -> List[Dict[str, Any]]:
    data = load_authoring_templates()
    out = []
    for t in data["templates"]:
        d = t.get("defaults", {})
        out.append({
            "id": t.get("id"),
            "label": t.get("label"),
            "category": t.get("category"),
            "default_focus": t.get("default_focus", []),
            "default_age_y": d.get("age_y"),
            "default_weight_kg": d.get("weight_kg"),
            "default_duration_s": d.get("duration_s"),
        })
    return out


def _apply_severity(scenario: Dict[str, Any], severity: str) -> None:
    severity = severity or "moderate"
    resp = scenario.setdefault("respiratory", {})
    cv = scenario.setdefault("cardiovascular", {})
    metab = scenario.setdefault("metabolism", {})
    if severity == "mild":
        resp["SaO2"] = max(float(resp.get("SaO2", 0.95)), 0.93)
        resp["PaCO2"] = min(float(resp.get("PaCO2", 42)), 50.0)
        cv["HR"] = max(80.0, float(cv.get("HR", 120)) - 10)
        cv["MAP"] = max(float(cv.get("MAP", 60)), 58.0)
        metab["lactate"] = min(float(metab.get("lactate", 1.5)), 2.5)
    elif severity == "severe":
        resp["SaO2"] = min(float(resp.get("SaO2", 0.90)), 0.86)
        resp["PaCO2"] = max(float(resp.get("PaCO2", 50)), 62.0)
        resp["PaO2"] = min(float(resp.get("PaO2", 65)), 54.0)
        cv["HR"] = max(float(cv.get("HR", 130)), 155.0)
        cv["MAP"] = min(float(cv.get("MAP", 60)), 52.0)
        metab["lactate"] = max(float(metab.get("lactate", 2.0)), 3.2)


def build_scenario_draft(req: Any) -> Dict[str, Any]:
    templates = load_authoring_templates()["by_id"]
    if req.template_id not in templates:
        raise ValueError(f"Unknown template_id: {req.template_id}")
    template = templates[req.template_id]
    defaults = copy.deepcopy(template.get("defaults") or {})
    custom = copy.deepcopy(getattr(req, "custom_parameters", {}) or {})
    _deep_update(defaults, custom)

    name = _slug(req.title)
    patient = {
        "profile": "child_20kg" if float(req.weight_kg or defaults.get("weight_kg", 20)) >= 15 else "infant_7kg",
        "age_y": req.age_y if req.age_y is not None else defaults.get("age_y", 5),
        "weight_kg": req.weight_kg if req.weight_kg is not None else defaults.get("weight_kg", 20),
        "sex": req.sex or defaults.get("sex", "M"),
        "diagnosis": req.diagnosis or defaults.get("diagnosis", name),
    }
    focus = req.focus if req.focus is not None else template.get("default_focus", [])
    questions = req.debrief_questions or [
        "What was the first sign of deterioration?",
        "Which intervention changed the physiology most clearly?",
        "Was escalation delayed or timely?",
    ]
    scenario: Dict[str, Any] = {
        "name": name,
        "version": "v2.7-alpha",
        "category": req.category or template.get("category", "authored"),
        "description": req.description or "Educational authored scenario. Not for clinical use.",
        "clinical_narrative": req.description or "Educational authored scenario. Not for clinical use.",
        "patient": patient,
        "respiratory": defaults.get("respiratory", {}),
        "cardiovascular": defaults.get("cardiovascular", {}),
        "metabolism": defaults.get("metabolism", {}),
        "perturbations": defaults.get("perturbations", []),
        "outputs": list(dict.fromkeys(BASE_OUTPUTS)),
        "simulation_time_s": req.duration_s if req.duration_s is not None else defaults.get("duration_s", 300),
        "decision_focus": focus,
        "debrief_questions": questions,
        "limitations": [
            "Authored educational scenario for simulation training only.",
            "Not calibrated for patient-specific prediction or clinical decision support.",
            "Intervention events are simplified proxies for physiology reversal, not treatment protocols.",
        ],
    }
    for optional in ["airway_interface", "airway", "ventilator", "airway_events", "events", "drugs"]:
        if optional in defaults:
            scenario[optional] = defaults[optional]
    _apply_severity(scenario, req.severity)

    yaml_text = yaml.safe_dump(scenario, sort_keys=False, allow_unicode=True, width=110)
    validation = validate_yaml_text(yaml_text)
    warnings = validation.get("warnings", [])
    if req.template_id == "generic_picu":
        warnings.append("Generic template has limited emergency debrief value unless events are added.")
    return {
        "schema": "pdt-scenario-draft-v2.7",
        "scenario_id": name,
        "suggested_filename": f"user_{name}_v2_7.yaml",
        "scenario": scenario,
        "yaml_text": yaml_text,
        "validation": validation,
        "warnings": warnings,
    }


def validate_yaml_text(yaml_text: str) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []
    try:
        scenario = yaml.safe_load(yaml_text) or {}
    except Exception as exc:
        return {"status": "fail", "errors": [f"YAML parse error: {exc}"], "warnings": []}
    if not isinstance(scenario, dict):
        return {"status": "fail", "errors": ["YAML root must be a mapping"], "warnings": []}
    required = ["name", "patient", "respiratory", "cardiovascular", "metabolism", "outputs", "simulation_time_s"]
    for key in required:
        if key not in scenario:
            errors.append(f"Missing required key: {key}")
    patient = scenario.get("patient") or {}
    if not patient.get("weight_kg"):
        errors.append("patient.weight_kg is required")
    if not patient.get("age_y") and patient.get("age_y") != 0:
        warnings.append("patient.age_y is missing")
    sim_time = float(scenario.get("simulation_time_s", 0) or 0)
    if sim_time < 60 or sim_time > 7200:
        errors.append("simulation_time_s must be between 60 and 7200")
    resp = scenario.get("respiratory") or {}
    sao2 = float(resp.get("SaO2", 0.95) or 0.95)
    if not 0.30 <= sao2 <= 1.0:
        errors.append("respiratory.SaO2 must be 0.30-1.00")
    fio2 = float(resp.get("FiO2", 0.21) or 0.21)
    if not 0.21 <= fio2 <= 1.0:
        errors.append("respiratory.FiO2 must be 0.21-1.00")
    if len(str(scenario.get("name", ""))) > 80:
        warnings.append("Scenario name is long; consider shortening it")
    if not scenario.get("debrief_questions"):
        warnings.append("No debrief_questions configured")
    if not scenario.get("decision_focus"):
        warnings.append("No decision_focus configured")
    if not errors:
        try:
            AUTHORING_DIR.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile("w", suffix=".yaml", dir=str(AUTHORING_DIR), delete=False) as fh:
                fh.write(yaml_text)
                tmp = Path(fh.name)
            loader = ScenarioLoader.from_yaml(str(tmp))
            loader.build_bus()
            loader.build_perturbations()
            tmp.unlink(missing_ok=True)
        except Exception as exc:
            errors.append(f"Scenario loader validation failed: {exc}")
    return {"status": "pass" if not errors else "fail", "errors": errors, "warnings": warnings}


def validate_payload(req: Any) -> Dict[str, Any]:
    if getattr(req, "scenario", None) is not None:
        yaml_text = yaml.safe_dump(req.scenario, sort_keys=False, allow_unicode=True, width=110)
    elif getattr(req, "yaml_text", None):
        yaml_text = req.yaml_text
    else:
        raise ValueError("Provide yaml_text or scenario")
    return {"validation": validate_yaml_text(yaml_text), "yaml_text": yaml_text}


def save_authored_scenario(yaml_text: str, filename: str | None = None, overwrite: bool = False, publish_to_scenarios: bool = True) -> Dict[str, Any]:
    validation = validate_yaml_text(yaml_text)
    if validation["status"] != "pass":
        raise ValueError("Invalid scenario: " + "; ".join(validation.get("errors", [])))
    scenario = yaml.safe_load(yaml_text) or {}
    base = filename or f"user_{_slug(str(scenario.get('name', 'authored_scenario')))}_v2_7.yaml"
    base = Path(base).name
    if not base.endswith(".yaml"):
        base += ".yaml"
    if not re.match(r"^[A-Za-z0-9_.-]+\.yaml$", base):
        raise ValueError("filename may contain only letters, numbers, dot, underscore and hyphen")
    target_dir = SCENARIO_DIR if publish_to_scenarios else AUTHORING_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / base
    if path.exists() and not overwrite:
        raise FileExistsError(f"Scenario already exists: {path.relative_to(ROOT)}")
    path.write_text(yaml_text)
    return {
        "status": "saved",
        "scenario_id": path.stem,
        "path": str(path.relative_to(ROOT)),
        "published": bool(publish_to_scenarios),
        "validation": validation,
    }


def list_authored_scenarios() -> List[Dict[str, Any]]:
    rows = []
    for folder, published in [(SCENARIO_DIR, True), (AUTHORING_DIR, False)]:
        if not folder.exists():
            continue
        for path in sorted(folder.glob("user_*_v2_7.yaml")):
            try:
                data = yaml.safe_load(path.read_text()) or {}
                rows.append({
                    "scenario_id": path.stem,
                    "path": str(path.relative_to(ROOT)),
                    "name": data.get("name", path.stem),
                    "description": data.get("description", ""),
                    "published": published,
                })
            except Exception as exc:
                rows.append({"scenario_id": path.stem, "path": str(path.relative_to(ROOT)), "error": str(exc), "published": published})
    return rows
