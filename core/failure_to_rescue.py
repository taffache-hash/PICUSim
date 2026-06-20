"""
Failure-to-rescue clock — v3.1 Step 4.46
=========================================

Adds an explicit educational timing layer after the critical-event trigger:

* golden-window / critical-window metadata;
* reversibility threshold metadata;
* point-of-no-return metadata;
* optional deterministic deterioration perturbations after the window expires.

This is a teaching scaffold, not a clinical prediction model.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

FAILURE_TO_RESCUE_REVISION = 446

DEFAULT_WINDOWS_BY_PHENOTYPE: Dict[str, Dict[str, float]] = {
    "septic_shock": {"critical_window_s": 480.0, "reversibility_threshold_s": 720.0, "point_of_no_return_s": 900.0},
    "anaphylaxis": {"critical_window_s": 180.0, "reversibility_threshold_s": 300.0, "point_of_no_return_s": 420.0},
    "tamponade": {"critical_window_s": 300.0, "reversibility_threshold_s": 480.0, "point_of_no_return_s": 600.0},
    "tension_pneumothorax": {"critical_window_s": 240.0, "reversibility_threshold_s": 420.0, "point_of_no_return_s": 540.0},
    "bronchiolitis_failure": {"critical_window_s": 600.0, "reversibility_threshold_s": 900.0, "point_of_no_return_s": 1200.0},
    "hyperkalemia": {"critical_window_s": 300.0, "reversibility_threshold_s": 480.0, "point_of_no_return_s": 660.0},
    "status_epilepticus": {"critical_window_s": 300.0, "reversibility_threshold_s": 600.0, "point_of_no_return_s": 900.0},
    "tbi_icp_crisis": {"critical_window_s": 420.0, "reversibility_threshold_s": 660.0, "point_of_no_return_s": 900.0},
    "dka_shock": {"critical_window_s": 600.0, "reversibility_threshold_s": 900.0, "point_of_no_return_s": 1200.0},
    "generic": {"critical_window_s": 300.0, "reversibility_threshold_s": 480.0, "point_of_no_return_s": 600.0},
}


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _lower_blob(config: Dict[str, Any]) -> str:
    parts = [str(config.get("name", "")), str(config.get("description", ""))]
    for key in ("shock", "scenario_timing", "critical_event_baseline"):
        parts.append(str(config.get(key, "")))
    return " ".join(parts).lower()


def infer_failure_phenotype(config: Dict[str, Any]) -> str:
    """Infer a coarse teaching phenotype from scenario metadata."""
    explicit = (config.get("failure_to_rescue", {}) or {}).get("phenotype")
    if explicit:
        return str(explicit)
    blob = _lower_blob(config)
    if "anaphyl" in blob:
        return "anaphylaxis"
    if "tamponade" in blob:
        return "tamponade"
    if "pneumothorax" in blob or "tension" in blob:
        return "tension_pneumothorax"
    if "bronchiolitis" in blob or "respiratory_failure" in blob:
        return "bronchiolitis_failure"
    if "hyperkal" in blob:
        return "hyperkalemia"
    if "seizure" in blob or "status_epilepticus" in blob:
        return "status_epilepticus"
    if "tbi" in blob or "icp" in blob:
        return "tbi_icp_crisis"
    if "dka" in blob:
        return "dka_shock"
    if "sepsis" in blob or "septic" in blob or "distributive" in blob:
        return "septic_shock"
    return "generic"


def failure_to_rescue_metadata(config: Dict[str, Any]) -> Dict[str, Any]:
    """Return timing metadata for rescue-window display and debrief."""
    from .scenario_timing import format_mmss, scenario_timing_metadata

    timing = scenario_timing_metadata(config)
    block = dict(config.get("failure_to_rescue", {}) or {})
    phenotype = infer_failure_phenotype(config)
    defaults = DEFAULT_WINDOWS_BY_PHENOTYPE.get(phenotype, DEFAULT_WINDOWS_BY_PHENOTYPE["generic"])
    trigger_s = _float(timing.get("critical_event_trigger_at_s", 60.0), 60.0)
    critical_window_s = _float(block.get("critical_window_s", defaults["critical_window_s"]), defaults["critical_window_s"])
    reversibility_threshold_s = _float(block.get("reversibility_threshold_s", defaults["reversibility_threshold_s"]), defaults["reversibility_threshold_s"])
    point_of_no_return_s = _float(block.get("point_of_no_return_s", defaults["point_of_no_return_s"]), defaults["point_of_no_return_s"])
    return {
        "revision": FAILURE_TO_RESCUE_REVISION,
        "phenotype": phenotype,
        "trigger_s": trigger_s,
        "critical_window_s": critical_window_s,
        "critical_window_end_s": trigger_s + critical_window_s,
        "reversibility_threshold_s": reversibility_threshold_s,
        "reversibility_threshold_abs_s": trigger_s + reversibility_threshold_s,
        "point_of_no_return_s": point_of_no_return_s,
        "point_of_no_return_abs_s": trigger_s + point_of_no_return_s,
        "critical_window_mmss": format_mmss(critical_window_s),
        "critical_window_end_mmss": format_mmss(trigger_s + critical_window_s),
        "reversibility_threshold_mmss": format_mmss(trigger_s + reversibility_threshold_s),
        "point_of_no_return_mmss": format_mmss(trigger_s + point_of_no_return_s),
        "display_timer_before_trigger": bool(block.get("display_timer_before_trigger", True)),
        "escalation_enabled": bool(block.get("escalation_enabled", True)),
        "teaching_note": block.get("teaching_note", "Treat before the critical window closes; late rescue becomes progressively harder."),
    }


def with_failure_to_rescue(config: Dict[str, Any], **overrides: Any) -> Dict[str, Any]:
    """Return a config copy with explicit failure_to_rescue block."""
    cfg = deepcopy(config)
    meta = failure_to_rescue_metadata({**cfg, "failure_to_rescue": {**(cfg.get("failure_to_rescue", {}) or {}), **overrides}})
    block = dict(cfg.get("failure_to_rescue", {}) or {})
    block.update(overrides)
    block.setdefault("phenotype", meta["phenotype"])
    block.setdefault("critical_window_s", meta["critical_window_s"])
    block.setdefault("reversibility_threshold_s", meta["reversibility_threshold_s"])
    block.setdefault("point_of_no_return_s", meta["point_of_no_return_s"])
    block.setdefault("display_timer_before_trigger", True)
    block.setdefault("escalation_enabled", True)
    block.setdefault("revision", FAILURE_TO_RESCUE_REVISION)
    cfg["failure_to_rescue"] = block
    return cfg


def build_failure_escalation_perturbations(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Build generic bus perturbations that make non-rescue progressively worse.

    These are deliberately conservative and deterministic. They give the sim a
    visible educational clock without pretending to be calibrated patient data.
    """
    meta = failure_to_rescue_metadata(config)
    if not meta["escalation_enabled"]:
        return []
    t1 = meta["critical_window_end_s"]
    t2 = meta["reversibility_threshold_abs_s"]
    t3 = meta["point_of_no_return_abs_s"]
    phenotype = meta["phenotype"]
    base: List[Dict[str, Any]] = [
        {"t": t1, "action": "lactate_multiplier", "value": 1.25, "label": "failure_to_rescue:critical_window_closed"},
        {"t": t2, "action": "lactate_multiplier", "value": 1.60, "label": "failure_to_rescue:late_reversibility_threshold"},
        {"t": t3, "action": "organ_perfusion_multiplier", "value": 0.55, "label": "failure_to_rescue:point_of_no_return"},
    ]
    if phenotype in {"septic_shock", "anaphylaxis"}:
        base += [
            {"t": t1, "action": "shock_vasoplegia_index", "value": 0.75, "label": "failure_to_rescue:vasoplegia_progression"},
            {"t": t2, "action": "shock_vasoplegia_index", "value": 0.90, "label": "failure_to_rescue:severe_vasoplegia"},
        ]
    if phenotype in {"tamponade", "tension_pneumothorax"}:
        base += [
            {"t": t1, "action": "shock_obstruction_index", "value": 0.80, "label": "failure_to_rescue:obstruction_progression"},
            {"t": t2, "action": "CO_multiplier", "value": 0.60, "label": "failure_to_rescue:low_output_progression"},
        ]
    if phenotype in {"bronchiolitis_failure", "tbi_icp_crisis", "status_epilepticus"}:
        base += [
            {"t": t1, "action": "SaO2_multiplier", "value": 0.92, "label": "failure_to_rescue:oxygenation_penalty"},
            {"t": t2, "action": "PaCO2_multiplier", "value": 1.25, "label": "failure_to_rescue:ventilatory_penalty"},
        ]
    return base
