"""
Recovery Engine — v3.1 Step 4.48
=================================

Educational treatment-response layer used by scenario authors to make correct
rescue actions visibly pull physiology back toward baseline after the critical
event has been triggered.  It does not replace the disease modules; it adds
bounded, delayed recovery perturbations so timing and sequence become teachable.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List

RECOVERY_ENGINE_REVISION = 448

# Conservative, scenario-authoring defaults. Times are simulation seconds and
# therefore remain compatible with the real/virtual timing layer added in 4.45.
PHENOTYPE_RECOVERY_PRESETS: Dict[str, Dict[str, Any]] = {
    "septic_shock": {
        "response_delay_s": 90.0,
        "partial_response_s": 240.0,
        "near_baseline_s": 600.0,
        "targets": {
            "shock_vasoplegia_index": 0.25,
            "shock_decompensation_index": 0.30,
            "organ_perfusion_multiplier": 0.88,
            "lactate_multiplier": 0.78,
        },
    },
    "anaphylaxis": {
        "response_delay_s": 30.0,
        "partial_response_s": 120.0,
        "near_baseline_s": 360.0,
        "targets": {
            "shock_vasoplegia_index": 0.20,
            "bronchospasm_index": 0.25,
            "SaO2_multiplier": 1.04,
            "lactate_multiplier": 0.82,
        },
    },
    "tamponade": {
        "response_delay_s": 45.0,
        "partial_response_s": 150.0,
        "near_baseline_s": 420.0,
        "targets": {
            "shock_obstruction_index": 0.20,
            "shock_low_output_index": 0.25,
            "organ_perfusion_multiplier": 0.92,
        },
    },
    "dka_shock": {
        "response_delay_s": 120.0,
        "partial_response_s": 360.0,
        "near_baseline_s": 900.0,
        "targets": {
            "shock_hypovolemia_index": 0.30,
            "organ_perfusion_multiplier": 0.90,
            "lactate_multiplier": 0.82,
        },
    },
    "bronchiolitis_failure": {
        "response_delay_s": 45.0,
        "partial_response_s": 180.0,
        "near_baseline_s": 480.0,
        "targets": {
            "SaO2_multiplier": 1.05,
            "PaCO2_multiplier": 0.88,
            "respiratory_distress_index": 0.25,
        },
    },
    "generic": {
        "response_delay_s": 60.0,
        "partial_response_s": 240.0,
        "near_baseline_s": 600.0,
        "targets": {
            "shock_decompensation_index": 0.35,
            "organ_perfusion_multiplier": 0.90,
            "lactate_multiplier": 0.82,
        },
    },
}

CORRECTIVE_ACTIONS = {
    # shock / circulation
    "set_norad", "set_adrenaline", "set_dopamine", "set_vasopressin", "set_milrinone",
    "set_balanced_crystalloid", "fluid_bolus", "start_fluid_bolus", "pericardiocentesis",
    "source_control", "set_source_control", "set_antibiotic_started", "set_antibiotic_effect",
    # airway / breathing
    "set_FiO2", "set_PEEP", "start_bag_mask", "bag_mask_ventilation", "intubate", "connect_ventilator",
    "set_salbutamol", "set_nebulized_epinephrine", "set_magnesium",
    # metabolic / neuro
    "set_insulin", "start_insulin", "set_bicarbonate", "hypertonic_saline", "set_hypertonic_saline_3pct",
}


def _mmss(seconds: float) -> str:
    seconds = max(int(round(float(seconds))), 0)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _infer_phenotype(config: Dict[str, Any]) -> str:
    for block_name in ("recovery_engine", "failure_to_rescue"):
        explicit = (config.get(block_name, {}) or {}).get("phenotype")
        if explicit:
            return str(explicit).lower()
    blob = " ".join(str(x).lower() for x in [
        config.get("name", ""), config.get("id", ""), config.get("description", ""), config.get("shock_type", ""),
        config.get("cardiovascular", {}).get("shock_type", "") if isinstance(config.get("cardiovascular"), dict) else "",
    ])
    if "anaphyl" in blob:
        return "anaphylaxis"
    if "tampon" in blob:
        return "tamponade"
    if "dka" in blob or "dehydration" in blob:
        return "dka_shock"
    if "bronchiolitis" in blob or "respiratory_failure" in blob:
        return "bronchiolitis_failure"
    if "sepsis" in blob or "septic" in blob:
        return "septic_shock"
    return "generic"


def recovery_metadata(config: Dict[str, Any]) -> Dict[str, Any]:
    block = dict(config.get("recovery_engine", {}) or {})
    phenotype = _infer_phenotype(config)
    preset = deepcopy(PHENOTYPE_RECOVERY_PRESETS.get(phenotype, PHENOTYPE_RECOVERY_PRESETS["generic"]))
    timing = config.get("scenario_timing", {}) or {}
    trigger_s = float(timing.get("critical_event_trigger_at_s", config.get("critical_event_trigger_at_s", 0.0)))
    response_delay = float(block.get("response_delay_s", preset["response_delay_s"]))
    partial_response = float(block.get("partial_response_s", preset["partial_response_s"]))
    near_baseline = float(block.get("near_baseline_s", preset["near_baseline_s"]))
    targets = dict(preset.get("targets", {}))
    targets.update(block.get("targets", {}) or {})
    return {
        "revision": RECOVERY_ENGINE_REVISION,
        "enabled": bool(block.get("enabled", True)),
        "phenotype": phenotype,
        "trigger_s": trigger_s,
        "response_delay_s": response_delay,
        "partial_response_s": partial_response,
        "near_baseline_s": near_baseline,
        "first_response_abs_s": trigger_s + response_delay,
        "partial_response_abs_s": trigger_s + partial_response,
        "near_baseline_abs_s": trigger_s + near_baseline,
        "first_response_mmss": _mmss(trigger_s + response_delay),
        "partial_response_mmss": _mmss(trigger_s + partial_response),
        "near_baseline_mmss": _mmss(trigger_s + near_baseline),
        "targets": targets,
        "requires_corrective_action": bool(block.get("requires_corrective_action", True)),
        "corrective_actions": list(block.get("corrective_actions", sorted(CORRECTIVE_ACTIONS))),
    }


def with_recovery_engine(config: Dict[str, Any], **overrides: Any) -> Dict[str, Any]:
    cfg = deepcopy(config)
    block = dict(cfg.get("recovery_engine", {}) or {})
    block.update(overrides)
    block.setdefault("enabled", True)
    block.setdefault("requires_corrective_action", True)
    cfg["recovery_engine"] = block
    return cfg


def _scenario_actions(config: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    for key in ("interventions", "timeline", "perturbations"):
        items = config.get(key, []) or []
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    yield item


def detect_first_corrective_action_time(config: Dict[str, Any]) -> float | None:
    meta = recovery_metadata(config)
    allowed = set(str(a) for a in meta["corrective_actions"])
    trigger_s = float(meta["trigger_s"])
    best: float | None = None
    for item in _scenario_actions(config):
        action = str(item.get("action", item.get("key", "")))
        label = str(item.get("label", ""))
        if label.startswith("trigger:"):
            continue
        if action not in allowed:
            continue
        t = float(item.get("t", item.get("time_s", item.get("time", 0.0))))
        if t < trigger_s:
            continue
        if best is None or t < best:
            best = t
    return best


def build_recovery_perturbations(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    meta = recovery_metadata(config)
    if not meta["enabled"]:
        return []
    action_t = detect_first_corrective_action_time(config)
    if meta["requires_corrective_action"] and action_t is None:
        return []
    anchor = float(action_t if action_t is not None else meta["trigger_s"])
    # Response is anchored to actual treatment time, not only scenario onset.
    t1 = anchor + float(meta["response_delay_s"])
    t2 = anchor + float(meta["partial_response_s"])
    t3 = anchor + float(meta["near_baseline_s"])
    targets = dict(meta["targets"])
    items: List[Dict[str, Any]] = []
    for action, target in targets.items():
        if action.endswith("_multiplier"):
            mid = (1.0 + float(target)) / 2.0
            items.append({"t": t1, "action": action, "value": mid, "label": "recovery_engine:first_response"})
            items.append({"t": t2, "action": action, "value": float(target), "label": "recovery_engine:partial_response"})
        else:
            mid = max(float(target), 0.55)
            items.append({"t": t1, "action": action, "value": mid, "label": "recovery_engine:first_response"})
            items.append({"t": t2, "action": action, "value": float(target), "label": "recovery_engine:partial_response"})
            # near-baseline step nudges severe indices down further without forcing zero
            items.append({"t": t3, "action": action, "value": min(float(target), 0.15), "label": "recovery_engine:near_baseline"})
    items.append({"t": t1, "action": "recovery_engine_active", "value": True, "label": "recovery_engine:activated"})
    items.append({"t": t3, "action": "recovery_phase", "value": "near_baseline", "label": "recovery_engine:near_baseline"})
    return sorted(items, key=lambda x: float(x["t"]))
