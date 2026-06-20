"""Airway intubation/extubation event system v1.24.

This module provides reusable educational airway events that can be placed in
scenario YAML under ``airway_events``.  The events are bounded proxy state
changes; they are not procedural guidance and are not patient-specific
prediction.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Iterable, List
import yaml

from .engine import Perturbation
from .bus import PhysiologicalBus

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AIRWAY_EVENT_SPEC = ROOT / "data" / "airway_events_v1.24.yaml"


AIRWAY_SEVERITY_ALIASES = {
    # UI quick buttons historically sent "moderate" for every airway event.
    # Successful intubation only has routine/emergency severities in the spec,
    # so map the generic quick-action severity to the clinically intended event.
    "perform_intubation": {
        "moderate": "emergency",
        "severe": "emergency",
        "mild": "routine",
        "adequate": "routine",
    },
    "start_bag_mask_ventilation": {
        "moderate": "adequate",
        "mild": "adequate",
        "severe": "difficult",
        "emergency": "difficult",
    },
}


def resolve_airway_event_severity(name: str, severity: str, severities: Dict[str, Any]) -> str:
    """Resolve generic UI severity labels to valid event-specific severities."""
    name = str(name)
    severity = str(severity)
    if severity in severities:
        return severity
    alias = AIRWAY_SEVERITY_ALIASES.get(name, {}).get(severity)
    if alias in severities:
        return alias
    raise ValueError(f"Unknown severity '{severity}' for airway event '{name}'")


def load_airway_event_spec(path: str | Path | None = None) -> Dict[str, Any]:
    with open(Path(path) if path else DEFAULT_AIRWAY_EVENT_SPEC, "r") as f:
        return yaml.safe_load(f)


def _clamp(x: float, lo: float, hi: float) -> float:
    return float(max(lo, min(hi, x)))


def _get(bus: PhysiologicalBus, key: str, default: Any = None) -> Any:
    return bus.get(key) if hasattr(bus.state, key) else default


def _set_if_present(bus: PhysiologicalBus, key: str, value: Any) -> None:
    if hasattr(bus.state, key):
        bus.set(key, value)


def _add(bus: PhysiologicalBus, key: str, delta: float, lo: float, hi: float) -> None:
    if hasattr(bus.state, key):
        bus.set(key, _clamp(float(bus.get(key)) + float(delta), lo, hi))


def _mul(bus: PhysiologicalBus, key: str, factor: float, lo: float, hi: float) -> None:
    if hasattr(bus.state, key):
        bus.set(key, _clamp(float(bus.get(key)) * float(factor), lo, hi))


def _event_header(bus: PhysiologicalBus, t_event: float, event_type: str, label: str, status: str) -> None:
    bus.update({
        "airway_event_revision": 1240,
        "airway_event_active": True,
        "airway_event_type": event_type,
        "airway_event_label": label,
        "airway_event_status": status,
        "airway_event_time_s": float(t_event),
    })


def _apply_common_effects(bus: PhysiologicalBus, effects: Dict[str, Any]) -> None:
    for key in ("SaO2_sub", "PaCO2_add", "PaO2_sub", "lactate_add", "K_add"):
        if key not in effects:
            continue
        if key == "SaO2_sub": _add(bus, "SaO2", -float(effects[key]), 0.25, 1.0)
        if key == "PaCO2_add": _add(bus, "PaCO2", float(effects[key]), 10.0, 180.0)
        if key == "PaO2_sub": _add(bus, "PaO2", -float(effects[key]), 15.0, 600.0)
        if key == "lactate_add": _add(bus, "lactate", float(effects[key]), 0.2, 30.0)
        if key == "K_add": _add(bus, "K_mmol_L", float(effects[key]), 1.5, 9.0)
    if "R_rs_add" in effects:
        _add(bus, "R_rs", float(effects["R_rs_add"]), 1.0, 160.0)
    if "airway_obstruction_add" in effects:
        _add(bus, "airway_obstruction_index", float(effects["airway_obstruction_add"]), 0.0, 1.0)
    if "upper_airway_obstruction_add" in effects:
        _add(bus, "upper_airway_obstruction_score", float(effects["upper_airway_obstruction_add"]), 0.0, 1.0)
    if "aspiration_risk_add" in effects:
        _add(bus, "aspiration_risk", float(effects["aspiration_risk_add"]), 0.0, 1.0)
    if "hypoxia_burden_add" in effects:
        _add(bus, "airway_event_hypoxia_burden", float(effects["hypoxia_burden_add"]), 0.0, 1.0)
    if "sed_resp_factor" in effects:
        _mul(bus, "sed_resp_mod", float(effects["sed_resp_factor"]), 0.02, 1.5)
    if "NMB_set" in effects:
        _set_if_present(bus, "drug_NMB_frac", _clamp(float(effects["NMB_set"]), 0.0, 1.0))
    if "MAP_factor" in effects:
        _mul(bus, "MAP", float(effects["MAP_factor"]), 10.0, 160.0)
    if "HR_add" in effects:
        _add(bus, "HR", float(effects["HR_add"]), 30.0, 260.0)


def _apply_event(bus: PhysiologicalBus, event_name: str, severity: str, effects: Dict[str, Any], t_event: float, label: str) -> None:
    event_name = event_name.lower()
    _event_header(bus, t_event, event_name, label, str(effects.get("status", "event")))
    _apply_common_effects(bus, effects)

    if event_name == "perform_intubation":
        bus.update({
            "airway_interface": "ETT",
            "intubated": True,
            "ventilator_connected": True,
            "airway_pressure_delivery_enabled": True,
            "unassisted_breathing_active": False,
            "spontaneous_airway_mode": False,
            "manual_ventilation_active": False,
            "bag_mask_ventilation_active": False,
            "bag_mask_quality": 0.0,
            "oxygen_interface": "VENTILATOR",
            "vent_mode": str(effects.get("vent_mode", "PCV")).upper(),
            "PEEP": float(effects.get("PEEP", 5.0)),
            "FiO2": float(effects.get("FiO2", 1.0)),
            "oxygen_FiO2_set": float(effects.get("FiO2", 1.0)),
            "FiO2_delivered": float(effects.get("FiO2", 1.0)),
            "Pinsp_cmH2O": float(effects.get("Pinsp_cmH2O", 16.0)),
            "PS_cmH2O": float(effects.get("PS_cmH2O", 10.0)),
            "tube_internal_diameter_mm": float(effects.get("tube_internal_diameter_mm", _get(bus, "tube_internal_diameter_mm", 5.0))),
            "tube_length_cm": float(effects.get("tube_length_cm", _get(bus, "tube_length_cm", 16.0))),
            "tube_obstruction_score": float(effects.get("tube_obstruction_score", 0.0)),
            "cuff_leak_fraction": float(effects.get("cuff_leak_fraction", 0.05)),
            "ETT_position_score": float(effects.get("ETT_position_score", 0.95)),
            "airway_rescue_state": "secured_ETT",
            "airway_event_status": "success",
            "intubation_success_time_s": float(t_event),
            "intubation_attempt_count": int(_get(bus, "intubation_attempt_count", 0)) + 1,
            "airway_protection_score": 0.85,
            "aspiration_risk": min(float(_get(bus, "aspiration_risk", 0.0)), 0.35),
        })
        return

    if event_name == "failed_intubation_attempt":
        bus.update({
            "airway_event_status": "failed",
            "airway_rescue_state": "failed_attempt",
            "intubation_attempt_count": int(_get(bus, "intubation_attempt_count", 0)) + 1,
            "failed_intubation_count": int(_get(bus, "failed_intubation_count", 0)) + 1,
            "intubated": False,
            "airway_pressure_delivery_enabled": False,
            "airway_protection_score": _clamp(float(_get(bus, "airway_protection_score", 1.0)) - 0.25, 0.0, 1.0),
        })
        return

    if event_name == "start_bag_mask_ventilation":
        quality = _clamp(float(effects.get("bag_mask_quality", 0.70)), 0.0, 1.0)
        leak = _clamp(1.0 - quality, 0.05, 0.85)
        epap = float(effects.get("EPAP", 4.0))
        ipap = float(effects.get("IPAP", 18.0))
        bus.update({
            "airway_interface": "NIV_BIPAP",
            "NIV_mode": "BIPAP",
            "intubated": False,
            "ventilator_connected": True,
            "airway_pressure_delivery_enabled": True,
            "manual_ventilation_active": True,
            "bag_mask_ventilation_active": True,
            "bag_mask_quality": quality,
            "airway_rescue_state": "rescued_BVM",
            "airway_event_status": "rescue",
            "vent_mode": "PSV",
            "NIV_EPAP_cmH2O": epap,
            "NIV_IPAP_cmH2O": ipap,
            "NIV_pressure_support_cmH2O": max(ipap - epap, 0.0),
            "NIV_FiO2_set": float(effects.get("FiO2", 1.0)),
            "NIV_leak_fraction": leak,
            "mask_leak_fraction": leak,
            "FiO2": float(effects.get("FiO2", 1.0)),
            "oxygen_FiO2_set": float(effects.get("FiO2", 1.0)),
            "airway_protection_score": _clamp(float(_get(bus, "airway_protection_score", 1.0)) - 0.10, 0.0, 1.0),
        })
        return

    if event_name in ("accidental_extubation", "planned_extubation"):
        planned = event_name == "planned_extubation"
        interface = str(effects.get("post_extubation_interface", "HFNC" if planned else "UNASSISTED")).upper()
        bus.update({
            "airway_interface": interface,
            "intubated": False,
            "ventilator_connected": False,
            "airway_pressure_delivery_enabled": False,
            "unassisted_breathing_active": True,
            "spontaneous_airway_mode": True,
            "manual_ventilation_active": False,
            "bag_mask_ventilation_active": False,
            "vent_mode": "NONE",
            "PEEP": 0.0,
            "Paw": 0.0,
            "Paw_current": 0.0,
            "oxygen_interface": interface if interface in ("HFNC", "LOW_FLOW_OXYGEN", "SIMPLE_MASK") else "ROOM_AIR",
            "HFNC_flow_L_min": float(effects.get("HFNC_flow_L_min", 1.5 * max(float(_get(bus, "weight_kg", 20.0)), 1.0))) if interface == "HFNC" else 0.0,
            "HFNC_FiO2_set": float(effects.get("FiO2", 0.60 if planned else 0.21)),
            "FiO2": float(effects.get("FiO2", 0.60 if planned else 0.21)),
            "extubation_time_s": float(t_event),
            "airway_event_status": "success" if planned else "unplanned",
            "airway_rescue_state": "extubated" if planned else "at_risk",
            "airway_protection_score": float(effects.get("airway_protection_score", 0.70 if planned else 0.35)),
        })
        return

    if event_name == "laryngospasm":
        bus.update({
            "airway_rescue_state": "upper_airway_obstruction",
            "laryngospasm_score": _clamp(float(_get(bus, "laryngospasm_score", 0.0)) + float(effects.get("laryngospasm_add", 0.55)), 0.0, 1.0),
            "upper_airway_obstruction_score": _clamp(float(_get(bus, "upper_airway_obstruction_score", 0.0)) + float(effects.get("upper_airway_obstruction_add", 0.45)), 0.0, 1.0),
        })
        return

    if event_name == "aspiration_event":
        bus.update({
            "airway_rescue_state": "aspiration_risk",
            "aspiration_risk": _clamp(float(_get(bus, "aspiration_risk", 0.0)) + float(effects.get("aspiration_risk_add", 0.45)), 0.0, 1.0),
            "airway_protection_score": _clamp(float(_get(bus, "airway_protection_score", 1.0)) - float(effects.get("airway_protection_sub", 0.25)), 0.0, 1.0),
        })
        return

    if event_name == "airway_obstruction_event":
        if bool(_get(bus, "intubated", False)):
            _add(bus, "tube_obstruction_score", float(effects.get("tube_obstruction_add", 0.35)), 0.0, 1.0)
        else:
            _add(bus, "upper_airway_obstruction_score", float(effects.get("upper_airway_obstruction_add", 0.35)), 0.0, 1.0)
        bus.set("airway_rescue_state", "obstructed_airway")
        return


def airway_event_to_perturbation(item: Dict[str, Any], spec: Dict[str, Any] | None = None) -> Perturbation:
    spec = spec or load_airway_event_spec()
    name = str(item.get("name") or item.get("event"))
    severity = str(item.get("severity", "moderate"))
    t_event = float(item.get("t", item.get("time", 0.0)))
    events = spec.get("events", {})
    if name not in events:
        raise ValueError(f"Unknown airway event: {name}")
    severities = events[name].get("severities", {})
    severity = resolve_airway_event_severity(name, severity, severities)
    effects = dict(severities[severity])
    # Item-level overrides allow scenario-specific tube size or FiO2 without creating new severities.
    effects.update({k: v for k, v in item.items() if k not in {"t", "time", "name", "event", "severity", "label"}})
    label = str(item.get("label", f"airway_event:{name}:{severity}"))
    return Perturbation(t=t_event, callback=lambda bus, ev=name, sev=severity, eff=effects, tt=t_event, lab=label: _apply_event(bus, ev, sev, eff, tt, lab), label=label)


def build_airway_event_perturbations(items: Iterable[Dict[str, Any]], spec_path: str | Path | None = None) -> List[Perturbation]:
    spec = load_airway_event_spec(spec_path)
    return sorted([airway_event_to_perturbation(item, spec) for item in items], key=lambda p: p.t)


class AirwayEventLibrary:
    def __init__(self, spec_path: str | Path | None = None):
        self.spec_path = spec_path
        self.spec = load_airway_event_spec(spec_path)
        self.events = self.spec.get("events", {})

    def names(self) -> List[str]:
        return sorted(self.events.keys())

    def severities(self, name: str) -> List[str]:
        return sorted(self.events[name].get("severities", {}).keys())

    def to_perturbation(self, t: float, name: str, severity: str = "moderate", label: str | None = None) -> Perturbation:
        item: Dict[str, Any] = {"t": t, "name": name, "severity": severity}
        if label:
            item["label"] = label
        return airway_event_to_perturbation(item, self.spec)
