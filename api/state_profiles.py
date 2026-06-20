
"""Compact API state profiles for PDT v2.4.

The GUI must not stream the full Bus at high frequency.  v2.4 adds
bedside_fast, waveform_fast and training profiles to reduce payload size
and keep emergency training views responsive.
"""
from __future__ import annotations

from typing import Any, Dict


def _get(state: Any, key: str, default: Any = None) -> Any:
    return getattr(state, key, default)


def _num(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _round(x: Any, digits: int = 1, default: float = 0.0) -> float:
    return round(_num(x, default), digits)


BEDSIDE_KEYS = [
    "t", "HR", "MAP", "SBP", "DBP", "SAP", "DAP", "arterial_pulse_pressure",
    "SaO2", "PaO2", "PaCO2", "EtCO2", "EtCO2_proxy", "etco2_pa_gradient", "pH_a", "lactate",
    "RR_total", "RR", "Vt", "MV_L_min", "Paw", "PEEP", "FiO2", "FiO2_delivered",
    "PIP", "Pmean", "Pdriving", "MP", "CO", "SV", "DO2", "VO2", "SvO2", "ScvO2", "T_core",
    "airway_interface", "oxygen_interface", "vent_mode", "intubated",
    "ventilator_connected", "manual_ventilation_active", "bag_mask_ventilation_active",
    "airway_event_type", "airway_event_status", "airway_rescue_state",
    "intubation_attempt_count", "failed_intubation_count", "intubation_success_time_s",
    "extubation_time_s", "airway_event_hypoxia_burden", "aspiration_risk",
    "laryngospasm_score", "upper_airway_obstruction_score",
    "cardiac_rhythm", "rhythm_category", "has_pulse", "cardiac_arrest_active",
    "shockable_rhythm", "ROSC", "post_arrest_phase", "CPR_active", "CPR_quality",
    "compression_fraction", "cardiac_event_type", "cardiac_arrest_cause",
    "cardiac_arrest_time_s", "rosc_time_s", "last_shock_energy_J",
    "last_shock_time_s", "last_shock_mode", "last_shock_appropriate",
    "last_shock_effective", "last_shock_result",
    "defibrillation_attempt_count", "synchronized_cardioversion_count",
    "epinephrine_bolus_count", "amiodarone_bolus_count",
    "atropine_bolus_count", "last_rcp_drug", "last_rcp_drug_result",
    "last_rcp_drug_appropriate", "last_rcp_drug_time_s",
    "reperfusion_injury_risk", "renal_hypoperfusion_index",
    "post_rosc_care_status", "post_rosc_care_time_s",
    "post_rosc_oxygenation_optimized", "post_rosc_ventilation_optimized",
    "post_rosc_perfusion_support_active", "post_rosc_acidosis_burden",
    "post_rosc_myocardial_dysfunction_risk",
    "crystalloid_type", "crystalloid_rate_mL_h", "crystalloid_effective_mL_h",
    "crystalloid_active", "crystalloid_preload_response", "crystalloid_MAP_support_mmHg",
    "crystalloid_renal_perfusion_gain", "cumulative_crystalloid_input_mL", "fluid_balance", "urine_rate_mL_h",
]

BEDSIDE_FAST_KEYS = [
    "t", "HR", "MAP", "SBP", "DBP", "SAP", "DAP", "SaO2", "PaCO2", "EtCO2", "EtCO2_proxy", "Paw", "PEEP", "FiO2_delivered",
    "RR_total", "Vt", "airway_interface", "oxygen_interface", "vent_mode",
    "intubated", "airway_event_type", "airway_rescue_state",
    "cardiac_rhythm", "has_pulse", "cardiac_arrest_active", "shockable_rhythm",
    "CPR_active", "ROSC", "post_rosc_care_status",
    "crystalloid_type", "crystalloid_rate_mL_h", "crystalloid_effective_mL_h",
    "crystalloid_active", "cumulative_crystalloid_input_mL", "fluid_balance", "urine_rate_mL_h",
]

WAVEFORM_KEYS = [
    "t", "HR", "MAP", "SBP", "DBP", "SAP", "DAP", "arterial_pulse_pressure",
    "SaO2", "RR_total", "Paw", "PEEP", "Vt", "flow_L_s", "PaCO2",
    "EtCO2", "EtCO2_proxy", "etco2_pa_gradient", "etco2_perfusion_factor",
    "etco2_deadspace_factor", "vent_mode", "airway_interface",
    "cardiac_rhythm", "has_pulse", "cardiac_arrest_active", "shockable_rhythm", "CPR_active",
]

WAVEFORM_FAST_KEYS = ["t", "HR", "MAP", "SBP", "DBP", "SAP", "DAP", "SaO2", "RR_total", "Paw", "PEEP", "Vt", "Flow_current_mL_s", "flow_L_s", "PaCO2", "EtCO2", "EtCO2_proxy", "cardiac_rhythm", "has_pulse", "cardiac_arrest_active", "shockable_rhythm", "CPR_active"]

TRAINING_KEYS = [
    "t", "airway_interface", "oxygen_interface", "vent_mode", "airway_event_type",
    "airway_event_status", "airway_rescue_state", "intubation_attempt_count",
    "failed_intubation_count", "intubation_success_time_s", "extubation_time_s",
    "manual_ventilation_active", "bag_mask_ventilation_active", "SaO2", "MAP", "PaCO2",
    "cardiac_rhythm", "rhythm_category", "has_pulse", "cardiac_arrest_active",
    "shockable_rhythm", "ROSC", "CPR_active", "CPR_quality", "compression_fraction",
    "last_shock_energy_J", "last_shock_mode", "last_shock_result",
    "epinephrine_bolus_count", "amiodarone_bolus_count", "atropine_bolus_count",
    "last_rcp_drug", "last_rcp_drug_result", "post_rosc_care_status",
    "post_rosc_acidosis_burden", "post_rosc_myocardial_dysfunction_risk",
]

CONTROL_KEYS = [
    # Ventilator / oxygen controls mirrored back to the UI.
    "FiO2", "PEEP", "RR", "ventilator_RR_set", "Paw",

    # Cardiovascular / vasoactive controls accepted by the router.
    "norad_mcg_kg_min", "adrenaline_mcg_kg_min", "dopamine_mcg_kg_min",
    "vasopressin_mU_kg_min", "milrinone_mcg_kg_min",

    # Sedation / analgesia / paralysis controls accepted by the router.
    "ketamine_mg_kg_h", "fentanyl_mcg_kg_h", "remifentanil_mcg_kg_min",
    "morphine_mcg_kg_h", "midazolam_mcg_kg_h", "propofol_mg_kg_h",
    "dexmedetomidine_mcg_kg_h", "clonidine_mcg_kg_h", "rocuronium_mg_kg_h",

    # Bronchodilator / respiratory pharmacology controls.
    "salbutamol_mcg_kg_min", "ipratropium_mcg_kg_h", "magnesium_mg_kg_h",
    "nebulized_epinephrine_mcg_kg_min", "ino_ppm",

    # Endocrine / metabolic / renal / antimicrobial controls.
    "hydrocortisone_mg_kg_h", "dexamethasone_mcg_kg_h", "insulin_UI_h",
    "furosemide_mg_kg", "furosemide_mg_kg_h", "vancomycin_mg_kg_h",
    "piperacillin_mg_kg_h",

    # Fluids / crystalloids.
    "crystalloid_type", "crystalloid_rate_mL_h",
]


def controls_state(state: Any) -> Dict[str, Any]:
    """Return command/control values for UI round-trip synchronisation.

    This is intentionally separate from physiological bedside variables: a
    delivered value, such as FiO2_delivered, can differ from the commanded
    control, such as FiO2.  The UI needs the commanded values to keep sliders
    and numeric drug fields bidirectionally aligned with the backend Bus.
    """
    out = _subset(state, CONTROL_KEYS)
    rr_set = _get(state, "ventilator_RR_set", 0.0)
    if rr_set not in (None, 0, 0.0):
        out["RR"] = rr_set
    return out

DEBUG_KEYS = [
    "t", "patient_profile", "age_y", "weight_kg", "HR", "MAP", "CO", "SV", "CVP",
    "PAWP", "PAP_mean", "SaO2", "PaO2", "PaCO2", "EtCO2", "EtCO2_proxy",
    "PvO2", "SvO2", "ScvO2", "ScvO2_source", "ScvO2_revision", "DO2", "VO2", "ERO2",
    "etco2_pa_gradient", "etco2_perfusion_factor", "etco2_deadspace_factor", "etco2_source",
    "pH_a", "HCO3_mmol_L",
    "K_mmol_L", "glucose_mmol_L", "lactate", "Paw", "PEEP", "FiO2", "FiO2_delivered",
    "C_rs", "R_rs", "recruited_frac", "vq_shunt_frac", "vq_deadspace_frac",
    "vq_adaptive_sigma", "airway_interface", "oxygen_interface", "vent_mode",
    "intubated", "tube_resistance_cmH2O_L_s", "tube_obstruction_score",
    "NIV_failure_risk", "HFNC_failure_risk", "airway_event_type", "airway_event_status",
    "intubation_attempt_count", "failed_intubation_count", "intubation_success_time_s",
    "cardiac_event_revision", "cardiac_event_type", "cardiac_arrest_cause",
    "cardiac_rhythm", "rhythm_category", "has_pulse", "cardiac_arrest_active",
    "shockable_rhythm", "ROSC", "post_arrest_phase", "cardiac_arrest_time_s",
    "rosc_time_s", "CPR_active", "CPR_quality", "compression_fraction",
    "last_shock_energy_J", "last_shock_time_s", "defibrillation_attempt_count",
    "last_shock_mode", "last_shock_appropriate", "last_shock_effective", "last_shock_result",
    "synchronized_cardioversion_count", "epinephrine_bolus_count",
    "amiodarone_bolus_count", "atropine_bolus_count", "reperfusion_injury_risk",
    "last_rcp_drug", "last_rcp_drug_result", "last_rcp_drug_appropriate",
    "last_rcp_drug_time_s",
    "renal_hypoperfusion_index", "post_rosc_care_status", "post_rosc_care_time_s",
    "post_rosc_oxygenation_optimized", "post_rosc_ventilation_optimized",
    "post_rosc_perfusion_support_active", "post_rosc_acidosis_burden",
    "post_rosc_myocardial_dysfunction_risk",
    "hydrocortisone_adrenal_support_signal", "hydrocortisone_vasopressor_sensitization_signal",
    "hydrocortisone_antiinflammatory_signal", "dexamethasone_antiinflammatory_signal",
    "dexamethasone_ICP_edema_signal", "steroid_delayed_effect_signal",
    "C_furosemide_mg_L", "furosemide_diuresis_signal",
    "furosemide_effective_diuretic_signal", "furosemide_urine_gain",
    "furosemide_additional_urine_mL_h", "diuretic_hypovolemia_risk",
    "C_insulin_mU_L", "insulin_action_signal", "insulin_glucose_clearance_signal",
    "insulin_effective_clearance_mmol_L_h", "insulin_potassium_shift_signal",
    "insulin_effective_potassium_shift_mmol_L_h", "insulin_hypoglycemia_risk",
    "insulin_glucose_safety_factor", "insulin_potassium_safety_factor",
    "crystalloid_type", "crystalloid_rate_mL_h", "crystalloid_effective_mL_h",
    "crystalloid_active", "crystalloid_balanced_fraction", "crystalloid_chloride_load_index",
    "crystalloid_glucose_GIR_mg_kg_min", "crystalloid_preload_response",
    "crystalloid_MAP_support_mmHg", "crystalloid_renal_perfusion_gain",
    "cumulative_crystalloid_input_mL", "fluid_balance", "urine_rate_mL_h",
]


def _subset(state: Any, keys) -> Dict[str, Any]:
    return {k: _get(state, k) for k in keys if hasattr(state, k)}


def _arterial_pressures(state: Any, digits: int = 1) -> Dict[str, Any]:
    """Return bedside arterial pressures from model outputs, not MAP±cosmetics."""
    map_v = _num(_get(state, "MAP", 65.0), 65.0)
    sbp_raw = _get(state, "SBP", None)
    if sbp_raw is None:
        sbp_raw = _get(state, "SAP", None)
    dbp_raw = _get(state, "DBP", None)
    if dbp_raw is None:
        dbp_raw = _get(state, "DAP", None)
    sbp = _num(sbp_raw, map_v + 20.0)
    dbp = _num(dbp_raw, max(map_v - 15.0, 10.0))
    if sbp <= dbp:
        sbp = dbp + 5.0
    return {
        "SBP": round(sbp, digits),
        "DBP": round(dbp, digits),
        "SAP": round(sbp, digits),
        "DAP": round(dbp, digits),
        "arterial_pulse_pressure": round(max(sbp - dbp, 0.0), digits),
    }


def bedside_state(state: Any) -> Dict[str, Any]:
    out = _subset(state, BEDSIDE_KEYS)
    out["SpO2_percent"] = round(_num(_get(state, "SaO2", 0.0)) * 100.0, 1)
    out["SaO2"] = _round(_get(state, "SaO2", 0.0), 4)
    out["HR"] = _round(_get(state, "HR", 0.0), 1)
    out["MAP"] = _round(_get(state, "MAP", 0.0), 1)
    out.update(_arterial_pressures(state, 1))
    out["PaCO2"] = _round(_get(state, "PaCO2", 0.0), 1)
    out["EtCO2"] = _round(_get(state, "EtCO2", max(_num(_get(state, "PaCO2", 40.0)) - 5.0, 5.0)), 1)
    out["EtCO2_proxy"] = out["EtCO2"]
    out["PaO2"] = _round(_get(state, "PaO2", 0.0), 1)
    out["Paw"] = _round(_get(state, "Paw", 0.0), 1)
    out["PEEP"] = _round(_get(state, "PEEP", 0.0), 1)
    out["Vt_mL"] = _round(_get(state, "Vt", 0.0), 1)
    out["time_s"] = _round(_get(state, "t", 0.0), 3)
    out["controls"] = controls_state(state)
    return out


def bedside_fast_state(state: Any) -> Dict[str, Any]:
    out = _subset(state, BEDSIDE_FAST_KEYS)
    out["time_s"] = _round(_get(state, "t", 0.0), 2)
    out["SpO2_percent"] = round(_num(_get(state, "SaO2", 0.0)) * 100.0, 0)
    out["HR"] = _round(_get(state, "HR", 0.0), 0)
    out["MAP"] = _round(_get(state, "MAP", 0.0), 0)
    out.update(_arterial_pressures(state, 0))
    out["PaCO2"] = _round(_get(state, "PaCO2", 0.0), 0)
    out["EtCO2"] = _round(_get(state, "EtCO2", max(_num(_get(state, "PaCO2", 40.0)) - 5.0, 5.0)), 0)
    out["EtCO2_proxy"] = out["EtCO2"]
    out["Paw"] = _round(_get(state, "Paw", 0.0), 1)
    out["controls"] = controls_state(state)
    return out


def _etco2_values(state: Any, digits: int = 1) -> Dict[str, Any]:
    """Return model EtCO2 values while preserving the old EtCO2_proxy key."""
    pa = _num(_get(state, "PaCO2", 40.0), 40.0)
    et = _num(_get(state, "EtCO2", max(pa - 5.0, 5.0)), max(pa - 5.0, 5.0))
    et = max(min(et, pa - 1.0 if pa >= 8.0 else et), 2.0)
    return {
        "EtCO2": round(et, digits),
        "EtCO2_proxy": round(et, digits),
        "etco2_pa_gradient": round(max(pa - et, 0.0), digits),
    }


def _flow_values(state: Any, digits: int = 3) -> Dict[str, Any]:
    flow_ml_s = _num(_get(state, "Flow_current_mL_s", _get(state, "flow_L_s", 0.0) * 1000.0), 0.0)
    return {
        "Flow_current_mL_s": round(flow_ml_s, digits),
        "flow_L_s": round(flow_ml_s / 1000.0, digits),
    }


def waveform_state(state: Any) -> Dict[str, Any]:
    out = _subset(state, WAVEFORM_KEYS)
    out.update(_arterial_pressures(state, 1))
    out.update(_etco2_values(state, 1))
    out.update(_flow_values(state, 3))
    out["time_s"] = _round(_get(state, "t", 0.0), 3)
    return out


def waveform_fast_state(state: Any) -> Dict[str, Any]:
    out = _subset(state, WAVEFORM_FAST_KEYS)
    out["time_s"] = _round(_get(state, "t", 0.0), 2)
    out.update(_arterial_pressures(state, 0))
    out.update(_etco2_values(state, 0))
    out.update(_flow_values(state, 3))
    out["Vt"] = _round(_get(state, "Vt", 0.0), 1)
    return out


def training_state(state: Any) -> Dict[str, Any]:
    out = _subset(state, TRAINING_KEYS)
    out["time_s"] = _round(_get(state, "t", 0.0), 2)
    out["SpO2_percent"] = round(_num(_get(state, "SaO2", 0.0)) * 100.0, 0)
    return out


def debug_state(state: Any) -> Dict[str, Any]:
    out = _subset(state, DEBUG_KEYS)
    out["time_s"] = _round(_get(state, "t", 0.0), 3)
    return out


def full_state(state: Any) -> Dict[str, Any]:
    """Return the full Bus plus stable display aliases for UI panels.

    The full profile is used on demand by the extended monitor/emogas panels.
    Keep aliases here instead of in the JS so old/new variable names remain
    compatible after model refactors.
    """
    out = dict(getattr(state, "__dict__", {}))

    # Respiratory pressure aliases.
    peep = _num(_get(state, "PEEP", 0.0), 0.0)
    paw = _num(_get(state, "Paw", peep), peep)
    ppeak = _num(_get(state, "Ppeak", max(paw, peep)), max(paw, peep))
    out.setdefault("PIP", ppeak)
    out.setdefault("Pmean", 0.65 * peep + 0.35 * paw)
    out.setdefault("mean_airway_pressure", out.get("Pmean"))

    # Hematology/coagulation aliases used by extended monitor cards.
    if "PLT_count" in out:
        out.setdefault("PLT", out["PLT_count"])
        out.setdefault("platelets_10e9_L", out["PLT_count"])
    if "Hct_percent" in out:
        out.setdefault("Hct", out["Hct_percent"])
    if "WBC_count" in out:
        out.setdefault("WBC", out["WBC_count"])
        out.setdefault("WBC_10e9_L", out["WBC_count"])
    if "fibrinogen" in out:
        out.setdefault("fibrinogen_mg_dL", out["fibrinogen"])
    if "d_dimer" in out:
        out.setdefault("D_dimer", out["d_dimer"])
        out.setdefault("d_dimer_mg_L", out["d_dimer"])

    # Renal/fluid aliases.
    if "fluid_overload_percent" in out:
        out.setdefault("fluid_overload_fraction", _num(out["fluid_overload_percent"], 0.0) / 100.0)
    if "CRRT_net_UF_mL_h" in out:
        out.setdefault("crrt_net_ultrafiltration_mL_h", out["CRRT_net_UF_mL_h"])
        out.setdefault("CRRT_UF_mL_h", out["CRRT_net_UF_mL_h"])

    # Ventilation/drug aliases.
    if "VILI_risk" in out:
        out.setdefault("VILI_risk_index", out["VILI_risk"])
    if "C_propofol_mg_L" in out:
        out.setdefault("C_propofol_mcg_mL", out["C_propofol_mg_L"])  # numerically equivalent
    if "C_norad_ng_mL" in out:
        out.setdefault("C_noradrenaline_ng_mL", out["C_norad_ng_mL"])

    # Sepsis/nutrition aliases for display continuity.
    if "sepsis_severity_score" in out:
        out.setdefault("SIRS_score", out["sepsis_severity_score"])
    if "energy_intake_kcal_day" in out and "energy_expenditure_kcal_day" in out:
        denom = max(_num(out["energy_expenditure_kcal_day"], 0.0), 1.0)
        out.setdefault("nutrition_delivery_fraction", _num(out["energy_intake_kcal_day"], 0.0) / denom)
    if "energy_expenditure_kcal_day" in out:
        out.setdefault("REE_kcal_day", out["energy_expenditure_kcal_day"])

    return out


def project_state(state: Any, profile: str = "bedside") -> Dict[str, Any]:
    profile = (profile or "bedside").lower()
    if profile == "bedside":
        return bedside_state(state)
    if profile == "bedside_fast":
        return bedside_fast_state(state)
    if profile == "waveform":
        return waveform_state(state)
    if profile == "waveform_fast":
        return waveform_fast_state(state)
    if profile == "training":
        return training_state(state)
    if profile == "controls":
        return controls_state(state)
    if profile == "debug":
        return debug_state(state)
    if profile == "full":
        return full_state(state)
    raise ValueError(f"Unknown state profile: {profile}")
