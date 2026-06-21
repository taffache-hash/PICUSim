"""Action router for PDT v2.0 API.

Actions are deliberately small and explicit.  The backend never exposes arbitrary
code execution to the UI; it either sets a Bus field or applies a known airway
event from the event library.
"""
from __future__ import annotations

from typing import Any, Dict

from core.airway_events import airway_event_to_perturbation, load_airway_event_spec
from core.cardiac_arrest_events import (
    apply_cardiac_rhythm_event,
    apply_cpr_control,
    apply_defibrillation,
    apply_post_rosc_care,
    apply_rcp_drug_bolus,
)


ACTION_KEY_MAP = {
    # Ventilator / oxygen controls
    "set_fio2": "FiO2",
    "set_FiO2": "FiO2",
    "set_peep": "PEEP",
    "set_PEEP": "PEEP",
    "set_rr": "RR",
    "set_RR": "RR",
    "set_paw": "Paw",
    "set_Paw": "Paw",
    "set_hr": "HR",
    "set_HR": "HR",

    # Cardiovascular / vasoactive drugs
    "set_norad": "norad_mcg_kg_min",
    "set_adrenaline": "adrenaline_mcg_kg_min",
    "set_dopamine": "dopamine_mcg_kg_min",
    "set_vasopressin": "vasopressin_mU_kg_min",
    "set_milrinone": "milrinone_mcg_kg_min",

    # Sedation / analgesia / paralysis drugs
    "set_ketamine": "ketamine_mg_kg_h",
    "set_fentanyl": "fentanyl_mcg_kg_h",
    "set_remifentanil": "remifentanil_mcg_kg_min",
    "set_morphine": "morphine_mcg_kg_h",
    "set_midazolam": "midazolam_mcg_kg_h",
    "set_propofol": "propofol_mg_kg_h",
    "set_dexmedetomidine": "dexmedetomidine_mcg_kg_h",
    "set_clonidine": "clonidine_mcg_kg_h",
    "set_rocuronium": "rocuronium_mg_kg_h",

    # Bronchodilator / respiratory pharmacology controls
    "set_salbutamol": "salbutamol_mcg_kg_min",
    "set_ipratropium": "ipratropium_mcg_kg_h",
    "set_magnesium": "magnesium_mg_kg_h",
    "set_nebulized_epinephrine": "nebulized_epinephrine_mcg_kg_min",
    "set_ino_ppm": "ino_ppm",

    # Endocrine / metabolic / renal / antimicrobial controls
    "set_hydrocortisone": "hydrocortisone_mg_kg_h",
    "set_dexamethasone": "dexamethasone_mcg_kg_h",
    "set_insulin": "insulin_UI_h",
    "set_furosemide": "furosemide_mg_kg",
    "set_furosemide_infusion": "furosemide_mg_kg_h",
    "set_furosemide_rate": "furosemide_mg_kg_h",
    "set_vancomycin": "vancomycin_mg_kg_h",
    "set_piperacillin": "piperacillin_mg_kg_h",
    "set_piptazo": "piperacillin_mg_kg_h",

    # Fluids / crystalloids
    "set_crystalloid_rate": "crystalloid_rate_mL_h",
    "set_crystalloid_type": "crystalloid_type",
}


def _coerce_value(value: Any) -> Any:
    if isinstance(value, str):
        v = value.strip()
        if v.lower() == "true":
            return True
        if v.lower() == "false":
            return False
        try:
            return float(v)
        except ValueError:
            return value
    return value


def _normalize_fio2_value(value: Any) -> float:
    """Normalize FiO2 commands accepted as fractions (0.21-1.0) or percent (21-100)."""
    coerced = _coerce_value(value)
    try:
        fio2 = float(coerced)
    except Exception as exc:
        raise ValueError("FiO2 command requires a numeric value") from exc
    if fio2 > 1.5:
        fio2 = fio2 / 100.0
    return max(0.21, min(fio2, 1.0))


def _bus_get(bus, key: str, default: Any = None) -> Any:
    return bus.get(key) if hasattr(bus.state, key) else default


