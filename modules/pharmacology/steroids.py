"""
Steroids Module
===============
PK/PD per corticosteroidi in PICU.

Farmaci implementati:
  Idrocortisone (idrocortisone_mg_kg_h):
    PK: monocompartimentale, t1/2 = 90 min
    PD onset lento (effetto genomico): τ_PD = 90 min
    Effetti:
      SVR: +20% (up-regulation recettori adrenergici α1)
      SIRS_factor: -15% (anti-infiammazione)
      Glicemia: +2 mmol/L a dose piena (gluconeogenesi)

  Desametasone (dexamethasone_mg_kg_h):
    PK: monocompartimentale, t1/2 = 200 min
    PD onset: τ_PD = 120 min
    Effetti:
      SIRS_factor: -25% (più potente anti-infiammatorio)
      Glicemia: +3 mmol/L
      ICP: -10% (riduzione edema cerebrale vasogenico, con τ_ICP = 6h)
      Effetto vasopressore minore rispetto a idrocortisone

Output:
  C_hydrocort_mcg_mL   : concentrazione idrocortisone plasmatica
  C_dexa_ng_mL         : concentrazione desametasone plasmatica
  steroid_SVR_mod      : moltiplicatore SVR (>1 = vasocostrizione)
  steroid_SIRS_mod     : moltiplicatore SIRS (< 1 = anti-infiammazione)
  steroid_glucose_add  : aggiunta assoluta alla glicemia [mmol/L]
  steroid_ICP_mod      : moltiplicatore ICP (dexa → riduzione edema)
  *_signal             : segnali audit [0-1] già filtrati dal ritardo PD
"""

from __future__ import annotations
import numpy as np
from typing import List

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


def _hill(C: float, EC50: float, Emax: float, n: float = 1.0) -> float:
    if C <= 0:
        return 0.0
    Cn = C ** n
    return float(Emax * Cn / (EC50 ** n + Cn))


