"""
Scenario Timing and Critical-Event Trigger — v3.1 Step 4.45
===========================================================

Adds explicit real-time/virtual-time metadata and a stable-start wrapper for
scenario teaching. The clinical/educational idea is simple:

1. the learner first sees a stable child at baseline;
2. the critical event is armed but not applied immediately;
3. the critical event timeline is shifted to a visible trigger time;
4. UI/CLI layers can report nominal real duration before the run starts.

This module intentionally does not claim clinical timing fidelity. It only makes
scenario timing transparent and reproducible.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

import yaml

SCENARIO_TIMING_REVISION = 445
DEFAULT_TRIGGER_AT_S = 60.0
DEFAULT_REAL_TIME_SPEED = 1.0
_TIMELINE_KEYS = ("perturbations", "events", "airway_events", "cardiac_events")
_DYNAMIC_BASELINE_KEYS = (
    "respiratory", "cardiovascular", "metabolism", "renal", "hepatic",
    "shock", "sepsis", "infection", "neuro", "neurology", "airway",
    "airway_interface", "drugs", "analgosedation", "hematology", "acidbase",
    "nutrition", "endocrine", "coagulation",
)


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def format_mmss(seconds: float) -> str:
    seconds = max(0, int(round(float(seconds))))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def scenario_timing_metadata(config: Dict[str, Any]) -> Dict[str, Any]:
    """Return explicit timing metadata for display before a scenario starts."""
    timing = dict(config.get("scenario_timing", {}) or {})
    virtual_duration_s = _float(config.get("simulation_time_s", timing.get("virtual_duration_s", 300.0)), 300.0)
    real_time_speed = max(_float(timing.get("real_time_speed", DEFAULT_REAL_TIME_SPEED), DEFAULT_REAL_TIME_SPEED), 1e-6)
    real_duration_s = _float(timing.get("real_duration_s", virtual_duration_s / real_time_speed), virtual_duration_s / real_time_speed)
    trigger_at_s = _float(timing.get("critical_event_trigger_at_s", timing.get("trigger_at_s", DEFAULT_TRIGGER_AT_S)), DEFAULT_TRIGGER_AT_S)
    stable_start_s = _float(timing.get("stable_start_s", trigger_at_s), trigger_at_s)
    failure_block = config.get("failure_to_rescue", {}) or {}
    return {
        "revision": SCENARIO_TIMING_REVISION,
        "virtual_duration_s": virtual_duration_s,
        "real_duration_s_at_1x": virtual_duration_s,
        "real_duration_s": real_duration_s,
        "real_time_speed": real_time_speed,
        "critical_event_trigger_at_s": trigger_at_s,
        "stable_start_s": stable_start_s,
        "virtual_duration_mmss": format_mmss(virtual_duration_s),
        "real_duration_mmss": format_mmss(real_duration_s),
        "critical_event_trigger_mmss": format_mmss(trigger_at_s),
        "mode": timing.get("mode", "stable_start_manual_trigger"),
        "failure_to_rescue_enabled": bool(failure_block.get("escalation_enabled", False)),
    }


def with_timing_metadata(config: Dict[str, Any], *, trigger_at_s: float = DEFAULT_TRIGGER_AT_S, real_time_speed: float = DEFAULT_REAL_TIME_SPEED) -> Dict[str, Any]:
    """Return a copy with explicit scenario_timing block filled in."""
    cfg = deepcopy(config)
    timing = dict(cfg.get("scenario_timing", {}) or {})
    timing.setdefault("mode", "stable_start_manual_trigger")
    timing.setdefault("stable_start_required", True)
    timing.setdefault("critical_event_trigger", "manual_button_or_configured_offset")
    timing.setdefault("critical_event_trigger_at_s", float(trigger_at_s))
    timing.setdefault("real_time_speed", float(real_time_speed))
    timing.setdefault("real_duration_s", float(cfg.get("simulation_time_s", 300.0)) / max(float(real_time_speed), 1e-6))
    timing.setdefault("display_duration_before_start", True)
    cfg["scenario_timing"] = timing
    if "failure_to_rescue" not in cfg:
        try:
            from .failure_to_rescue import with_failure_to_rescue
            cfg = with_failure_to_rescue(cfg)
        except Exception:
            pass
    return cfg


def shift_timeline_items(items: Iterable[Dict[str, Any]], offset_s: float) -> list[Dict[str, Any]]:
    shifted: list[Dict[str, Any]] = []
    for item in items or []:
        new_item = deepcopy(item)
        t_key = "t" if "t" in new_item else ("time" if "time" in new_item else "t")
        new_item[t_key] = _float(new_item.get(t_key, 0.0), 0.0) + float(offset_s)
        shifted.append(new_item)
    return shifted


def shift_critical_timelines(config: Dict[str, Any], trigger_at_s: float) -> Dict[str, Any]:
    """Shift all critical timelines so they occur after the visible trigger."""
    cfg = deepcopy(config)
    for key in _TIMELINE_KEYS:
        if key in cfg:
            cfg[key] = shift_timeline_items(cfg.get(key, []), trigger_at_s)
    cfg = with_timing_metadata(cfg, trigger_at_s=trigger_at_s)
    return cfg


def load_yaml(path: str | Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML scenario must be a mapping: {path}")
    return data


def make_stable_start_config(config: Dict[str, Any], healthy_template: Dict[str, Any] | None = None, *, trigger_at_s: float = DEFAULT_TRIGGER_AT_S) -> Dict[str, Any]:
    """
    Wrap a scenario so the initial state is a stable child and the original
    critical physiology/timeline is moved to the trigger point.

    The original disease blocks are preserved under critical_event_baseline so
    Codex/UI can display what will be activated, but they are removed from the
    initial bus construction.
    """
    original = deepcopy(config)
    base = deepcopy(healthy_template) if healthy_template else deepcopy(config)
    if healthy_template:
        # Keep the original patient identity/weight when present, but use healthy
        # physiologic blocks for the initial visible baseline.
        base["patient"] = deepcopy(original.get("patient", base.get("patient", {})))
    base["name"] = str(original.get("name", "scenario")) + "__stable_start"
    base["description"] = (
        "Stable-start wrapper: the child starts from a healthy/stable baseline; "
        "the critical event is applied only after the trigger. Original: "
        + str(original.get("description", ""))
    )
    base["simulation_time_s"] = float(original.get("simulation_time_s", base.get("simulation_time_s", 300.0)))
    base["outputs"] = deepcopy(original.get("outputs", base.get("outputs", [])))

    critical_baseline = {k: deepcopy(original[k]) for k in _DYNAMIC_BASELINE_KEYS if k in original}
    base["critical_event_baseline"] = critical_baseline
    base["critical_event_source_name"] = original.get("name", "unnamed_scenario")

    # Convert original disease baseline blocks to trigger-time assignments for
    # common scalar fields. This makes the critical deterioration visible after
    # the stable period without silently starting sick.
    generated: list[Dict[str, Any]] = []
    action_prefix = {
        "respiratory": "set_",
        "cardiovascular": "set_",
        "metabolism": "set_",
        "drugs": "set_",
        "shock": "shock_",
    }
    for section in ("respiratory", "cardiovascular", "metabolism", "drugs"):
        values = original.get(section, {}) or {}
        if isinstance(values, dict):
            for key, value in values.items():
                if isinstance(value, (int, float)):
                    generated.append({"t": 0.0, "action": f"set_{key}", "value": float(value), "label": f"trigger:{section}.{key}"})
    # Shock fields are not all direct action names; use direct bus keys.
    shock = original.get("shock", {}) or {}
    if isinstance(shock, dict):
        for src, dst in {
            "severity": "shock_severity", "vasoplegia_index": "shock_vasoplegia_index",
            "hypovolemia_index": "shock_hypovolemia_index", "low_output_index": "shock_low_output_index",
            "obstruction_index": "shock_obstruction_index", "tamponade_index": "shock_obstruction_index",
        }.items():
            if src in shock and isinstance(shock[src], (int, float)):
                generated.append({"t": 0.0, "action": dst, "value": float(shock[src]), "label": f"trigger:shock.{src}"})

    merged_perturbations = generated + deepcopy(original.get("perturbations", []) or [])
    base["perturbations"] = shift_timeline_items(merged_perturbations, trigger_at_s)
    for key in ("events", "airway_events", "cardiac_events"):
        if key in original:
            base[key] = shift_timeline_items(original.get(key, []), trigger_at_s)
        elif key in base:
            base[key] = []

    # Remove dynamic disease blocks from initial stable baseline when no explicit
    # healthy template was supplied.
    if not healthy_template:
        for key in _DYNAMIC_BASELINE_KEYS:
            if key in base and key not in ("patient",):
                base.pop(key, None)

    base = with_timing_metadata(base, trigger_at_s=trigger_at_s)
    base["scenario_timing"]["stable_start_applied"] = True
    return base


def stable_start_from_paths(scenario_path: str | Path, healthy_template_path: str | Path, *, trigger_at_s: float = DEFAULT_TRIGGER_AT_S) -> Dict[str, Any]:
    return make_stable_start_config(load_yaml(scenario_path), load_yaml(healthy_template_path), trigger_at_s=trigger_at_s)
