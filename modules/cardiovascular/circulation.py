"""
Circulation Module
==================
Circuito Windkessel a 3 elementi per circolazione sistemica e polmonare.

Schema sistemico (3-element Windkessel):
  CO → [Zc] → [C_ao] // [R_p] → CVP

  dP_ao/dt = (CO_mL_s - P_ao/R_p) / C_ao

Schema polmonare analogo:
  CO_rv → [Zc_pul] → [C_pul] // [R_pv] → PAWP

Accoppiamento cardio-respiratorio:
  - Ppl (pressione pleurica dal modulo respiratorio) modifica il preload
    tramite pressione transmurale delle vene centrali
  - PVR aumenta con l'ipossia (vasocostrizione ipossica polmonare)
  - SVR modulata dal baroreflex (→ baroreflex.py) e dai farmaci
"""

from __future__ import annotations
import numpy as np
from typing import List

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


class CirculationModule(BaseModule):
    """
    Windkessel 3-elemento per circolo sistemico e polmonare.

    Parametri sistemici
    -------------------
    R_systemic : float    Resistenza periferica totale [mmHg·s/mL]
    C_aortic   : float    Compliance aortica [mL/mmHg]
    Zc_sys     : float    Impedenza caratteristica aortica [mmHg·s/mL]

    Parametri polmonari
    -------------------
    R_pulmonary : float   Resistenza vascolare polmonare [mmHg·s/mL]
    C_pulmonary : float   Compliance arterie polmonari [mL/mmHg]

    Vasocostrizione ipossica polmonare (HPV)
    ----------------------------------------
    HPV_gain : float      Aumento di PVR per deficit di PaO2 sotto 80 mmHg
    PaO2_HPV_thresh : float  Soglia HPV [mmHg]
    """

    DEFAULT_PARAMS = {
        # Sistemico — auto-consistenti: MAP=68, CO=3.85 L/min → R=68/64.2=1.06
        # τ_sys = R*C = 5s → C_ao = 5/1.06 = 4.72 mL/mmHg
        "R_systemic":       1.060,   # mmHg·s/mL
        "C_aortic":         4.72,    # mL/mmHg
        "Zc_sys":           0.05,    # mmHg·s/mL (impedenza caratteristica)

        # Polmonare — auto-consistenti: PAP=15, CO=3.85 → R=15/64.2=0.234
        # τ_pul = R*C = 8s → C_pul = 8/0.234 = 34.2 mL/mmHg
        "R_pulmonary":      0.234,   # mmHg·s/mL
        "C_pulmonary":      34.2,    # mL/mmHg
        "Zc_pul":           0.01,    # mmHg·s/mL

        # HPV (vasocostrizione ipossica polmonare)
        "HPV_gain":         0.008,   # relativo per mmHg sotto soglia
        "PaO2_HPV_thresh":  80.0,    # mmHg

        # VENE CENTRALI
        # CVP target=5 mmHg, CO_mL_s=64.2 → R_ven = 5/64.2 = 0.078
        "R_venous_sys":     0.078,   # mmHg·s/mL
        "C_venous_sys":     15.0,
        "Vunstressed_sys":  1200.0,
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="Circulation", params=merged)

        # Stato pressioni interne
        self._P_ao:  float = 65.0    # pressione aortica [mmHg]
        self._P_pul: float = 15.0    # pressione a. polmonare [mmHg]
        self._CVP:   float = 5.0     # CVP [mmHg]
        self._PAWP:  float = 8.0     # wedge pressure [mmHg]
        self._R_sys_base: float = self.params["R_systemic"]
        self._R_pul_base: float = self.params["R_pulmonary"]
        # v3.1 Step 4.43: smoothed effective vasoactive exposure.
        self._vaso_eff = {
            "norad": 0.0, "adrenaline": 0.0, "dopamine": 0.0,
            "milrinone": 0.0, "vasopressin": 0.0,
        }
        self._vaso_exposure_s = 0.0
        self._last_total_pressors = 0.0

    @property
    def input_keys(self) -> List[str]:
        return ["CO", "Ppl", "PaO2", "norad_mcg_kg_min",
                "milrinone_mcg_kg_min", "fluid_balance", "ino_PVR_mod",
                "PEEP", "Paw_current", "auto_PEEP", "auto_PEEP_obstructive", "dynamic_hyperinflation",
                "overdistension_index", "fluid_responsiveness", "crystalloid_preload_response", "crystalloid_MAP_support_mmHg",
                "sed_SVR_mod", "sympathetic_tone", "sepsis_SVR_mod", "sepsis_CO_mod",
                "steroid_SVR_mod", "shock_SVR_mod", "shock_preload_mod",
                "shock_sympathetic_tone", "shock_vasoplegia_index",
                "adrenaline_mcg_kg_min", "dopamine_mcg_kg_min", "vasopressin_mU_kg_min"]

    @property
    def output_keys(self) -> List[str]:
        return ["MAP", "PAP_mean", "CVP", "PAWP", "SVR", "PVR",
                "SAP", "DAP", "SBP", "DBP", "arterial_pulse_pressure",
                "arterial_pressure_source", "heart_lung_CO_mod", "venous_return_mod",
                "RV_afterload_index", "PEEP_hemodynamic_penalty",
                "vasoactive_SVR_mod", "vasoactive_CO_mod",
                "vasoactive_engine_revision", "vasoactive_alpha1_signal",
                "vasoactive_beta1_signal", "vasoactive_beta2_signal",
                "vasoactive_v1_signal", "vasoactive_pde3_signal",
                "vasoactive_effective_norad", "vasoactive_effective_adrenaline",
                "vasoactive_effective_dopamine", "vasoactive_effective_milrinone",
                "vasoactive_effective_vasopressin", "vasoactive_tachyphylaxis_index",
                "vasoactive_hysteresis_index", "vasoactive_interaction_index",
                "vasoactive_HR_mod", "vasoactive_inotropy_mod"]

    def initialize(self, bus: PhysiologicalBus) -> None:
        self._P_ao  = bus.get("MAP")
        self._P_pul = bus.get("PAP_mean")
        self._CVP   = bus.get("CVP")
        self._PAWP  = bus.get("PAWP")
        CO_mL_s = max(bus.get("CO") * 1000.0 / 60.0, 1.0)
        # Calibrazione scenario-specifica delle resistenze iniziali.
        # Evita che PHT/sepsi vengano normalizzate verso parametri sani di default.
        self._R_sys_base = float(np.clip((self._P_ao - self._CVP) / CO_mL_s, 0.20, 3.50))
        self._R_pul_base = float(np.clip((self._P_pul - self._PAWP) / CO_mL_s, 0.05, 2.00))
        self._vaso_eff = {
            "norad": 0.0, "adrenaline": 0.0, "dopamine": 0.0,
            "milrinone": 0.0, "vasopressin": 0.0,
        }
        self._vaso_exposure_s = 0.0
        self._last_total_pressors = 0.0

    def _HPV_factor(self, PaO2: float) -> float:
        """
        Vasocostrizione ipossica polmonare (von Euler-Liljestrand).
        PVR aumenta sotto la soglia HPV in modo lineare semplificato.
        """
        deficit = max(self.params["PaO2_HPV_thresh"] - PaO2, 0.0)
        return 1.0 + self.params["HPV_gain"] * deficit

    @staticmethod
    def _sat(dose: float, ec50: float) -> float:
        """Saturable educational dose-response helper [0-1]."""
        d = max(float(dose), 0.0)
        return d / (float(ec50) + d + 1e-9)

    def _advanced_vasoactive_effects(self, bus: PhysiologicalBus, dt: float) -> tuple[float, float, dict]:
        """Step 4.43 receptor-weighted vasoactive engine.

        This keeps the previous monotonic Step 3.3 contract, but adds:
        - receptor-weighted alpha1/beta1/beta2/V1/PDE3 signals,
        - first-order infusion hysteresis,
        - high-dose/high-exposure tachyphylaxis,
        - mixed pressor/inodilator interaction audit fields,
        - explicit HR and inotropy modifiers for downstream modules.
        """
        commanded = {
            "norad": max(float(bus.get("norad_mcg_kg_min")), 0.0),
            "adrenaline": max(float(bus.get("adrenaline_mcg_kg_min") if hasattr(bus.state, "adrenaline_mcg_kg_min") else 0.0), 0.0),
            "dopamine": max(float(bus.get("dopamine_mcg_kg_min") if hasattr(bus.state, "dopamine_mcg_kg_min") else 0.0), 0.0),
            "milrinone": max(float(bus.get("milrinone_mcg_kg_min")), 0.0),
            "vasopressin": max(float(bus.get("vasopressin_mU_kg_min") if hasattr(bus.state, "vasopressin_mU_kg_min") else 0.0), 0.0),
        }

        # Different clinical impression of onset/offset: catecholamines fast,
        # vasopressin and milrinone slower. This is qualitative hysteresis.
        tau = {"norad": 6.0, "adrenaline": 5.0, "dopamine": 10.0, "milrinone": 35.0, "vasopressin": 28.0}
        for key, dose in commanded.items():
            alpha = 1.0 - np.exp(-max(dt, 0.0) / tau[key])
            self._vaso_eff[key] += alpha * (dose - self._vaso_eff[key])

        total_pressor = commanded["norad"] / 0.18 + commanded["adrenaline"] / 0.18 + commanded["vasopressin"] / 0.06 + max(commanded["dopamine"] - 8.0, 0.0) / 8.0
        if total_pressor > 1.0:
            self._vaso_exposure_s += max(dt, 0.0) * min(total_pressor, 5.0)
        else:
            self._vaso_exposure_s *= float(np.exp(-max(dt, 0.0) / 180.0))
        tachy = float(np.clip((self._vaso_exposure_s - 240.0) / 900.0, 0.0, 0.32))

        n = self._vaso_eff["norad"]
        a = self._vaso_eff["adrenaline"]
        d = self._vaso_eff["dopamine"]
        m = self._vaso_eff["milrinone"]
        v = self._vaso_eff["vasopressin"]

        sat = self._sat
        # Receptor-weighted signals [0-1-ish], intentionally bounded.
        alpha1 = 0.78 * sat(n, 0.16) + 0.36 * sat(a, 0.14) + 0.22 * sat(max(d - 8.0, 0.0), 7.0)
        beta1 = 0.18 * sat(n, 0.22) + 0.68 * sat(a, 0.10) + 0.50 * sat(d, 7.0)
        beta2 = 0.42 * sat(a, 0.08) + 0.18 * sat(d, 5.0)
        v1 = 0.85 * sat(v, 0.055)
        pde3 = 0.90 * sat(m, 0.45)

        alpha1 *= (1.0 - tachy)
        beta1 *= (1.0 - 0.45 * tachy)
        v1 *= (1.0 - 0.25 * tachy)

        vasoplegia = float(np.clip(bus.get("shock_vasoplegia_index") if hasattr(bus.state, "shock_vasoplegia_index") else 0.0, 0.0, 1.0))
        vasopressin_rescue = 1.0 + 0.18 * vasoplegia * sat(v, 0.04)
        interaction = float(np.clip(0.32 * min(alpha1, beta1) + 0.45 * min(alpha1 + v1, pde3), 0.0, 1.0))

        SVR_mod = (1.0 + 1.45 * alpha1 + 0.95 * v1) * (1.0 - 0.24 * beta2) * (1.0 - 0.30 * pde3) * vasopressin_rescue
        CO_mod = (1.0 + 0.17 * pde3) * (1.0 + 0.05 * beta1) * (1.0 - 0.08 * max(alpha1 + v1 - 1.2, 0.0))
        HR_mod = 1.0 + 0.18 * beta1 - 0.04 * v1
        inotropy_mod = 1.0 + 0.28 * beta1 + 0.20 * pde3

        # Preserve previous qualitative behavior: dopamine low dose not alpha,
        # milrinone is not a primary vasopressor, high pressors raise MAP.
        SVR_mod = float(np.clip(SVR_mod, 0.20, 4.5))
        CO_mod = float(np.clip(CO_mod, 0.50, 1.65))
        HR_mod = float(np.clip(HR_mod, 0.75, 1.55))
        inotropy_mod = float(np.clip(inotropy_mod, 0.80, 1.70))
        hysteresis = float(np.clip(abs(total_pressor - self._last_total_pressors) / 4.0, 0.0, 1.0))
        self._last_total_pressors = total_pressor

        audit = {
            "vasoactive_engine_revision": 443,
            "vasoactive_alpha1_signal": float(np.clip(alpha1, 0.0, 1.6)),
            "vasoactive_beta1_signal": float(np.clip(beta1, 0.0, 1.4)),
            "vasoactive_beta2_signal": float(np.clip(beta2, 0.0, 1.0)),
            "vasoactive_v1_signal": float(np.clip(v1, 0.0, 1.0)),
            "vasoactive_pde3_signal": float(np.clip(pde3, 0.0, 1.0)),
            "vasoactive_effective_norad": float(n),
            "vasoactive_effective_adrenaline": float(a),
            "vasoactive_effective_dopamine": float(d),
            "vasoactive_effective_milrinone": float(m),
            "vasoactive_effective_vasopressin": float(v),
            "vasoactive_tachyphylaxis_index": float(tachy),
            "vasoactive_hysteresis_index": hysteresis,
            "vasoactive_interaction_index": interaction,
            "vasoactive_HR_mod": HR_mod,
            "vasoactive_inotropy_mod": inotropy_mod,
        }
        return SVR_mod, CO_mod, audit

    def _drug_effects(self, bus: PhysiologicalBus, dt: float = 0.0) -> tuple[float, float, dict]:
        """Primary vasoactive effects with Step 4.43 advanced audit fields."""
        T_core = float(bus.get("T_core"))
        SVR_sepsis = 1.0 - 0.08 * max(T_core - 38.0, 0.0)
        SVR_sepsis = float(np.clip(SVR_sepsis, 0.30, 1.0))
        SVR_mod, CO_mod, audit = self._advanced_vasoactive_effects(bus, dt)
        return float(np.clip(SVR_sepsis * SVR_mod, 0.20, 4.5)), float(np.clip(CO_mod, 0.5, 1.65)), audit

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        CO    = bus.get("CO")          # L/min
        Ppl   = bus.get("Ppl")        # cmH2O
        PaO2  = bus.get("PaO2")
        PEEP  = bus.get("PEEP") if hasattr(bus.state, "PEEP") else 5.0
        Paw_current = bus.get("Paw_current") if hasattr(bus.state, "Paw_current") else bus.get("Paw")
        overdist = bus.get("overdistension_index") if hasattr(bus.state, "overdistension_index") else 0.0
        auto_peep = max(bus.get("auto_PEEP") if hasattr(bus.state, "auto_PEEP") else 0.0,
                        bus.get("auto_PEEP_obstructive") if hasattr(bus.state, "auto_PEEP_obstructive") else 0.0)
        dyn_hyper = bus.get("dynamic_hyperinflation") if hasattr(bus.state, "dynamic_hyperinflation") else 0.0
        fluid_resp = bus.get("fluid_responsiveness") if hasattr(bus.state, "fluid_responsiveness") else 0.6

        # Effetti farmacologici (combinati: Circulation + PK/PD module)
        SVR_mod_circ, CO_mod, vaso_audit = self._drug_effects(bus, dt)
        # drug_SVR_mod da PharmacologyModule (sedativi/vasodilatatori non vasoattivi).
        # Vasoactive SVR/MAP tone is now kept in SVR_mod_circ to avoid double-counting.
        bus.update({
            "vasoactive_SVR_mod": float(SVR_mod_circ),
            "vasoactive_CO_mod": float(CO_mod),
            **vaso_audit,
        })
        # drug_SVR_mod da PharmacologyModule (propofol, midazolam)
        SVR_mod_pharma = bus.get("drug_SVR_mod")
        sed_SVR_mod = bus.get("sed_SVR_mod") if hasattr(bus.state, "sed_SVR_mod") else 1.0
        sympathetic_tone = bus.get("sympathetic_tone") if hasattr(bus.state, "sympathetic_tone") else 1.0
        sepsis_SVR_mod = bus.get("sepsis_SVR_mod") if hasattr(bus.state, "sepsis_SVR_mod") else 1.0
        sepsis_CO_mod = bus.get("sepsis_CO_mod") if hasattr(bus.state, "sepsis_CO_mod") else 1.0
        endocrine_SVR_mod = bus.get("endocrine_SVR_mod") if hasattr(bus.state, "endocrine_SVR_mod") else 1.0
        steroid_SVR_mod = bus.get("steroid_SVR_mod") if hasattr(bus.state, "steroid_SVR_mod") else 1.0
        shock_SVR_mod = bus.get("shock_SVR_mod") if hasattr(bus.state, "shock_SVR_mod") else 1.0
        shock_preload_mod = bus.get("shock_preload_mod") if hasattr(bus.state, "shock_preload_mod") else 1.0
        shock_sympathetic = bus.get("shock_sympathetic_tone") if hasattr(bus.state, "shock_sympathetic_tone") else 1.0
        SVR_mod = SVR_mod_circ * SVR_mod_pharma * sepsis_SVR_mod * endocrine_SVR_mod * steroid_SVR_mod * shock_SVR_mod * (0.92 + 0.08 * sed_SVR_mod) * (0.94 + 0.06 * sympathetic_tone * shock_sympathetic)

        # drug_MAP_mod (ketamina +, propofol -)
        MAP_drug_mod = bus.get("drug_MAP_mod")

        # Resistenza periferica effettiva
        R_sys = self._R_sys_base * SVR_mod

        # Heart-lung interaction v0.11. PEEP/Paw alte riducono il ritorno venoso;
        # overdistension e ipossia aumentano il carico RV/PVR. L'effetto è
        # qualitativo e saturabile, non un modello emodinamico closed-loop completo.
        mean_airway_pressure = 0.65 * float(PEEP + 0.5 * auto_peep) + 0.35 * float(Paw_current)
        peep_penalty = float(np.clip((mean_airway_pressure - 10.0) / 22.0 + 0.18 * dyn_hyper, 0.0, 0.75))
        venous_return_mod = float(np.clip(1.0 - peep_penalty * (1.0 - 0.35 * fluid_resp), 0.55, 1.10))
        hypoxic_rv = float(np.clip((80.0 - PaO2) / 60.0, 0.0, 1.0))
        RV_afterload_index = float(np.clip(0.32 * overdist + 0.30 * hypoxic_rv + 0.20 * max(float(PEEP + auto_peep)-8.0,0.0)/18.0 + 0.18 * dyn_hyper, 0.0, 1.0))
        venous_return_mod *= float(np.clip(shock_preload_mod, 0.25, 1.15))
        heart_lung_CO_mod = float(np.clip(venous_return_mod * (1.0 - 0.25 * RV_afterload_index), 0.35, 1.10))

        # CO effettiva con farmaci inotropi e interazione cuore-polmone
        crystalloid_preload = float(np.clip(getattr(bus.state, "crystalloid_preload_response", 0.0), 0.0, 1.0))
        crystalloid_co_mod = 1.0 + 0.10 * crystalloid_preload
        CO_eff = CO * CO_mod * sepsis_CO_mod * heart_lung_CO_mod * crystalloid_co_mod

        # Conversione Ppl cmH2O → mmHg
        Ppl_mmHg = Ppl * 0.7355

        CO_mL_s = CO * 1000.0 / 60.0
        CO_mL_s_eff = CO_eff * 1000.0 / 60.0

        # --- CIRCOLO SISTEMICO (Windkessel 3-elem, Euler implicito) ---
        # MAP_drug_mod agisce sulla resistenza target (stato stazionario),
        # NON come moltiplicatore istantaneo su P_ao (che divergerebbe).
        # R_eff = R_sys * MAP_drug_mod → a parità di CO, MAP varia nello stesso
        # verso del modificatore: >1 aumenta MAP, <1 riduce MAP.
        R_sys_eff = R_sys * MAP_drug_mod
        C_ao = self.params["C_aortic"]
        tau_sys = R_sys_eff * C_ao
        self._P_ao = (self._P_ao + CO_mL_s_eff * dt / C_ao) / (1.0 + dt / tau_sys)
        self._P_ao = float(np.clip(self._P_ao, 25.0, 200.0))

        # CVP: R_venous * CO_reale + correzione da overload/ipovolemia
        R_ven = self.params["R_venous_sys"]
        CVP_target = float(np.clip(CO_mL_s * R_ven, 1.0, 18.0))
        # Accoppiamento respiratorio: Ppl aumenta CVP apparente
        CVP_tm = CVP_target + Ppl_mmHg * 0.3
        # Correzione persistente da bilancio idrico (FluidBalance la calcola)
        fluid_corr = bus.get("fluid_CVP_correction") \
                     if hasattr(bus.state, "fluid_CVP_correction") else 0.0
        self._CVP = float(np.clip(CVP_tm + fluid_corr, 0.5, 20.0))

        # PAWP: tipicamente CVP + 3-5 mmHg
        self._PAWP = float(np.clip(self._CVP * 1.3 + 2.0, 2.0, 28.0))

        # --- CIRCOLO POLMONARE (Euler implicito) ---
        HPV = self._HPV_factor(PaO2)
        ino_mod = bus.get("ino_PVR_mod") if hasattr(bus.state, "ino_PVR_mod") else 1.0
        # PVR aumenta anche con overdistension/dynamic pulmonary vascular compression.
        mech_pvr_mod = 1.0 + 0.55 * RV_afterload_index
        R_pul = self._R_pul_base * HPV * ino_mod * mech_pvr_mod
        C_pul = self.params["C_pulmonary"]
        tau_pul = R_pul * C_pul
        self._P_pul = (self._P_pul + CO_mL_s_eff * dt / C_pul) / (1.0 + dt / tau_pul)
        self._P_pul = float(np.clip(self._P_pul, 5.0, 80.0))

        # Parametri derivati per il Bus. v3.1 Step 4.0A: expose
        # bedside SBP/DBP aliases from the circulation model so the ABP
        # waveform does not need cosmetic MAP±constants.  This remains an
        # educational pressure-envelope extracted from the Windkessel state,
        # stroke volume and effective arterial load, not an invasive monitor.
        crystalloid_map_support = float(np.clip(getattr(bus.state, "crystalloid_MAP_support_mmHg", 0.0), 0.0, 10.0))
        MAP_out = float(np.clip(self._P_ao + crystalloid_map_support, 25.0, 210.0))
        arterial_load = max(R_sys_eff, 0.05)
        pulse_pressure = float(np.clip((bus.get("SV") * arterial_load) / max(C_ao, 0.1) * 1.8, 8.0, 85.0))
        SAP = MAP_out + 0.67 * pulse_pressure
        DAP = MAP_out - 0.33 * pulse_pressure
        SAP = float(np.clip(SAP, DAP + 5.0, 220.0))
        DAP = float(np.clip(DAP, 15.0, SAP - 5.0))
        # Preserve MAP≈DBP+1/3PP after clipping when possible.
        pulse_pressure = float(max(SAP - DAP, 5.0))

        # SVR [dyne·s/cm5] = R_sys [mmHg·s/mL] × 80
        SVR_dyn = R_sys * 80.0
        # PVR [dyne·s/cm5]
        PVR_dyn = R_pul * 80.0

        bus.update({
            "MAP":      MAP_out,
            "PAP_mean": float(self._P_pul),
            "CVP":      float(self._CVP),
            "PAWP":     float(self._PAWP),
            "SVR":      float(SVR_dyn),
            "PVR":      float(PVR_dyn),
            "SAP":      float(SAP),
            "DAP":      float(DAP),
            "SBP":      float(SAP),
            "DBP":      float(DAP),
            "arterial_pulse_pressure": float(pulse_pressure),
            "arterial_pressure_source": "circulation_windkessel_envelope",
            "heart_lung_CO_mod": float(heart_lung_CO_mod),
            "venous_return_mod": float(venous_return_mod),
            "RV_afterload_index": float(RV_afterload_index),
            "PEEP_hemodynamic_penalty": float(peep_penalty),
            "crystalloid_CO_mod": float(crystalloid_co_mod),
        })
