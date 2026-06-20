"""
Pediatric cardiovascular scaling helpers (v1.05-alpha)
======================================================

Purpose
-------
Generate age/profile-aware cardiovascular parameter anchors for the public
Pediatric Critical Care Physiology Simulation Framework.

The functions in this file are pragmatic simulation anchors, not clinical
reference ranges or bedside decision rules. They preserve the historical
child_20kg model as the numerical reference while avoiding inappropriate reuse
of 20 kg ventricular volumes, elastance, vascular resistance, and baroreflex
limits in neonates/infants/adolescents.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
import math


AGE_GROUP_DEFAULTS = {
    "neonate": {
        "EF_lv": 0.60, "EF_rv": 0.56,
        "HR_min": 80.0, "HR_max": 220.0,
        "MAP": 45.0, "PAP_mean": 18.0, "PAWP": 7.0, "CVP": 5.0,
        "Ts_frac": 0.40, "T_ivc_frac": 0.055, "T_ivr_frac": 0.090,
        "FS_gain": 0.32,
    },
    "infant": {
        "EF_lv": 0.62, "EF_rv": 0.57,
        "HR_min": 65.0, "HR_max": 210.0,
        "MAP": 55.0, "PAP_mean": 17.0, "PAWP": 7.5, "CVP": 5.0,
        "Ts_frac": 0.39, "T_ivc_frac": 0.058, "T_ivr_frac": 0.095,
        "FS_gain": 0.36,
    },
    "toddler": {
        "EF_lv": 0.63, "EF_rv": 0.58,
        "HR_min": 55.0, "HR_max": 195.0,
        "MAP": 60.0, "PAP_mean": 16.0, "PAWP": 8.0, "CVP": 5.0,
        "Ts_frac": 0.385, "T_ivc_frac": 0.060, "T_ivr_frac": 0.100,
        "FS_gain": 0.38,
    },
    "child": {
        "EF_lv": 0.64, "EF_rv": 0.58,
        "HR_min": 45.0, "HR_max": 180.0,
        "MAP": 65.0, "PAP_mean": 15.0, "PAWP": 8.0, "CVP": 5.0,
        "Ts_frac": 0.38, "T_ivc_frac": 0.060, "T_ivr_frac": 0.100,
        "FS_gain": 0.40,
    },
    "adolescent": {
        "EF_lv": 0.62, "EF_rv": 0.57,
        "HR_min": 40.0, "HR_max": 170.0,
        "MAP": 75.0, "PAP_mean": 15.0, "PAWP": 8.0, "CVP": 5.0,
        "Ts_frac": 0.37, "T_ivc_frac": 0.065, "T_ivr_frac": 0.105,
        "FS_gain": 0.42,
    },
}

# Historical numerical anchor of the v1.0-alpha child_20kg cardiovascular model.
CHILD_20KG_ANCHOR = {
    "weight_kg": 20.0,
    "age_y": 6.0,
    "age_group": "child",
    "HR": 100.0,
    "MAP": 65.0,
    "CO_L_min": 4.0,
    "SV_mL": 40.0,
    "Emax_lv": 5.10,
    "Emin_lv": 0.08,
    "V0_lv": 5.0,
    "EDV0_lv": 55.0,
    "Emax_rv": 0.978,
    "Emin_rv": 0.03,
    "V0_rv": 8.0,
    "EDV0_rv": 60.0,
    "C_la": 8.0,
    "C_ra": 10.0,
    "V0_la": 20.0,
    "V0_ra": 25.0,
    "R_systemic": 1.060,
    "C_aortic": 4.72,
    "Zc_sys": 0.05,
    "R_pulmonary": 0.234,
    "C_pulmonary": 34.2,
    "Zc_pul": 0.01,
    "R_venous_sys": 0.078,
    "C_venous_sys": 15.0,
    "Vunstressed_sys": 1200.0,
}


def _clip(x: float, lo: float, hi: float) -> float:
    return float(max(lo, min(hi, x)))


def _cardiac_index_l_min_m2(age_group: str) -> float:
    """Pragmatic age-aware CI anchor for simulation initialization."""
    return {
        "neonate": 3.2,
        "infant": 3.8,
        "toddler": 4.0,
        "child": 4.2,
        "adolescent": 3.6,
    }.get(age_group, 4.0)


def _estimate_bsa_m2(weight_kg: float, age_y: float) -> float:
    """Small local BSA estimate to keep this helper dependency-light."""
    height_cm = 50.0 + 6.0 * age_y if age_y < 1.0 else 75.0 + 6.0 * min(age_y, 15.0)
    height_cm = _clip(height_cm, 48.0, 180.0)
    return math.sqrt(max(height_cm * weight_kg, 1.0) / 3600.0)


def profile_age_defaults(age_group: str) -> dict:
    """Return a copy of age-group cardiovascular defaults."""
    return dict(AGE_GROUP_DEFAULTS.get(age_group, AGE_GROUP_DEFAULTS["child"]))


def build_cardiovascular_scaling(
    *,
    weight_kg: float,
    age_y: float = 6.0,
    age_group: str = "child",
    patient_profile: str = "child_20kg",
    HR_ref: float | None = None,
    MAP_ref: float | None = None,
    CO_ref_L_min: float | None = None,
    CVP_ref: float | None = None,
    PAWP_ref: float | None = None,
    PAP_ref: float | None = None,
) -> dict:
    """
    Build cardiovascular parameter anchors for the requested pediatric profile.

    Rules
    -----
    * child_20kg remains the numerical anchor of the v1.0-alpha model.
    * ventricular volumes scale primarily with expected stroke volume.
    * elastance is recalculated from age-specific pressure and target ESV/V0,
      avoiding reuse of a 20 kg Emax in neonates.
    * vascular resistances are initialized from pressure-flow consistency;
      Windkessel compliances are chosen to preserve pragmatic time constants.
    """
    wt = max(float(weight_kg), 0.5)
    age_y = max(float(age_y), 0.0)
    group = str(age_group or "child")
    defaults = profile_age_defaults(group)

    # Preserve historical child_20kg anchor unless explicit scenario values require recalibration.
    is_child_anchor = (
        str(patient_profile) == "child_20kg"
        and abs(wt - 20.0) < 1e-6
        and (HR_ref is None or abs(float(HR_ref) - CHILD_20KG_ANCHOR["HR"]) <= 12.0)
        and (MAP_ref is None or abs(float(MAP_ref) - CHILD_20KG_ANCHOR["MAP"]) <= 8.0)
        and CO_ref_L_min is None
    )
    if is_child_anchor:
        out = dict(CHILD_20KG_ANCHOR)
        out.update({
            "age_y": age_y,
            "age_group": group,
            "patient_profile": patient_profile,
            "HR_ref": float(HR_ref if HR_ref is not None else CHILD_20KG_ANCHOR["HR"]),
            "MAP_ref": float(MAP_ref if MAP_ref is not None else CHILD_20KG_ANCHOR["MAP"]),
            "CO_ref_L_min": CHILD_20KG_ANCHOR["CO_L_min"],
            "Ts_frac": defaults["Ts_frac"],
            "T_ivc_frac": defaults["T_ivc_frac"],
            "T_ivr_frac": defaults["T_ivr_frac"],
            "FS_gain": defaults["FS_gain"],
            "MAP_setpoint": float(MAP_ref if MAP_ref is not None else CHILD_20KG_ANCHOR["MAP"]),
            "HR_min": defaults["HR_min"],
            "HR_max": defaults["HR_max"],
            "cv_scaling_revision": "v1.05-alpha",
        })
        return out

    BSA = _estimate_bsa_m2(wt, age_y)
    HR = float(HR_ref if HR_ref is not None else {
        "neonate": 145.0, "infant": 130.0, "toddler": 115.0, "child": 100.0, "adolescent": 80.0
    }.get(group, 100.0))
    MAP = float(MAP_ref if MAP_ref is not None else defaults["MAP"])
    CVP = float(CVP_ref if CVP_ref is not None else defaults["CVP"])
    PAWP = float(PAWP_ref if PAWP_ref is not None else defaults["PAWP"])
    PAP = float(PAP_ref if PAP_ref is not None else defaults["PAP_mean"])

    # Prefer scenario/profile CO if provided. Otherwise use age-aware CI with a
    # conservative mL/kg/min cap to avoid unrealistic adolescent hyperdynamic baseline.
    if CO_ref_L_min is not None:
        CO = float(CO_ref_L_min)
    else:
        CO_by_ci = _cardiac_index_l_min_m2(group) * BSA
        CO_by_weight = wt * {"neonate": 0.20, "infant": 0.18, "toddler": 0.17, "child": 0.16, "adolescent": 0.11}.get(group, 0.16)
        CO = float(0.5 * CO_by_ci + 0.5 * CO_by_weight)
    CO = _clip(CO, 0.15, 9.0)

    SV = max(CO * 1000.0 / max(HR, 1.0), 0.5)
    EF_lv = defaults["EF_lv"]
    EF_rv = defaults["EF_rv"]
    EDV0_lv = SV / EF_lv
    ESV_lv = max(EDV0_lv - SV, 0.25)
    V0_lv = max(0.09 * EDV0_lv, 0.15)
    Emax_lv = MAP / max(ESV_lv - V0_lv, 0.25)
    Emin_lv = 0.08 * (20.0 / wt) ** 0.35

    SV_rv = SV * 0.98
    EDV0_rv = SV_rv / EF_rv
    ESV_rv = max(EDV0_rv - SV_rv, 0.25)
    V0_rv = max(0.12 * EDV0_rv, 0.18)
    Emax_rv = PAP / max(ESV_rv - V0_rv, 0.20)
    Emin_rv = 0.03 * (20.0 / wt) ** 0.30

    CO_mL_s = max(CO * 1000.0 / 60.0, 1.0)
    R_systemic = _clip((MAP - CVP) / CO_mL_s, 0.15, 8.0)
    R_pulmonary = _clip(max(PAP - PAWP, 2.0) / CO_mL_s, 0.04, 3.0)
    R_venous = _clip(max(CVP, 1.0) / CO_mL_s, 0.02, 0.60)

    # Maintain approximate pressure-decay constants across body sizes.
    C_aortic = _clip(5.0 / R_systemic, 0.35, 35.0)
    C_pulmonary = _clip(8.0 / R_pulmonary, 1.5, 160.0)
    C_venous = _clip(6.0 * wt / 20.0 + 6.0 * BSA, 3.0, 45.0)
    volume_scale = wt / 20.0

    return {
        "weight_kg": wt,
        "age_y": age_y,
        "age_group": group,
        "patient_profile": str(patient_profile),
        "BSA_m2": BSA,
        "HR_ref": HR,
        "MAP_ref": MAP,
        "CO_ref_L_min": CO,
        "SV_mL": SV,
        "EF_lv_ref": EF_lv,
        "EF_rv_ref": EF_rv,
        "Emax_lv": _clip(Emax_lv, 1.2, 55.0),
        "Emin_lv": _clip(Emin_lv, 0.04, 0.35),
        "V0_lv": V0_lv,
        "EDV0_lv": EDV0_lv,
        "Emax_rv": _clip(Emax_rv, 0.25, 18.0),
        "Emin_rv": _clip(Emin_rv, 0.015, 0.15),
        "V0_rv": V0_rv,
        "EDV0_rv": EDV0_rv,
        "Ts_frac": defaults["Ts_frac"],
        "T_ivc_frac": defaults["T_ivc_frac"],
        "T_ivr_frac": defaults["T_ivr_frac"],
        "FS_gain": defaults["FS_gain"],
        "C_la": _clip(8.0 * volume_scale ** 0.85, 0.7, 25.0),
        "C_ra": _clip(10.0 * volume_scale ** 0.85, 0.8, 32.0),
        "V0_la": _clip(20.0 * volume_scale, 1.0, 70.0),
        "V0_ra": _clip(25.0 * volume_scale, 1.2, 85.0),
        "R_systemic": R_systemic,
        "C_aortic": C_aortic,
        "Zc_sys": _clip(0.05 * (20.0 / wt) ** 0.65, 0.015, 0.35),
        "R_pulmonary": R_pulmonary,
        "C_pulmonary": C_pulmonary,
        "Zc_pul": _clip(0.01 * (20.0 / wt) ** 0.65, 0.003, 0.08),
        "R_venous_sys": R_venous,
        "C_venous_sys": C_venous,
        "Vunstressed_sys": _clip(1200.0 * volume_scale, 120.0, 4200.0),
        "MAP_setpoint": MAP,
        "HR_min": defaults["HR_min"],
        "HR_max": defaults["HR_max"],
        "cv_scaling_revision": "v1.05-alpha",
    }


def heart_btb_params_from_scaling(scaling: dict) -> dict:
    keys = [
        "weight_kg", "Emax_lv", "Emin_lv", "V0_lv", "EDV0_lv", "Ts_frac",
        "T_ivc_frac", "T_ivr_frac", "Emax_rv", "Emin_rv", "V0_rv", "EDV0_rv",
        "FS_gain", "C_la", "C_ra", "V0_la", "V0_ra",
    ]
    return {k: scaling[k] for k in keys if k in scaling}


def heart_lumped_params_from_scaling(scaling: dict) -> dict:
    keys = [
        "Emax_lv", "Emin_lv", "V0_lv", "EDV0_lv", "Emax_rv", "Emin_rv",
        "V0_rv", "EDV0_rv", "C_la", "C_ra", "Ts_frac",
    ]
    out = {k: scaling[k] for k in keys if k in scaling}
    out["frank_starling_gain"] = scaling.get("FS_gain", 0.40)
    return out


def circulation_params_from_scaling(scaling: dict) -> dict:
    keys = [
        "R_systemic", "C_aortic", "Zc_sys", "R_pulmonary", "C_pulmonary",
        "Zc_pul", "R_venous_sys", "C_venous_sys", "Vunstressed_sys",
    ]
    return {k: scaling[k] for k in keys if k in scaling}


def baroreflex_params_from_scaling(scaling: dict, *, auto_setpoint: bool = False) -> dict:
    return {
        "MAP_setpoint": float(scaling.get("MAP_setpoint", 65.0)),
        "HR_min": float(scaling.get("HR_min", 40.0)),
        "HR_max": float(scaling.get("HR_max", 180.0)),
        "auto_setpoint": bool(auto_setpoint),
    }
