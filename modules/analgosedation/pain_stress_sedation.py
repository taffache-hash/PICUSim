"""
Pain / Stress / Analgosedation Module — v0.12
=============================================
Modulo clinico qualitativo per PICU: dolore, stress simpatico, sedazione,
analgesia, rischio delirium e withdrawal. Non è un modello PK/PD validato;
serve come accoppiatore fisiologico tra farmaci sedativi/analgesici e organi.

Farmaci aggiunti con PK monocompartimentale semplificata:
  - remifentanil
  - morphine/clonidine come fallback se PharmacologyModule non è presente

Integra anche concentrazioni già prodotte da PharmacologyModule:
  - ketamina, midazolam, propofol, rocuronio
  - fentanyl, dexmedetomidine, morphine e clonidine quando disponibili

Output chiave:
  pain_score, stress_index, sedation_score, analgesia_score,
  sympathetic_tone, delirium_risk, withdrawal_risk,
  sed_resp_mod, sed_VO2_mod, sed_HR_mod, sed_SVR_mod.
"""
from __future__ import annotations
import numpy as np
from typing import List

from core.base_module import BaseModule
from core.bus import PhysiologicalBus
from modules.pharmacology.pk_pd import OneCompartmentPK, hill


class PainStressSedationModule(BaseModule):
    DEFAULT_PARAMS = {
        "weight_kg": 20.0,
        "baseline_pain": 2.0,
        "procedural_pain_gain": 1.0,
        # PK rough, pediatric-friendly placeholders
        "fen_Vd_per_kg": 4.0, "fen_k_elim": 0.0000963,   # t1/2 ~120 min
        "remi_Vd_per_kg": 0.25, "remi_k_elim": 0.00462,  # t1/2 ~2.5 min
        "mor_Vd_per_kg": 3.0, "mor_k_elim": 0.000193,    # t1/2 ~60 min
        "dex_Vd_per_kg": 1.5, "dex_k_elim": 0.0000963,   # t1/2 ~120 min
        "clo_Vd_per_kg": 2.0, "clo_k_elim": 0.0000385,   # t1/2 ~300 min
        # PD EC50 rough
        "fen_EC50_anal": 1.5, "fen_EC50_resp": 3.0,
        "remi_EC50_anal": 2.0, "remi_EC50_resp": 4.0,
        "mor_EC50_anal": 20.0, "mor_EC50_resp": 45.0,
        "dex_EC50_sed": 0.6, "dex_EC50_hemo": 0.8,
        "clo_EC50_sed": 0.8, "clo_EC50_hemo": 1.0,
        # delirium / withdrawal qualitative weights
        "benzo_delirium_weight": 0.30,
        "opioid_withdrawal_tau_h": 36.0,
        "benzo_withdrawal_tau_h": 48.0,
        # v1.08: when PharmacologyModule is present, fentanyl and dexmedetomidine
        # concentrations are owned by that module to keep PK scaling centralized.
        "use_external_fentanyl_dex_pk": True,
        "use_external_morphine_pk": True,
        "use_external_clonidine_pk": True,
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="PainStressSedation", params=merged)
        self._pk_fen = self._pk_remi = self._pk_mor = None
        self._pk_dex = self._pk_clo = None
        self._opioid_exposure_h = 0.0
        self._benzo_exposure_h = 0.0
        self._prev_opioid_load = 0.0
        self._prev_benzo_load = 0.0

    @property
    def input_keys(self) -> List[str]:
        return ["fentanyl_mcg_kg_h", "remifentanil_mcg_kg_min", "morphine_mcg_kg_h",
                "dexmedetomidine_mcg_kg_h", "clonidine_mcg_kg_h",
                "C_ketamine_mg_L", "C_midazolam_ng_mL", "C_propofol_mg_L",
                "C_rocuronium_ng_mL", "PaCO2", "PaO2", "MAP", "T_core", "lactate"]

    @property
    def output_keys(self) -> List[str]:
        return ["pain_score", "stress_index", "sedation_score", "analgesia_score",
                "sympathetic_tone", "delirium_risk", "withdrawal_risk",
                "sed_resp_mod", "sed_VO2_mod", "sed_HR_mod", "sed_SVR_mod",
                "opioid_resp_depression", "opioid_analgesia_signal",
                "gaba_sedation_signal", "sedation_non_gaba_resp_signal",
                "ketamine_analgesia_signal", "ketamine_dissociation_signal",
                "ketamine_resp_depression_signal",
                "alpha2_sedation_signal", "alpha2_sympatholysis_signal",
                "dexmedetomidine_sedation_signal", "dexmedetomidine_sympatholysis_signal",
                "fentanyl_analgesia_signal", "fentanyl_resp_depression_signal",
                "remifentanil_analgesia_signal", "remifentanil_resp_depression_signal",
                "morphine_analgesia_signal", "morphine_resp_depression_signal",
                "C_fentanyl_ng_mL", "C_remifentanil_ng_mL",
                "C_morphine_ng_mL", "C_dexmedetomidine_ng_mL", "C_clonidine_ng_mL"]

    def initialize(self, bus: PhysiologicalBus) -> None:
        wt = self.params["weight_kg"]
        self._pk_fen = OneCompartmentPK(self.params["fen_Vd_per_kg"] * wt, self.params["fen_k_elim"])
        self._pk_remi = OneCompartmentPK(self.params["remi_Vd_per_kg"] * wt, self.params["remi_k_elim"])
        self._pk_mor = OneCompartmentPK(self.params["mor_Vd_per_kg"] * wt, self.params["mor_k_elim"])
        self._pk_dex = OneCompartmentPK(self.params["dex_Vd_per_kg"] * wt, self.params["dex_k_elim"])
        self._pk_clo = OneCompartmentPK(self.params["clo_Vd_per_kg"] * wt, self.params["clo_k_elim"])
        bus.update({
            "pain_score": float(self.params["baseline_pain"]),
            "stress_index": 0.10,
            "sedation_score": 0.0,
            "analgesia_score": 0.0,
            "sympathetic_tone": 1.0,
            "delirium_risk": 0.05,
            "withdrawal_risk": 0.0,
            "sed_resp_mod": 1.0,
            "sed_VO2_mod": 1.0,
            "sed_HR_mod": 1.0,
            "sed_SVR_mod": 1.0,
            "opioid_resp_depression": 0.0,
            "opioid_analgesia_signal": 0.0,
            "gaba_sedation_signal": 0.0,
            "sedation_non_gaba_resp_signal": 0.0,
            "ketamine_analgesia_signal": 0.0,
            "ketamine_dissociation_signal": 0.0,
            "ketamine_resp_depression_signal": 0.0,
            "alpha2_sedation_signal": 0.0,
            "alpha2_sympatholysis_signal": 0.0,
            "dexmedetomidine_sedation_signal": 0.0,
            "dexmedetomidine_sympatholysis_signal": 0.0,
            "fentanyl_analgesia_signal": 0.0,
            "fentanyl_resp_depression_signal": 0.0,
            "remifentanil_analgesia_signal": 0.0,
            "remifentanil_resp_depression_signal": 0.0,
            "morphine_analgesia_signal": 0.0,
            "morphine_resp_depression_signal": 0.0,
        })

    def _uses_external_fentanyl_dex_pk(self, bus: PhysiologicalBus) -> bool:
        return bool(
            self.params.get("use_external_fentanyl_dex_pk", True)
            and hasattr(bus.state, "pk_extension_revision")
            and int(bus.get("pk_extension_revision")) >= 108
        )

    def _uses_external_morphine_pk(self, bus: PhysiologicalBus) -> bool:
        return bool(
            self.params.get("use_external_morphine_pk", True)
            and hasattr(bus.state, "pk_extension_revision")
            and int(bus.get("pk_extension_revision")) >= 114
        )

    def _uses_external_clonidine_pk(self, bus: PhysiologicalBus) -> bool:
        return bool(
            self.params.get("use_external_clonidine_pk", True)
            and hasattr(bus.state, "pk_extension_revision")
            and int(bus.get("pk_extension_revision")) >= 115
        )

    def _step_pk(self, bus: PhysiologicalBus, dt: float) -> tuple[float, float, float, float, float, bool, bool, bool]:
        wt = self.params["weight_kg"]
        external_fd = self._uses_external_fentanyl_dex_pk(bus)
        external_mor = self._uses_external_morphine_pk(bus)
        external_clo = self._uses_external_clonidine_pk(bus)
        # Convert all infusion rates to mg/min for OneCompartmentPK.
        fen_mg_min = bus.get("fentanyl_mcg_kg_h") * wt / 1000.0 / 60.0
        remi_mg_min = bus.get("remifentanil_mcg_kg_min") * wt / 1000.0
        mor_mg_min = bus.get("morphine_mcg_kg_h") * wt / 1000.0 / 60.0
        dex_mg_min = bus.get("dexmedetomidine_mcg_kg_h") * wt / 1000.0 / 60.0
        clo_mg_min = bus.get("clonidine_mcg_kg_h") * wt / 1000.0 / 60.0

        # Fentanyl/dex are either owned by PharmacologyModule v1.08 or by this
        # module as a standalone fallback. Morphine is owned by PharmacologyModule
        # v1.14+/v1.15+ when available; remifentanil remains owned locally.
        if not external_fd:
            self._pk_fen.step(fen_mg_min, dt)
            self._pk_dex.step(dex_mg_min, dt)
        self._pk_remi.step(remi_mg_min, dt)
        if not external_mor:
            self._pk_mor.step(mor_mg_min, dt)
        if not external_clo:
            self._pk_clo.step(clo_mg_min, dt)

        C_fen = bus.get("C_fentanyl_ng_mL") if external_fd else self._pk_fen.C_plasma * 1000.0
        C_dex = bus.get("C_dexmedetomidine_ng_mL") if external_fd else self._pk_dex.C_plasma * 1000.0
        C_mor = bus.get("C_morphine_ng_mL") if external_mor else self._pk_mor.C_plasma * 1000.0
        C_clo = bus.get("C_clonidine_ng_mL") if external_clo else self._pk_clo.C_plasma * 1000.0

        # mg/L == mcg/mL == 1000 ng/mL for conversion
        return (C_fen,
                self._pk_remi.C_plasma * 1000.0,
                C_mor,
                C_dex,
                C_clo,
                external_fd,
                external_mor,
                external_clo)

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        C_fen, C_remi, C_mor, C_dex, C_clo, external_fd_pk, external_mor_pk, external_clo_pk = self._step_pk(bus, dt)
        C_ket = bus.get("C_ketamine_mg_L")
        C_mid = bus.get("C_midazolam_ng_mL")
        C_pro = bus.get("C_propofol_mg_L")
        nmb = bus.get("drug_NMB_frac")

        E_fen_anal = hill(C_fen, self.params["fen_EC50_anal"], 0.85, 1.3)
        E_remi_anal = hill(C_remi, self.params["remi_EC50_anal"], 0.90, 1.5)
        E_mor_anal = hill(C_mor, self.params["mor_EC50_anal"], 0.75, 1.2)
        opioid_anal = 1.0 - (1.0 - E_fen_anal) * (1.0 - E_remi_anal) * (1.0 - E_mor_anal)
        ket_anal = hill(C_ket, 0.20, 0.55, 1.4)
        alpha2_sed = 1.0 - (1.0 - hill(C_dex, self.params["dex_EC50_sed"], 0.70, 1.7)) \
                           * (1.0 - hill(C_clo, self.params["clo_EC50_sed"], 0.45, 1.4))
        gaba_sed = 1.0 - (1.0 - hill(C_mid, 150.0, 0.80, 1.8)) \
                         * (1.0 - hill(C_pro, 2.0, 0.90, 2.0))
        diss_sed = hill(C_ket, 1.2, 0.35, 1.5)

        analgesia = float(np.clip(1.0 - (1.0 - opioid_anal) * (1.0 - ket_anal), 0.0, 1.0))
        # Step 3.5: neuromuscular blockade is not sedation. Keep rocuronium
        # out of sedation_score; sedation must still come from GABA drugs,
        # alpha-2 agonists or dissociative ketamine.
        sedation = float(np.clip(1.0 - (1.0 - gaba_sed) * (1.0 - alpha2_sed) * (1.0 - diss_sed), 0.0, 1.0))

        # Pain/stress: hypoxia, hypercapnia, fever and lactate add physiologic stress;
        # analgesia/sedation suppress perceived pain and sympathetic output.
        base_pain = self.params["baseline_pain"]
        gas_stress = 0.025 * max(bus.get("PaCO2") - 50.0, 0.0) + 0.020 * max(75.0 - bus.get("PaO2"), 0.0)
        metabolic_stress = 0.18 * max(bus.get("T_core") - 38.0, 0.0) + 0.07 * max(bus.get("lactate") - 2.0, 0.0)
        hemo_stress = 0.015 * max(55.0 - bus.get("MAP"), 0.0)
        raw_pain = base_pain + 10.0 * (gas_stress + metabolic_stress + hemo_stress)
        pain = float(np.clip(raw_pain * (1.0 - 0.75*analgesia) * (1.0 - 0.25*sedation), 0.0, 10.0))
        stress = float(np.clip((pain/10.0)*0.55 + gas_stress + metabolic_stress + hemo_stress, 0.0, 1.0))

        E_fen_resp = hill(C_fen, self.params["fen_EC50_resp"], 0.55, 1.4)
        E_remi_resp = hill(C_remi, self.params["remi_EC50_resp"], 0.60, 1.6)
        E_mor_resp = hill(C_mor, self.params["mor_EC50_resp"], 0.45, 1.2)
        opioid_resp = float(np.clip(1.0 - (1.0 - E_fen_resp) * (1.0 - E_remi_resp) * (1.0 - E_mor_resp), 0.0, 0.95))
        alpha2_hemo = float(np.clip(1.0 - (1.0 - hill(C_dex, self.params["dex_EC50_hemo"], 0.22, 1.6))
                                      * (1.0 - hill(C_clo, self.params["clo_EC50_hemo"], 0.15, 1.3)), 0.0, 0.45))

        # Step 3.4B: midazolam/propofol depress respiratory drive through
        # PharmacologyModule.drug_drive_mod. Do not apply the same GABA sedation
        # a second time through sed_resp_mod.
        # Step 3.4C: ketamine contributes analgesia/dissociative sedation but is
        # not treated as a primary respiratory depressant. Keep diss_sed out of
        # sed_resp_mod so ketamine differs clearly from opioids/GABA sedatives.
        # Step 3.4D: alpha-2 agonists provide cooperative sedation and
        # sympatholysis with minimal primary respiratory depression in this
        # educational scaffold. Keep alpha2_sed out of sed_resp_mod so
        # dexmedetomidine/clonidine do not behave like GABA sedatives/opioids.
        # Step 3.5: rocuronium is neuromuscular blockade, not respiratory
        # sedation. The blockade is applied once in ChemoreflexModule through
        # drug_NMB_frac, so keep NMB out of sed_resp_mod to avoid double counting.
        non_gaba_resp_sedation = 0.0
        ketamine_resp_depression = 0.0
        alpha2_resp_depression = 0.0
        sed_resp_mod = float(np.clip((1.0 - 0.65*opioid_resp), 0.02, 1.20))
        sympathetic_tone = float(np.clip(1.0 + 0.55*stress - 0.30*alpha2_hemo - 0.08*sedation + 0.08*ket_anal, 0.65, 1.55))
        sed_HR_mod = float(np.clip(sympathetic_tone * (1.0 - 0.18*alpha2_hemo), 0.55, 1.60))
        sed_SVR_mod = float(np.clip(1.0 + 0.30*stress - 0.18*alpha2_hemo, 0.65, 1.45))
        sed_VO2_mod = float(np.clip(1.0 + 0.30*stress - 0.12*sedation - 0.08*nmb, 0.65, 1.45))

        opioid_load = opioid_anal
        benzo_load = hill(C_mid, 150.0, 1.0, 1.8)
        if opioid_load > 0.20:
            self._opioid_exposure_h += dt / 3600.0 * opioid_load
        if benzo_load > 0.20:
            self._benzo_exposure_h += dt / 3600.0 * benzo_load
        # Withdrawal rises after accumulated exposure when current load falls.
        opioid_drop = max(self._prev_opioid_load - opioid_load, 0.0)
        benzo_drop = max(self._prev_benzo_load - benzo_load, 0.0)
        withdrawal_raw = (self._opioid_exposure_h/self.params["opioid_withdrawal_tau_h"])*opioid_drop + (self._benzo_exposure_h/self.params["benzo_withdrawal_tau_h"])*benzo_drop
        clonidine_withdrawal_mod = float(np.clip(bus.get("clonidine_withdrawal_mod"), 0.0, 0.80))
        withdrawal = float(np.clip(withdrawal_raw * (1.0 - clonidine_withdrawal_mod), 0.0, 1.0))
        self._prev_opioid_load = opioid_load
        self._prev_benzo_load = benzo_load

        delirium = float(np.clip(0.05 + self.params["benzo_delirium_weight"]*benzo_load + 0.10*max(bus.get("T_core")-38.0,0.0) +
                                      0.12*max(bus.get("PaCO2")-55.0,0.0)/25.0 - 0.12*alpha2_sed, 0.0, 1.0))

        concentration_updates = {
            "C_remifentanil_ng_mL": float(C_remi),
        }
        if not external_clo_pk:
            concentration_updates["C_clonidine_ng_mL"] = float(C_clo)
        if not external_mor_pk:
            concentration_updates["C_morphine_ng_mL"] = float(C_mor)
        if not external_fd_pk:
            concentration_updates.update({
                "C_fentanyl_ng_mL": float(C_fen),
                "C_dexmedetomidine_ng_mL": float(C_dex),
            })

        bus.update({
            **concentration_updates,
            "analgesia_score": analgesia,
            "sedation_score": sedation,
            "pain_score": pain,
            "stress_index": stress,
            "sympathetic_tone": sympathetic_tone,
            "delirium_risk": delirium,
            "withdrawal_risk": withdrawal,
            "sed_resp_mod": sed_resp_mod,
            "sed_VO2_mod": sed_VO2_mod,
            "sed_HR_mod": sed_HR_mod,
            "sed_SVR_mod": sed_SVR_mod,
            "opioid_resp_depression": opioid_resp,
            "opioid_analgesia_signal": float(np.clip(opioid_anal, 0.0, 1.0)),
            "gaba_sedation_signal": float(np.clip(gaba_sed, 0.0, 1.0)),
            "sedation_non_gaba_resp_signal": float(np.clip(non_gaba_resp_sedation, 0.0, 1.0)),
            "ketamine_analgesia_signal": float(np.clip(ket_anal, 0.0, 1.0)),
            "ketamine_dissociation_signal": float(np.clip(diss_sed, 0.0, 1.0)),
            "ketamine_resp_depression_signal": float(ketamine_resp_depression),
            "alpha2_resp_depression_signal": float(alpha2_resp_depression),
            "alpha2_sedation_signal": float(np.clip(alpha2_sed, 0.0, 1.0)),
            "alpha2_sympatholysis_signal": float(np.clip(alpha2_hemo, 0.0, 1.0)),
            "dexmedetomidine_sedation_signal": float(np.clip(hill(C_dex, self.params["dex_EC50_sed"], 0.70, 1.7), 0.0, 1.0)),
            "dexmedetomidine_sympatholysis_signal": float(np.clip(hill(C_dex, self.params["dex_EC50_hemo"], 0.22, 1.6), 0.0, 1.0)),
            "fentanyl_analgesia_signal": float(np.clip(E_fen_anal, 0.0, 1.0)),
            "fentanyl_resp_depression_signal": float(np.clip(E_fen_resp, 0.0, 1.0)),
            "remifentanil_analgesia_signal": float(np.clip(E_remi_anal, 0.0, 1.0)),
            "remifentanil_resp_depression_signal": float(np.clip(E_remi_resp, 0.0, 1.0)),
            "morphine_analgesia_signal": float(np.clip(E_mor_anal, 0.0, 1.0)),
            "morphine_resp_depression_signal": float(np.clip(E_mor_resp, 0.0, 1.0)),
        })
