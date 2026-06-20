"""Educational cardiac rhythm/arrest state events.

This module provides bounded, qualitative state transitions for rhythm and
cardiac-arrest training.  It is not a clinical decision engine.
"""
from __future__ import annotations

from typing import Any, Dict

from .engine import Perturbation


SHOCKABLE_RHYTHMS = {"vf", "pulseless_vt"}
NONSHOCKABLE_ARREST_RHYTHMS = {"pea", "asystole"}
PULSED_UNSTABLE_RHYTHMS = {"vt_with_pulse", "svt_unstable", "bradycardia_unstable"}
SUPPORTED_RHYTHMS = {
    "sinus",
    "bradycardia",
    "bradycardia_unstable",
    "svt",
    "svt_unstable",
    "vt_with_pulse",
    "pulseless_vt",
    "vf",
    "pea",
    "asystole",
}

EVENT_TO_RHYTHM = {
    "induce_pea": "pea",
    "induce_vf": "vf",
    "induce_pulseless_vt": "pulseless_vt",
    "induce_asystole": "asystole",
    "induce_vt_with_pulse": "vt_with_pulse",
    "induce_svt_unstable": "svt_unstable",
    "induce_bradycardia_unstable": "bradycardia_unstable",
    "respiratory_arrest": "bradycardia_unstable",
    "cardiac_arrest": "pea",
    "rosc": "sinus",
}


def _clamp(x: Any, lo: float, hi: float, default: float) -> float:
    try:
        v = float(x)
    except Exception:
        v = float(default)
    return max(lo, min(hi, v))


def rhythm_metadata(rhythm: str) -> Dict[str, Any]:
    rhythm = str(rhythm or "sinus").lower()
    if rhythm not in SUPPORTED_RHYTHMS:
        raise ValueError(f"Unknown cardiac rhythm: {rhythm}")
    shockable = rhythm in SHOCKABLE_RHYTHMS
    arrest = rhythm in SHOCKABLE_RHYTHMS or rhythm in NONSHOCKABLE_ARREST_RHYTHMS
    has_pulse = not arrest
    category = "shockable" if shockable else ("nonshockable" if arrest else "pulsed")
    return {
        "cardiac_rhythm": rhythm,
        "shockable_rhythm": shockable,
        "cardiac_arrest_active": arrest,
        "has_pulse": has_pulse,
        "rhythm_category": category,
    }