class SteroidsModule(BaseModule):
    """
    Corticosteroidi: idrocortisone + desametasone.

    Parametri PK (scalati per peso al momento di initialize)
    ---------------------------------------------------------
    hc_Vd_per_kg   : float   [L/kg] Vd idrocortisone (0.30)
    hc_k_elim      : float   [s-1]  costante eliminazione (0.000128 → t1/2=90 min)
    dexa_Vd_per_kg : float   [L/kg] Vd desametasone (0.82)
    dexa_k_elim    : float   [s-1]  (0.0000578 → t1/2=200 min)
    tau_PD_hc_s    : float   [s]    onset PD idrocortisone (5400 = 90 min)
    tau_PD_dexa_s  : float   [s]    onset PD desametasone (7200 = 120 min)

    Parametri PD
    ------------
    hc_EC50_mcg_mL : float   EC50 effetti idrocortisone [mcg/mL] (10.0)
    hc_Emax_SVR    : float   Aumento max SVR (0.25)
    hc_Emax_SIRS   : float   Riduzione max SIRS_factor (0.15)
    hc_Emax_gluc   : float   Aumento max glicemia [mmol/L] (2.5)
    dexa_EC50_ng_mL: float   EC50 desametasone (50.0 ng/mL)
    dexa_Emax_SIRS : float   Riduzione max SIRS (0.25)
    dexa_Emax_gluc : float   Aumento max glicemia (3.5)
    dexa_Emax_ICP  : float   Riduzione max ICP (0.15 = 15%)
    """

    DEFAULT_PARAMS = {
        # PK Idrocortisone
        "hc_Vd_per_kg":    0.30,
        "hc_k_elim":       0.000128,   # s-1 (t1/2 ≈ 90 min)
        "tau_PD_hc_s":     5400.0,     # s = 90 min
        # PK Desametasone
        "dexa_Vd_per_kg":  0.82,
        "dexa_k_elim":     0.0000578,  # s-1 (t1/2 ≈ 200 min)
        "tau_PD_dexa_s":   7200.0,     # s = 120 min
        # PD Idrocortisone
        "hc_EC50_mcg_mL":  10.0,
        "hc_Emax_SVR":      0.25,
        "hc_Emax_SIRS":     0.15,
        "hc_Emax_gluc":     2.5,
        "hc_n":             1.2,
        # PD Desametasone
        "dexa_EC50_ng_mL": 50.0,
        "dexa_Emax_SIRS":   0.25,
        "dexa_Emax_gluc":   3.5,
        "dexa_Emax_ICP":    0.15,
        "dexa_n":           1.0,
        # Scaling peso
        "weight_kg":       20.0,
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="Steroids", params=merged)

        # Stato PK
        self._C_hc:   float = 0.0   # mcg/mL = mg/L
        self._C_dexa: float = 0.0   # ng/mL

        # Effetti PD (filtrati con τ_PD)
        self._E_hc_SVR:  float = 0.0
        self._E_hc_SIRS: float = 0.0
        self._E_hc_gluc: float = 0.0
        self._E_dexa_SIRS: float = 0.0
        self._E_dexa_gluc: float = 0.0
        self._E_dexa_ICP:  float = 0.0

    @property
    def input_keys(self) -> List[str]:
        return ["hydrocortisone_mg_kg_h", "dexamethasone_mcg_kg_h"]

    @property
    def output_keys(self) -> List[str]:
        return ["C_hydrocort_mcg_mL", "C_dexa_ng_mL",
                "steroid_SVR_mod", "steroid_SIRS_mod",
                "steroid_glucose_add", "steroid_ICP_mod",
                "hydrocortisone_adrenal_support_signal",
                "hydrocortisone_vasopressor_sensitization_signal",
                "hydrocortisone_antiinflammatory_signal",
                "dexamethasone_antiinflammatory_signal",
                "dexamethasone_ICP_edema_signal",
                "steroid_glucose_signal", "steroid_delayed_effect_signal"]

    def initialize(self, bus: PhysiologicalBus) -> None:
        self._C_hc   = 0.0
        self._C_dexa = 0.0
        bus.update({
            "C_hydrocort_mcg_mL":  0.0,
            "C_dexa_ng_mL":        0.0,
            "steroid_SVR_mod":     1.0,
            "steroid_SIRS_mod":    1.0,
            "steroid_glucose_add": 0.0,
            "steroid_ICP_mod":     1.0,
            "hydrocortisone_adrenal_support_signal": 0.0,
            "hydrocortisone_vasopressor_sensitization_signal": 0.0,
            "hydrocortisone_antiinflammatory_signal": 0.0,
            "dexamethasone_antiinflammatory_signal": 0.0,
            "dexamethasone_ICP_edema_signal": 0.0,
            "steroid_glucose_signal": 0.0,
            "steroid_delayed_effect_signal": 0.0,
        })

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        wt = self.params["weight_kg"]

        # --- PK idrocortisone ---
        dose_hc = bus.get("hydrocortisone_mg_kg_h") * wt / 60.0   # mg/min
        Vd_hc   = self.params["hc_Vd_per_kg"] * wt                # L
        rate_hc = dose_hc / 60.0 / Vd_hc                          # mg/L/s = mcg/mL/s
        dC_hc   = rate_hc - self.params["hc_k_elim"] * self._C_hc
        self._C_hc = max(self._C_hc + dC_hc * dt, 0.0)

        # --- PK desametasone ---
        dose_dexa = bus.get("dexamethasone_mcg_kg_h") * wt / 1000.0 / 60.0  # mg/min
        Vd_dexa   = self.params["dexa_Vd_per_kg"] * wt
        # C in ng/mL: dose in mcg/min, Vd in L → C in mcg/L = ng/mL ×1000... 
        # Meglio tenere tutto coerente: C_dexa in ng/mL
        # dose_dexa in mcg/min; Vd in L; 1 mcg/L = 1 ng/mL × 1000 → NO
        # 1 mg/L = 1000 mcg/L = 1e6 ng/mL; 1 mcg/L = 1000 ng/mL
        dose_dexa_mcg_min = bus.get("dexamethasone_mcg_kg_h") * wt / 60.0  # mcg/min
        rate_dexa = dose_dexa_mcg_min / 60.0 / (Vd_dexa * 1000.0)  # mcg/mL/s = ng/mL × 0.001/s
        # Meglio: C in mcg/L = ng/mL
        rate_dexa_ngmL = dose_dexa_mcg_min * 1000.0 / 60.0 / (Vd_dexa * 1000.0)  # ng/mL/s
        dC_dexa = rate_dexa_ngmL - self.params["dexa_k_elim"] * self._C_dexa
        self._C_dexa = max(self._C_dexa + dC_dexa * dt, 0.0)

        # --- Effetti PD target (Hill istantaneo) ---
        E_hc_SVR_tgt  = _hill(self._C_hc,   self.params["hc_EC50_mcg_mL"],
                               self.params["hc_Emax_SVR"],  self.params["hc_n"])
        E_hc_SIRS_tgt = _hill(self._C_hc,   self.params["hc_EC50_mcg_mL"],
                               self.params["hc_Emax_SIRS"], self.params["hc_n"])
        E_hc_gluc_tgt = _hill(self._C_hc,   self.params["hc_EC50_mcg_mL"],
                               self.params["hc_Emax_gluc"], self.params["hc_n"])

        E_dexa_SIRS_tgt = _hill(self._C_dexa, self.params["dexa_EC50_ng_mL"],
                                 self.params["dexa_Emax_SIRS"], self.params["dexa_n"])
        E_dexa_gluc_tgt = _hill(self._C_dexa, self.params["dexa_EC50_ng_mL"],
                                 self.params["dexa_Emax_gluc"], self.params["dexa_n"])
        E_dexa_ICP_tgt  = _hill(self._C_dexa, self.params["dexa_EC50_ng_mL"],
                                 self.params["dexa_Emax_ICP"],  self.params["dexa_n"])

        # --- Filtro PD (effetto genomico lento) ---
        alpha_hc   = 1.0 - np.exp(-dt / self.params["tau_PD_hc_s"])
        alpha_dexa = 1.0 - np.exp(-dt / self.params["tau_PD_dexa_s"])

        self._E_hc_SVR   += alpha_hc   * (E_hc_SVR_tgt   - self._E_hc_SVR)
        self._E_hc_SIRS  += alpha_hc   * (E_hc_SIRS_tgt  - self._E_hc_SIRS)
        self._E_hc_gluc  += alpha_hc   * (E_hc_gluc_tgt  - self._E_hc_gluc)
        self._E_dexa_SIRS += alpha_dexa * (E_dexa_SIRS_tgt - self._E_dexa_SIRS)
        self._E_dexa_gluc += alpha_dexa * (E_dexa_gluc_tgt - self._E_dexa_gluc)
        self._E_dexa_ICP  += alpha_dexa * (E_dexa_ICP_tgt  - self._E_dexa_ICP)

        # --- Composizione modificatori ---
        SVR_mod   = 1.0 + self._E_hc_SVR
        SIRS_mod  = 1.0 - self._E_hc_SIRS - self._E_dexa_SIRS
        gluc_add  = self._E_hc_gluc + self._E_dexa_gluc
        ICP_mod   = 1.0 - self._E_dexa_ICP

        # Audit/contract signals: all are based on delayed PD effects, not on
        # the raw infusion command.  Downstream modules must consume these
        # slow signals when they need glucocorticoid/mineralocorticoid activity.
        hc_vaso_sig = self._E_hc_SVR / max(float(self.params["hc_Emax_SVR"]), 1e-9)
        hc_anti_sig = self._E_hc_SIRS / max(float(self.params["hc_Emax_SIRS"]), 1e-9)
        dexa_anti_sig = self._E_dexa_SIRS / max(float(self.params["dexa_Emax_SIRS"]), 1e-9)
        dexa_icp_sig = self._E_dexa_ICP / max(float(self.params["dexa_Emax_ICP"]), 1e-9)
        gluc_sig = gluc_add / max(float(self.params["hc_Emax_gluc"] + self.params["dexa_Emax_gluc"]), 1e-9)
        delayed_sig = max(hc_vaso_sig, hc_anti_sig, dexa_anti_sig, dexa_icp_sig, gluc_sig)

        bus.update({
            "C_hydrocort_mcg_mL":  float(self._C_hc),
            "C_dexa_ng_mL":        float(self._C_dexa),
            "steroid_SVR_mod":     float(np.clip(SVR_mod,  0.5, 2.0)),
            "steroid_SIRS_mod":    float(np.clip(SIRS_mod, 0.4, 1.5)),
            "steroid_glucose_add": float(np.clip(gluc_add, 0.0, 6.0)),
            "steroid_ICP_mod":     float(np.clip(ICP_mod,  0.7, 1.0)),
            "hydrocortisone_adrenal_support_signal": float(np.clip(hc_vaso_sig, 0.0, 1.0)),
            "hydrocortisone_vasopressor_sensitization_signal": float(np.clip(hc_vaso_sig, 0.0, 1.0)),
            "hydrocortisone_antiinflammatory_signal": float(np.clip(hc_anti_sig, 0.0, 1.0)),
            "dexamethasone_antiinflammatory_signal": float(np.clip(dexa_anti_sig, 0.0, 1.0)),
            "dexamethasone_ICP_edema_signal": float(np.clip(dexa_icp_sig, 0.0, 1.0)),
            "steroid_glucose_signal": float(np.clip(gluc_sig, 0.0, 1.0)),
            "steroid_delayed_effect_signal": float(np.clip(delayed_sig, 0.0, 1.0)),
        })