def _apply_fio2_command(bus, value: Any) -> Dict[str, Any]:
    """Apply a FiO2 command to the correct oxygen-control channel.

    v3.2 public-polish: FiO2 is the commanded set-point, while
    FiO2_delivered is the effective oxygen after interface/leak.  Older code
    changed only FiO2; HFNC, low-flow oxygen and NIV then reverted on the next
    AirwayInterface step because they read HFNC_FiO2_set, oxygen_FiO2_set or
    NIV_FiO2_set instead.
    """
    fio2 = _normalize_fio2_value(value)
    iface = str(_bus_get(bus, "airway_interface", "")).upper()
    oxygen_iface = str(_bus_get(bus, "oxygen_interface", "")).upper()
    vent_mode = str(_bus_get(bus, "vent_mode", "")).upper()
    connected = bool(_bus_get(bus, "ventilator_connected", False))
    intubated = bool(_bus_get(bus, "intubated", False))

    bus.set("FiO2", fio2)

    if iface == "HFNC" or oxygen_iface == "HFNC":
        bus.set("HFNC_FiO2_set", fio2)
        bus.set("oxygen_FiO2_set", fio2)
        # Keep the immediate response useful; AirwayInterface recomputes exact
        # delivered FiO2 after leak/flow on the next engine step.
        bus.set("FiO2_delivered", max(0.21, min(float(_bus_get(bus, "FiO2_delivered", fio2)), fio2)))
        target = "HFNC_FiO2_set"
    elif iface in ("NIV_CPAP", "NIV_BIPAP") or oxygen_iface == "NIV":
        bus.set("NIV_FiO2_set", fio2)
        bus.set("oxygen_FiO2_set", fio2)
        target = "NIV_FiO2_set"
    elif connected or intubated or iface in ("ETT", "TRACHEOSTOMY") or vent_mode not in ("NONE", "UNASSISTED", ""):
        bus.set("oxygen_FiO2_set", fio2)
        bus.set("HFNC_FiO2_set", fio2)
        bus.set("FiO2_delivered", fio2)
        target = "ventilator_FiO2"
    else:
        # Spontaneous/unassisted oxygen: the same control acts as the oxygen
        # source setting.  Do not leave oxygen_FiO2_set at room air or the next
        # step will collapse back toward 0.21.
        bus.set("oxygen_FiO2_set", fio2)
        bus.set("HFNC_FiO2_set", fio2)
        if fio2 <= 0.22:
            bus.set("oxygen_interface", "ROOM_AIR")
            bus.set("oxygen_flow_L_min", 0.0)
        else:
            if oxygen_iface in ("", "ROOM_AIR", "VENTILATOR"):
                bus.set("oxygen_interface", "LOW_FLOW_OXYGEN")
            if float(_bus_get(bus, "oxygen_flow_L_min", 0.0) or 0.0) <= 0.0:
                bus.set("oxygen_flow_L_min", 1.0)
        target = "oxygen_FiO2_set"

    return {"status": "applied", "action": "set_fio2", "key": "FiO2", "target": target, "value": bus.get("FiO2")}


def apply_action(bus, action: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = dict(payload or {})
    action = str(action)

    if action in ("set_fio2", "set_FiO2"):
        return _apply_fio2_command(bus, payload.get("value"))

    if action in ("set_rr", "set_RR"):
        value = _coerce_value(payload.get("value"))
        bus.set("RR", value)
        bus.set("ventilator_RR_set", value)
        return {"status": "applied", "action": action, "key": "ventilator_RR_set", "value": bus.get("ventilator_RR_set")}

    if action in ACTION_KEY_MAP:
        key = ACTION_KEY_MAP[action]
        value = payload.get("value")
        bus.set(key, _coerce_value(value))
        return {"status": "applied", "action": action, "key": key, "value": bus.get(key)}

    if action == "set_variable":
        key = str(payload.get("key"))
        if not key or key == "None":
            raise ValueError("set_variable requires payload.key")
        if not hasattr(bus.state, key):
            raise ValueError(f"Unknown Bus field: {key}")
        value = _coerce_value(payload.get("value"))
        bus.set(key, value)
        return {"status": "applied", "action": action, "key": key, "value": bus.get(key)}

    if action == "airway_event":
        name = str(payload.get("name") or payload.get("event") or "")
        severity = str(payload.get("severity", "moderate"))
        if not name:
            raise ValueError("airway_event requires payload.name")
        item = dict(payload)
        item.update({"name": name, "severity": severity, "t": float(getattr(bus.state, "t", 0.0))})
        p = airway_event_to_perturbation(item, load_airway_event_spec())
        p.apply(bus)
        return {"status": "applied", "action": action, "event": name, "severity": severity}

    if action == "cardiac_rhythm_event":
        return apply_cardiac_rhythm_event(bus, payload)

    if action == "cpr_control":
        return apply_cpr_control(bus, payload)

    if action == "defibrillation":
        return apply_defibrillation(bus, payload)

    if action == "rcp_drug_bolus":
        return apply_rcp_drug_bolus(bus, payload)

    if action == "post_rosc_care":
        return apply_post_rosc_care(bus, payload)

    if action == "set_airway_interface":
        interface = str(payload.get("interface", "UNASSISTED")).upper()
        bus.set("airway_interface", interface)
        bus.set("intubated", interface in ("ETT", "TRACHEOSTOMY"))
        bus.set("ventilator_connected", interface in ("ETT", "TRACHEOSTOMY", "NIV_CPAP", "NIV_BIPAP"))
        if interface in ("UNASSISTED", "LOW_FLOW_OXYGEN", "SIMPLE_MASK", "HFNC"):
            bus.set("vent_mode", "NONE")
            bus.set("Paw", 0.0)
            bus.set("PEEP", 0.0)
        return {"status": "applied", "action": action, "interface": interface}

    raise ValueError(f"Unknown action: {action}")