def apply_cardiac_rhythm_event(bus, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = dict(payload or {})
    event = str(payload.get("name") or payload.get("event") or payload.get("rhythm") or "").lower()
    rhythm = str(payload.get("rhythm") or EVENT_TO_RHYTHM.get(event, event) or "sinus").lower()
    cause = str(payload.get("cause") or payload.get("etiology") or "manual")
    quality = _clamp(payload.get("cpr_quality", getattr(bus.state, "CPR_quality", 0.0)), 0.0, 1.0, 0.0)
    t = float(getattr(bus.state, "t", 0.0))
    was_arrest = bool(getattr(bus.state, "cardiac_arrest_active", False))
    meta = rhythm_metadata(rhythm)

    updates: Dict[str, Any] = {
        "cardiac_event_revision": 100,
        "cardiac_event_active": True,
        "cardiac_event_type": event or f"set_{rhythm}",
        "cardiac_event_time_s": t,
        "cardiac_arrest_cause": cause,
        "cardiac_rhythm": meta["cardiac_rhythm"],
        "shockable_rhythm": meta["shockable_rhythm"],
        "cardiac_arrest_active": meta["cardiac_arrest_active"],
        "has_pulse": meta["has_pulse"],
        "rhythm_category": meta["rhythm_category"],
        "ROSC": rhythm == "sinus" and was_arrest,
        "post_arrest_phase": rhythm == "sinus" and was_arrest,
    }

    if rhythm == "sinus":
        updates.update({
            "has_pulse": True,
            "cardiac_arrest_active": False,
            "shockable_rhythm": False,
            "CPR_active": False,
            "CPR_quality": 0.0,
            "compression_fraction": 0.0,
            "cardiac_arrest_time_s": -1.0,
            "rosc_time_s": t,
            "MAP": max(float(getattr(bus.state, "MAP", 65.0)), 55.0),
            "SBP": max(float(getattr(bus.state, "SBP", 90.0)), 80.0),
            "DBP": max(float(getattr(bus.state, "DBP", 50.0)), 45.0),
            "SAP": max(float(getattr(bus.state, "SAP", 90.0)), 80.0),
            "DAP": max(float(getattr(bus.state, "DAP", 50.0)), 45.0),
            "arterial_pulse_pressure": max(float(getattr(bus.state, "arterial_pulse_pressure", 40.0)), 25.0),
            "CO": max(float(getattr(bus.state, "CO", 3.0)), 2.5),
            "SV": max(float(getattr(bus.state, "SV", 25.0)), 25.0),
            "EtCO2": max(float(getattr(bus.state, "EtCO2", 25.0)), 30.0),
            "EtCO2_proxy": max(float(getattr(bus.state, "EtCO2_proxy", 25.0)), 30.0),
            "etco2_perfusion_factor": max(float(getattr(bus.state, "etco2_perfusion_factor", 0.5)), 0.75),
            "renal_hypoperfusion_index": max(float(getattr(bus.state, "renal_hypoperfusion_index", 0.0)) - 0.15, 0.0),
        })
        if was_arrest:
            updates.update({
                "reperfusion_injury_risk": max(float(getattr(bus.state, "reperfusion_injury_risk", 0.0)), 0.35),
                "post_rosc_care_status": "needed",
                "post_rosc_care_time_s": -1.0,
                "post_rosc_oxygenation_optimized": False,
                "post_rosc_ventilation_optimized": False,
                "post_rosc_perfusion_support_active": False,
                "post_rosc_acidosis_burden": max(float(getattr(bus.state, "post_rosc_acidosis_burden", 0.0)), 0.55),
                "post_rosc_myocardial_dysfunction_risk": max(float(getattr(bus.state, "post_rosc_myocardial_dysfunction_risk", 0.0)), 0.45),
                "lactate": max(float(getattr(bus.state, "lactate", 1.0)), 3.0),
                "pH_a": min(float(getattr(bus.state, "pH_a", 7.40)), 7.30),
            })
        else:
            updates.update({
                "rosc_time_s": -1.0,
                "post_rosc_care_status": "none",
                "post_rosc_care_time_s": -1.0,
                "post_rosc_oxygenation_optimized": False,
                "post_rosc_ventilation_optimized": False,
                "post_rosc_perfusion_support_active": False,
            })
    elif meta["cardiac_arrest_active"]:
        cpr_map = 18.0 + 22.0 * quality
        updates.update({
            "cardiac_arrest_time_s": t if float(getattr(bus.state, "cardiac_arrest_time_s", -1.0)) < 0 else getattr(bus.state, "cardiac_arrest_time_s"),
            "CPR_active": bool(payload.get("cpr_active", getattr(bus.state, "CPR_active", False))),
            "CPR_quality": quality,
            "compression_fraction": _clamp(payload.get("compression_fraction", getattr(bus.state, "compression_fraction", 0.0)), 0.0, 1.0, 0.0),
            "MAP": cpr_map if bool(payload.get("cpr_active", getattr(bus.state, "CPR_active", False))) else 5.0,
            "SBP": cpr_map + 8.0 if quality > 0 else 8.0,
            "DBP": max(cpr_map - 8.0, 2.0) if quality > 0 else 2.0,
            "SAP": cpr_map + 8.0 if quality > 0 else 8.0,
            "DAP": max(cpr_map - 8.0, 2.0) if quality > 0 else 2.0,
            "arterial_pulse_pressure": 16.0 if quality > 0 else 0.0,
            "CO": 0.25 + 1.15 * quality if quality > 0 else 0.05,
            "SV": 3.0 + 10.0 * quality if quality > 0 else 1.0,
            "EtCO2": 8.0 + 14.0 * quality if quality > 0 else 4.0,
            "EtCO2_proxy": 8.0 + 14.0 * quality if quality > 0 else 4.0,
            "etco2_perfusion_factor": 0.12 + 0.38 * quality if quality > 0 else 0.08,
            "SaO2": min(float(getattr(bus.state, "SaO2", 0.97)), 0.88),
            "pH_a": min(float(getattr(bus.state, "pH_a", 7.40)), 7.24),
            "lactate": max(float(getattr(bus.state, "lactate", 1.0)), 4.0),
            "renal_hypoperfusion_index": max(float(getattr(bus.state, "renal_hypoperfusion_index", 0.0)), 0.65),
        })
    elif rhythm in PULSED_UNSTABLE_RHYTHMS:
        updates.update({
            "cardiac_arrest_time_s": -1.0,
            "MAP": min(float(getattr(bus.state, "MAP", 65.0)), 48.0),
            "CO": min(float(getattr(bus.state, "CO", 3.5)), 2.0),
            "arterial_pulse_pressure": min(float(getattr(bus.state, "arterial_pulse_pressure", 35.0)), 18.0),
        })

    bus.update(updates)
    return {
        "status": "applied",
        "action": "cardiac_rhythm_event",
        "event": updates["cardiac_event_type"],
        "rhythm": rhythm,
        "shockable": updates["shockable_rhythm"],
        "cardiac_arrest_active": updates["cardiac_arrest_active"],
        "has_pulse": updates["has_pulse"],
    }


def apply_cpr_control(bus, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = dict(payload or {})
    active = bool(payload.get("active", payload.get("CPR_active", True)))
    quality = _clamp(payload.get("quality", payload.get("CPR_quality", getattr(bus.state, "CPR_quality", 0.75))), 0.0, 1.0, 0.75)
    fraction = _clamp(payload.get("compression_fraction", 0.85 if active else 0.0), 0.0, 1.0, 0.85 if active else 0.0)
    arrest = bool(getattr(bus.state, "cardiac_arrest_active", False))

    updates: Dict[str, Any] = {
        "CPR_active": active,
        "CPR_quality": quality if active else 0.0,
        "compression_fraction": fraction if active else 0.0,
    }
    if arrest:
        if active:
            cpr_map = 18.0 + 22.0 * quality
            updates.update({
                "MAP": cpr_map,
                "SBP": cpr_map + 8.0,
                "DBP": max(cpr_map - 8.0, 2.0),
                "SAP": cpr_map + 8.0,
                "DAP": max(cpr_map - 8.0, 2.0),
                "arterial_pulse_pressure": 16.0,
                "CO": 0.25 + 1.15 * quality,
                "SV": 3.0 + 10.0 * quality,
                "EtCO2": 8.0 + 14.0 * quality,
                "EtCO2_proxy": 8.0 + 14.0 * quality,
                "etco2_perfusion_factor": 0.12 + 0.38 * quality,
            })
        else:
            updates.update({
                "MAP": 5.0,
                "SBP": 8.0,
                "DBP": 2.0,
                "SAP": 8.0,
                "DAP": 2.0,
                "arterial_pulse_pressure": 0.0,
                "CO": 0.05,
                "SV": 1.0,
                "EtCO2": 4.0,
                "EtCO2_proxy": 4.0,
                "etco2_perfusion_factor": 0.08,
            })

    bus.update(updates)
    return {
        "status": "applied",
        "action": "cpr_control",
        "active": active,
        "quality": updates["CPR_quality"],
        "compression_fraction": updates["compression_fraction"],
        "cardiac_arrest_active": arrest,
    }


def apply_defibrillation(bus, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = dict(payload or {})
    mode = str(payload.get("mode") or payload.get("shock_mode") or "defibrillation").lower()
    synchronized = bool(payload.get("synchronized", mode in {"sync", "synchronized", "cardioversion"}))
    energy_j = _clamp(payload.get("energy_J", payload.get("joules", 4.0)), 0.0, 360.0, 4.0)
    rhythm = str(getattr(bus.state, "cardiac_rhythm", "sinus")).lower()
    arrest = bool(getattr(bus.state, "cardiac_arrest_active", False))
    shockable = rhythm in SHOCKABLE_RHYTHMS
    pulsed_unstable = rhythm in PULSED_UNSTABLE_RHYTHMS
    t = float(getattr(bus.state, "t", 0.0))
    weight = max(float(getattr(bus.state, "weight_kg", 20.0)), 1.0)
    energy_per_kg = energy_j / weight

    appropriate = (shockable and not synchronized) or (pulsed_unstable and synchronized)
    effective = False
    converted_rhythm = rhythm
    result = "not_indicated"

    updates: Dict[str, Any] = {
        "last_shock_energy_J": energy_j,
        "last_shock_time_s": t,
        "last_shock_mode": "synchronized" if synchronized else "defibrillation",
        "last_shock_appropriate": appropriate,
        "last_shock_effective": False,
    }
    if synchronized:
        updates["synchronized_cardioversion_count"] = int(getattr(bus.state, "synchronized_cardioversion_count", 0)) + 1
    else:
        updates["defibrillation_attempt_count"] = int(getattr(bus.state, "defibrillation_attempt_count", 0)) + 1

    if shockable and synchronized:
        result = "sync_not_for_pulseless_shockable"
    elif arrest and not shockable:
        result = "not_shockable"
    elif shockable and not synchronized:
        if energy_per_kg >= 2.0:
            effective = True
            converted_rhythm = "sinus"
            result = "rosc"
        else:
            result = "energy_too_low"
    elif pulsed_unstable and synchronized:
        if energy_per_kg >= 0.5:
            effective = True
            converted_rhythm = "sinus"
            result = "converted"
        else:
            result = "energy_too_low"

    updates["last_shock_effective"] = effective
    updates["last_shock_result"] = result
    bus.update(updates)

    if effective and converted_rhythm == "sinus":
        apply_cardiac_rhythm_event(bus, {"name": "rosc" if arrest else "set_sinus", "rhythm": "sinus", "cause": "shock"})

    return {
        "status": "applied",
        "action": "defibrillation",
        "mode": updates["last_shock_mode"],
        "energy_J": energy_j,
        "energy_J_kg": round(energy_per_kg, 2),
        "rhythm": rhythm,
        "appropriate": appropriate,
        "effective": effective,
        "result": result,
    }


def apply_rcp_drug_bolus(bus, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = dict(payload or {})
    drug = str(payload.get("drug") or payload.get("name") or "").lower()
    rhythm = str(getattr(bus.state, "cardiac_rhythm", "sinus")).lower()
    arrest = bool(getattr(bus.state, "cardiac_arrest_active", False))
    shockable = rhythm in SHOCKABLE_RHYTHMS
    brady = rhythm in {"bradycardia", "bradycardia_unstable"}
    if drug in {"adrenaline", "epinephrine", "epi"}:
        key = "epinephrine_bolus_count"
        result = "arrest_vasopressor" if arrest else "not_arrest_context"
        appropriate = arrest
    elif drug == "amiodarone":
        key = "amiodarone_bolus_count"
        result = "shockable_antiarrhythmic" if shockable else "not_shockable_context"
        appropriate = shockable
    elif drug == "atropine":
        key = "atropine_bolus_count"
        result = "bradycardia_context" if brady else "not_primary_arrest_drug"
        appropriate = brady
    else:
        raise ValueError(f"Unknown RCP drug bolus: {drug}")

    count = int(getattr(bus.state, key, 0)) + 1
    updates: Dict[str, Any] = {
        key: count,
        "last_rcp_drug": drug,
        "last_rcp_drug_result": result,
        "last_rcp_drug_appropriate": appropriate,
        "last_rcp_drug_time_s": float(getattr(bus.state, "t", 0.0)),
    }
    if drug in {"adrenaline", "epinephrine", "epi"} and arrest:
        updates.update({
            "SVR": max(float(getattr(bus.state, "SVR", 1200.0)), 1500.0),
            "MAP": max(float(getattr(bus.state, "MAP", 5.0)), 18.0),
            "renal_hypoperfusion_index": max(float(getattr(bus.state, "renal_hypoperfusion_index", 0.0)), 0.65),
        })
    if drug == "atropine" and brady:
        updates.update({
            "HR": max(float(getattr(bus.state, "HR", 60.0)), 90.0),
            "MAP": max(float(getattr(bus.state, "MAP", 45.0)), 55.0),
        })
    bus.update(updates)
    return {
        "status": "applied",
        "action": "rcp_drug_bolus",
        "drug": drug,
        "count": count,
        "appropriate": appropriate,
        "result": result,
        "rhythm": rhythm,
    }


def apply_post_rosc_care(bus, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = dict(payload or {})
    post_rosc = bool(getattr(bus.state, "post_arrest_phase", False)) or bool(getattr(bus.state, "ROSC", False))
    has_pulse = bool(getattr(bus.state, "has_pulse", True))
    if not post_rosc or not has_pulse:
        bus.update({
            "post_rosc_care_status": "none",
            "post_rosc_care_time_s": float(getattr(bus.state, "t", 0.0)),
        })
        return {
            "status": "applied",
            "action": "post_rosc_care",
            "appropriate": False,
            "result": "not_post_rosc_context",
        }

    fio2_target = _clamp(payload.get("fio2_target", payload.get("FiO2", 0.60)), 0.21, 1.0, 0.60)
    map_target = _clamp(payload.get("map_target", payload.get("MAP", 55.0)), 35.0, 90.0, 55.0)
    paco2_target = _clamp(payload.get("paco2_target", payload.get("PaCO2", 45.0)), 30.0, 65.0, 45.0)
    current_paco2 = float(getattr(bus.state, "PaCO2", paco2_target))
    current_lactate = float(getattr(bus.state, "lactate", 3.5))
    current_ph = float(getattr(bus.state, "pH_a", 7.25))

    updates = {
        "post_rosc_care_status": "active",
        "post_rosc_care_time_s": float(getattr(bus.state, "t", 0.0)),
        "post_rosc_oxygenation_optimized": True,
        "post_rosc_ventilation_optimized": True,
        "post_rosc_perfusion_support_active": True,
        "FiO2": fio2_target,
        "FiO2_delivered": fio2_target,
        "SaO2": max(min(float(getattr(bus.state, "SaO2", 0.94)), 0.99), 0.94),
        "PaO2": max(float(getattr(bus.state, "PaO2", 70.0)), 75.0),
        "PaCO2": current_paco2 + (paco2_target - current_paco2) * 0.45,
        "EtCO2": max(float(getattr(bus.state, "EtCO2", 25.0)), 30.0),
        "EtCO2_proxy": max(float(getattr(bus.state, "EtCO2_proxy", 25.0)), 30.0),
        "MAP": max(float(getattr(bus.state, "MAP", 45.0)), map_target),
        "SBP": max(float(getattr(bus.state, "SBP", 75.0)), map_target + 25.0),
        "DBP": max(float(getattr(bus.state, "DBP", 40.0)), map_target - 10.0),
        "SAP": max(float(getattr(bus.state, "SAP", 75.0)), map_target + 25.0),
        "DAP": max(float(getattr(bus.state, "DAP", 40.0)), map_target - 10.0),
        "CO": max(float(getattr(bus.state, "CO", 2.0)), 2.6),
        "DO2": max(float(getattr(bus.state, "DO2", 250.0)), 360.0),
        "lactate": max(current_lactate * 0.92, 2.5),
        "pH_a": min(max(current_ph + 0.03, 7.20), 7.36),
        "post_rosc_acidosis_burden": max(float(getattr(bus.state, "post_rosc_acidosis_burden", 0.55)) - 0.18, 0.25),
        "post_rosc_myocardial_dysfunction_risk": max(float(getattr(bus.state, "post_rosc_myocardial_dysfunction_risk", 0.45)), 0.35),
        "renal_hypoperfusion_index": max(float(getattr(bus.state, "renal_hypoperfusion_index", 0.50)) - 0.10, 0.25),
        "reperfusion_injury_risk": max(float(getattr(bus.state, "reperfusion_injury_risk", 0.35)), 0.35),
    }
    bus.update(updates)
    return {
        "status": "applied",
        "action": "post_rosc_care",
        "appropriate": True,
        "result": "post_rosc_stabilization_started",
        "fio2_target": fio2_target,
        "map_target": map_target,
        "paco2_target": paco2_target,
    }


def cardiac_event_to_perturbation(item: Dict[str, Any]) -> Perturbation:
    payload = dict(item)
    t_event = float(payload.pop("t", payload.pop("time", 0.0)))
    label = str(payload.pop("label", f"cardiac_event:{payload.get('name') or payload.get('rhythm')}"))
    return Perturbation(
        t=t_event,
        callback=lambda bus, p=payload: apply_cardiac_rhythm_event(bus, p),
        label=label,
    )


def build_cardiac_event_perturbations(items) -> list[Perturbation]:
    return sorted([cardiac_event_to_perturbation(item) for item in items], key=lambda p: p.t)
