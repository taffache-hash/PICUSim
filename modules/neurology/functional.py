"""
Neurofunctional Module — v0.25
==============================

Qualitative neurological-function layer for PICU simulations.

Scope
-----
This module models functional neurological status rather than structural ICP only:

* GCS/AVPU/RASS proxy
* global encephalopathy burden
* septic, metabolic, hepatic and hypoxic-ischemic encephalopathy components
* seizure-risk proxy
* delirium/withdrawal state indices
* cerebral metabolic-rate modifier
* respiratory-drive and sympathetic modifiers from depressed consciousness/agitation

This is not a diagnostic neurological model and is not intended to replace
clinical scores. It is a qualitative physiology axis for exploratory simulation.
"""
from __future__ import annotations
from typing import List
import numpy as np

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


def _clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return float(np.clip(x, lo, hi))


class NeurofunctionalModule(BaseModule):
    DEFAULT_PARAMS = {
        "weight_kg": 20.0,
        "baseline_GCS": 15.0,
        "tau_state_s": 45.0,
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="Neurofunctional", params=merged)
        self._gcs = float(merged["baseline_GCS"])
        self._enceph = 0.0
        self._seizure = 0.0
        self._delirium_state = 0.0
        self._withdrawal_state = 0.0
        self._structural_burden = 0.0

    @property
    def input_keys(self) -> List[str]:
        return [
            "PaO2", "PaCO2", "SaO2", "pH_a", "DO2", "MAP", "lactate",
            "Na_mmol_L", "K_mmol_L", "osmolarity_mOsm_L", "glucose_mmol_L",
            "urea_mmol_L", "ammonia_umol_L", "T_core", "ICP_mmHg", "CPP_mmHg",
            "PbtO2_mmHg", "sepsis_severity_score", "cytokine_drive",
            "hepatic_encephalopathy_index", "sedation_score", "delirium_risk",
            "withdrawal_risk", "pain_score", "stress_index", "drug_NMB_frac",
            "midazolam_mcg_kg_h", "propofol_mg_kg_h", "dexmedetomidine_mcg_kg_h",
            "opioid_resp_depression", "cooling_device_active", "hypothermia_index",
        ]

    @property
    def output_keys(self) -> List[str]:
        return [
            "GCS_proxy", "AVPU_state", "consciousness_index", "encephalopathy_index",
            "septic_encephalopathy_index", "metabolic_encephalopathy_index",
            "hypoxic_ischemic_neuro_index", "seizure_risk_index",
            "delirium_state_index", "withdrawal_state_index",
            "cerebral_metabolic_rate_mod", "neuro_resp_drive_mod",
            "neuro_HR_add", "neuro_sympathetic_mod", "neuro_severity_score",
            "neuro_alert", "RASS_proxy",
        ]

    def initialize(self, bus: PhysiologicalBus) -> None:
        self._gcs = float(np.clip(getattr(bus.state, "GCS_proxy", self.params["baseline_GCS"]), 3.0, 15.0))
        self._enceph = float(np.clip(getattr(bus.state, "encephalopathy_index", 0.0), 0.0, 1.0))
        self._seizure = float(np.clip(getattr(bus.state, "seizure_risk_index", 0.0), 0.0, 1.0))
        self._delirium_state = float(np.clip(getattr(bus.state, "delirium_state_index", 0.0), 0.0, 1.0))
        self._withdrawal_state = float(np.clip(getattr(bus.state, "withdrawal_state_index", 0.0), 0.0, 1.0))
        # Persistent structural/primary neurological burden. This is mainly for
        # TBI/primary CNS scenarios where an initially low GCS should not fully
        # normalize simply because sedatives are weaned and ICP improves.
        self._structural_burden = _clip(max((12.0 - self._gcs) / 9.0, 0.0), 0.0, 0.45)
        bus.update({
            "GCS_proxy": self._gcs,
            "AVPU_state": self._avpu(self._gcs),
            "consciousness_index": _clip((15.0 - self._gcs) / 12.0),
            "encephalopathy_index": self._enceph,
            "seizure_risk_index": self._seizure,
            "delirium_state_index": self._delirium_state,
            "withdrawal_state_index": self._withdrawal_state,
            "cerebral_metabolic_rate_mod": 1.0,
            "neuro_resp_drive_mod": 1.0,
            "neuro_HR_add": 0.0,
            "neuro_sympathetic_mod": 1.0,
            "neuro_severity_score": 0.0,
            "neuro_alert": False,
            "RASS_proxy": 0.0,
        })

    @staticmethod
    def _avpu(gcs: float) -> str:
        if gcs >= 14.0:
            return "A"
        if gcs >= 10.0:
            return "V"
        if gcs >= 7.0:
            return "P"
        return "U"

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        PaO2 = float(getattr(bus.state, "PaO2", 90.0))
        PaCO2 = float(getattr(bus.state, "PaCO2", 40.0))
        SaO2 = float(getattr(bus.state, "SaO2", 0.97))
        pH = float(getattr(bus.state, "pH_a", 7.40))
        DO2 = float(getattr(bus.state, "DO2", 500.0))
        MAP = float(getattr(bus.state, "MAP", 65.0))
        lactate = float(getattr(bus.state, "lactate", 1.0))
        Na = float(getattr(bus.state, "Na_mmol_L", 138.0))
        K = float(getattr(bus.state, "K_mmol_L", 4.0))
        osm = float(getattr(bus.state, "osmolarity_mOsm_L", 286.0))
        glucose = float(getattr(bus.state, "glucose_mmol_L", 5.0))
        urea = float(getattr(bus.state, "urea_mmol_L", 5.0))
        ammonia = float(getattr(bus.state, "ammonia_umol_L", 35.0))
        T = float(getattr(bus.state, "T_core", 37.0))
        ICP = float(getattr(bus.state, "ICP_mmHg", 10.0))
        CPP = float(getattr(bus.state, "CPP_mmHg", MAP - ICP))
        PbtO2 = float(getattr(bus.state, "PbtO2_mmHg", 25.0))
        sepsis = float(getattr(bus.state, "sepsis_severity_score", 0.0))
        cytokine = float(getattr(bus.state, "cytokine_drive", 0.0))
        hep_enceph = float(getattr(bus.state, "hepatic_encephalopathy_index", 0.0))
        sedation = float(getattr(bus.state, "sedation_score", 0.0))
        delirium_risk = float(getattr(bus.state, "delirium_risk", 0.05))
        withdrawal_risk = float(getattr(bus.state, "withdrawal_risk", 0.0))
        pain = float(getattr(bus.state, "pain_score", 2.0))
        stress = float(getattr(bus.state, "stress_index", 0.1))
        nmb = float(getattr(bus.state, "drug_NMB_frac", 0.0))
        opioid_dep = float(getattr(bus.state, "opioid_resp_depression", 0.0))
        cooling = bool(getattr(bus.state, "cooling_device_active", False))
        hypothermia = float(getattr(bus.state, "hypothermia_index", 0.0))
        seizure_treatment = float(getattr(bus.state, "seizure_treatment_effect", 0.0))
        wt = float(self.params["weight_kg"])

        hypoxemia = _clip((0.92 - SaO2) * 3.0 + (60.0 - PaO2) / 70.0 + (20.0 - PbtO2) / 25.0)
        low_cpp = _clip((45.0 - CPP) / 30.0 + (50.0 - MAP) / 35.0)
        low_do2 = _clip((wt * 14.0 - DO2) / max(wt * 14.0, 1.0))
        hypercapnia = _clip((PaCO2 - 55.0) / 35.0)
        severe_acidosis = _clip((7.25 - pH) / 0.35)
        hypoxic_ischemic = _clip(0.35 * hypoxemia + 0.30 * low_cpp + 0.20 * low_do2 + 0.15 * severe_acidosis)

        sodium_derange = max(_clip((135.0 - Na) / 18.0), _clip((Na - 150.0) / 18.0))
        osm_derange = max(_clip((275.0 - osm) / 28.0), _clip((osm - 320.0) / 45.0))
        glucose_derange = max(_clip((4.0 - glucose) / 2.5), _clip((glucose - 15.0) / 15.0))
        uremia = _clip((urea - 16.0) / 25.0)
        ammonia_burden = _clip((ammonia - 60.0) / 150.0)
        acid_base_burden = max(_clip((7.25 - pH) / 0.35), _clip((pH - 7.55) / 0.25))
        metabolic = _clip(0.26 * sodium_derange + 0.18 * osm_derange + 0.18 * glucose_derange +
                          0.16 * uremia + 0.14 * ammonia_burden + 0.08 * acid_base_burden)

        septic = _clip(0.55 * sepsis + 0.35 * cytokine + 0.10 * _clip((lactate - 3.0) / 8.0))
        intracranial = _clip((ICP - 20.0) / 20.0 + (50.0 - CPP) / 35.0)
        fever_burden = _clip((T - 39.0) / 2.5)
        temp_burden = max(fever_burden, 0.5 * hypothermia)

        # Structural burden decays slowly; this prevents primary CNS scenarios
        # from becoming neurologically normal within minutes.
        self._structural_burden *= float(np.exp(-dt / 5400.0))
        enceph_target = _clip(0.24 * hypoxic_ischemic + 0.22 * metabolic + 0.18 * septic +
                              0.14 * hep_enceph + 0.08 * intracranial + 0.04 * temp_burden +
                              0.10 * self._structural_burden)

        seizure_target = _clip(0.36 * sodium_derange + 0.24 * glucose_derange + 0.14 * fever_burden +
                               0.10 * hypoxemia + 0.08 * ammonia_burden + 0.12 * withdrawal_risk +
                               0.07 * intracranial + 0.05 * _clip((K - 6.0) / 2.0))
        seizure_target *= (1.0 - 0.65 * seizure_treatment)

        delirium_target = _clip(delirium_risk + 0.25 * septic + 0.18 * metabolic + 0.10 * pain / 10.0 +
                                0.12 * stress + 0.10 * withdrawal_risk - 0.08 * nmb)
        withdrawal_target = _clip(withdrawal_risk + 0.20 * pain / 10.0 + 0.15 * stress - 0.08 * sedation)

        alpha = 1.0 - np.exp(-dt / max(float(self.params["tau_state_s"]), 1.0))
        self._enceph += alpha * (enceph_target - self._enceph)
        self._seizure += alpha * (seizure_target - self._seizure)
        self._delirium_state += alpha * (delirium_target - self._delirium_state)
        self._withdrawal_state += alpha * (withdrawal_target - self._withdrawal_state)

        consciousness_target = _clip(0.44 * self._enceph + 0.30 * sedation + 0.10 * opioid_dep + 0.06 * intracranial + 0.18 * self._structural_burden)
        gcs_target = 15.0 - 12.0 * consciousness_target
        # NMB affects motor exam: reduce observable GCS proxy modestly without implying worse brain injury.
        gcs_target -= 2.0 * nmb
        self._gcs += alpha * (gcs_target - self._gcs)
        self._gcs = float(np.clip(self._gcs, 3.0, 15.0))
        consciousness = _clip((15.0 - self._gcs) / 12.0)

        cmro2_mod = float(np.clip(1.0 - 0.22 * sedation - 0.12 * hypothermia - 0.08 * nmb +
                                  0.12 * fever_burden + 0.15 * self._seizure, 0.55, 1.35))
        resp_drive_mod = float(np.clip(1.0 - 0.35 * consciousness - 0.20 * opioid_dep - 0.12 * hypercapnia +
                                       0.10 * self._seizure, 0.20, 1.15))
        sympathetic_mod = float(np.clip(1.0 + 0.25 * self._delirium_state + 0.22 * self._withdrawal_state +
                                        0.10 * self._seizure - 0.18 * sedation, 0.65, 1.55))
        neuro_hr_add = float(np.clip(18.0 * (sympathetic_mod - 1.0) - 8.0 * consciousness, -18.0, 22.0))
        severity = _clip(0.28 * consciousness + 0.22 * self._enceph + 0.18 * self._seizure +
                         0.14 * self._delirium_state + 0.08 * hypoxic_ischemic + 0.05 * metabolic + 0.05 * intracranial)
        rass = float(np.clip(-5.0 * sedation - 2.5 * self._enceph + 3.0 * self._delirium_state +
                             2.0 * self._withdrawal_state + 1.5 * self._seizure, -5.0, 4.0))
        neuro_alert = bool(severity > 0.45 or self._seizure > 0.35 or self._gcs < 9.0)

        bus.update({
            "GCS_proxy": self._gcs,
            "AVPU_state": self._avpu(self._gcs),
            "consciousness_index": consciousness,
            "encephalopathy_index": float(self._enceph),
            "septic_encephalopathy_index": septic,
            "metabolic_encephalopathy_index": metabolic,
            "hypoxic_ischemic_neuro_index": hypoxic_ischemic,
            "seizure_risk_index": float(self._seizure),
            "delirium_state_index": float(self._delirium_state),
            "withdrawal_state_index": float(self._withdrawal_state),
            "cerebral_metabolic_rate_mod": cmro2_mod,
            "neuro_resp_drive_mod": resp_drive_mod,
            "neuro_HR_add": neuro_hr_add,
            "neuro_sympathetic_mod": sympathetic_mod,
            "neuro_severity_score": severity,
            "neuro_alert": neuro_alert,
            "RASS_proxy": rass,
        })
