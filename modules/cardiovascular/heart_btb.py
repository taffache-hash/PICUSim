"""
Heart Beat-to-Beat Model (v2 — Waveform Analitica Stabile)
============================================================
Modello cardiaco beat-to-beat con forme d'onda analitiche.

Strategia numericamente stabile (Ottesen 2004, Heldt 2002):
  - ESV determinato dalla ESPVR: E_max * (ESV - V0) = P_es ≈ DAP
  - SV = EDV - ESV  (punto fisso stabile)
  - Forme d'onda P_lv(t), V_lv(t) calcolate ANALITICAMENTE da E(t) e V(t)
  - Q_ao(t): profilo sinusoidale scalato su SV e T_eject
  - Valvole: timing esplicito per fase del ciclo (no diodo iterativo instabile)

4 fasi esplicite:
  IVC  : V = EDV, P_lv sale (E aumenta, V costante)
  EJECT: V scende EDV→ESV (profilo sin²), P_lv ≈ MAP
  IVR  : V = ESV, P_lv scende (E decresce esponenzialmente)
  FILL : V sale ESV→EDV (profilo sin²), P_lv ≈ LVEDP bassa

Metriche beat-to-beat (calcolate ad ogni fine sistole):
  dP/dt_max, dP/dt_min, Tau_relax, LVEDP, SW_lv, PVA_lv, MVO2_lv
  Ea (elastanza arteriosa), VAC (ventricular-arterial coupling)

Waveform di output (alta risoluzione temporale):
  P_lv_t, V_lv_t, Q_ao_t, P_rv_t, V_rv_t, Q_pul_t
  P_la, P_ra, cardiac_phase
"""

from __future__ import annotations
import numpy as np
from typing import List
from enum import Enum, auto

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


class CardiacPhase(Enum):
    IVC   = "IVC"
    EJECT = "EJECT"
    IVR   = "IVR"
    FILL  = "FILL"


class HeartBTBModule(BaseModule):
    """
    Cuore beat-to-beat con waveform analitiche.

    Parametri (default bambino 20 kg, 5 anni, HR=105, MAP=68)
    ----------------------------------------------------------
    Emax_lv  : 5.10 mmHg/mL   — slope ESPVR
    Emin_lv  : 0.08 mmHg/mL   — elastanza diastolica
    V0_lv    : 5.0  mL         — volume non estraibile
    EDV0_lv  : 55.0 mL         — EDV di riferimento (F-S)
    Ts_frac  : 0.38             — sistole/T_ciclo
    T_ivc_frac: 0.06            — IVC/T_ciclo
    T_ivr_frac: 0.10            — IVR/T_ciclo
    Emax_rv  : 0.978, Emin_rv: 0.03, V0_rv: 8.0, EDV0_rv: 60.0
    FS_gain  : 0.40             — Frank-Starling gain
    MVO2_efficiency: 0.25
    """

    DEFAULT_PARAMS = {
        # LV
        "Emax_lv":     5.10,
        "Emin_lv":     0.08,
        "V0_lv":       5.0,
        "EDV0_lv":    55.0,
        "Ts_frac":     0.38,
        "T_ivc_frac":  0.06,
        "T_ivr_frac":  0.10,
        # RV
        "Emax_rv":     0.978,
        "Emin_rv":     0.03,
        "V0_rv":       8.0,
        "EDV0_rv":    60.0,
        # Frank-Starling
        "FS_gain":     0.40,
        # Atri
        "C_la":        8.0,    # mL/mmHg
        "C_ra":       10.0,
        "V0_la":      20.0,    # mL
        "V0_ra":      25.0,
        # MVO2
        "MVO2_efficiency": 0.25,
        "weight_kg":  20.0,
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="HeartBTB", params=merged)

        # Stato ciclo
        self._T_cycle:  float = 0.571
        self._t_cycle:  float = 0.0

        # Volumi e SV
        self._EDV_lv:   float = 55.0
        self._ESV_lv:   float = 18.3
        self._SV_lv:    float = 36.7
        self._EDV_rv:   float = 60.0
        self._ESV_rv:   float = 25.0
        self._SV_rv:    float = 35.0

        # Atri
        self._V_la:     float = 30.0
        self._V_ra:     float = 35.0

        # Metriche ciclo
        self._dPdt_max:  float = 0.0
        self._dPdt_min:  float = 0.0
        self._Tau_relax: float = 0.05
        self._LVEDP:     float = 4.0
        self._SW_lv:     float = 0.0
        self._PVA_lv:    float = 0.0
        self._MVO2_lv:   float = 8.0
        self._Ea:        float = 1.7
        self._VAC:       float = 1.0

        # Forma d'onda corrente
        self._P_lv:    float = 4.0
        self._V_lv:    float = 55.0
        self._P_rv:    float = 2.0
        self._V_rv:    float = 60.0
        self._Q_ao:    float = 0.0
        self._Q_pul:   float = 0.0
        self._Q_mit:   float = 0.0
        self._P_la:    float = 8.0
        self._P_ra:    float = 3.0
        self._beat_count: int = 0

    @property
    def input_keys(self) -> List[str]:
        return ["HR", "MAP", "CVP", "PAP_mean", "PAWP", "Ppl",
                "drug_HR_mod", "fluid_CVP_correction",
                "heart_lung_CO_mod", "venous_return_mod", "fluid_responsiveness"]

    @property
    def output_keys(self) -> List[str]:
        return [
            "P_lv_t", "P_rv_t", "V_lv_t", "V_rv_t",
            "cardiac_phase", "P_la", "P_ra",
            "Q_ao", "Q_pul", "Q_mitral",
            "dPdt_max", "dPdt_min", "Tau_relax",
            "LVEDP", "LVESV", "Ea", "VAC",
            "SW_lv", "PVA_lv", "MVO2_lv",
            "CO", "SV", "EDV_lv", "ESV_lv", "EF_lv",
            "SAP_btb", "DAP_btb",
        ]

    # ------------------------------------------------------------------
    # Elastanza tempo-variante
    # ------------------------------------------------------------------

    def _elastance_lv(self, t: float, T: float) -> float:
        Emax = self._lv_Emax_eff
        Emin = self.params["Emin_lv"]
        Ts   = T * self.params["Ts_frac"]
        T_ivr_start = Ts
        T_ivr_end   = Ts + T * self.params["T_ivr_frac"]

        if t <= Ts:
            return Emin + (Emax - Emin) / 2.0 * (1.0 - np.cos(np.pi * t / Ts))
        elif t <= T_ivr_end:
            tau_ivr = T * self.params["T_ivr_frac"] / 3.0
            return Emin + (Emax - Emin) * np.exp(-(t - T_ivr_start) / tau_ivr)
        else:
            return float(Emin)

    def _elastance_rv(self, t: float, T: float) -> float:
        Emax = self._rv_Emax_eff
        Emin = self.params["Emin_rv"]
        Ts   = T * self.params["Ts_frac"]
        T_ivr_end = Ts + T * self.params["T_ivr_frac"]
        if t <= Ts:
            return Emin + (Emax - Emin) / 2.0 * (1.0 - np.cos(np.pi * t / Ts))
        elif t <= T_ivr_end:
            tau_ivr = T * self.params["T_ivr_frac"] / 3.0
            return Emin + (Emax - Emin) * np.exp(-(t - Ts) / tau_ivr)
        else:
            return float(Emin)

    # ------------------------------------------------------------------
    # Forme d'onda analitiche
    # ------------------------------------------------------------------

    def _V_lv_waveform(self, t: float, T: float) -> float:
        """Volume LV in funzione del tempo nel ciclo [mL]."""
        Ts    = T * self.params["Ts_frac"]
        T_ivc = T * self.params["T_ivc_frac"]
        T_ivr = T * self.params["T_ivr_frac"]
        T_eject = Ts - T_ivc
        T_fill  = T - Ts - T_ivr

        if t <= T_ivc:
            return float(self._EDV_lv)   # IVC: V costante
        elif t <= Ts:
            frac = (t - T_ivc) / (T_eject + 1e-9)
            return float(self._EDV_lv - self._SV_lv * np.sin(np.pi * frac / 2.0) ** 2)
        elif t <= Ts + T_ivr:
            return float(self._ESV_lv)   # IVR: V costante
        else:
            frac = (t - Ts - T_ivr) / (T_fill + 1e-9)
            return float(self._ESV_lv + self._SV_lv * np.sin(np.pi * frac / 2.0) ** 2)

    def _V_rv_waveform(self, t: float, T: float) -> float:
        """Volume RV analogo al LV."""
        Ts    = T * self.params["Ts_frac"]
        T_ivc = T * self.params["T_ivc_frac"]
        T_ivr = T * self.params["T_ivr_frac"]
        T_eject = Ts - T_ivc
        T_fill  = T - Ts - T_ivr
        if t <= T_ivc:
            return float(self._EDV_rv)
        elif t <= Ts:
            frac = (t - T_ivc) / (T_eject + 1e-9)
            return float(self._EDV_rv - self._SV_rv * np.sin(np.pi * frac / 2.0) ** 2)
        elif t <= Ts + T_ivr:
            return float(self._ESV_rv)
        else:
            frac = (t - Ts - T_ivr) / (T_fill + 1e-9)
            return float(self._ESV_rv + self._SV_rv * np.sin(np.pi * frac / 2.0) ** 2)

    def _Q_ao_waveform(self, t: float, T: float) -> float:
        """Flusso aortico [mL/s] — profilo sinusoidale durante eiezione."""
        Ts    = T * self.params["Ts_frac"]
        T_ivc = T * self.params["T_ivc_frac"]
        T_eject = Ts - T_ivc
        if T_ivc < t <= Ts:
            frac = (t - T_ivc) / T_eject
            Q_peak = np.pi / 2.0 * self._SV_lv / T_eject
            return float(Q_peak * np.sin(np.pi * frac))
        return 0.0

    # ------------------------------------------------------------------
    # Frank-Starling
    # ------------------------------------------------------------------

    def _FS_Emax(self, Emax_0: float, V_ed: float, V_ed0: float) -> float:
        gain = self.params["FS_gain"]
        mod  = 1.0 + gain * (V_ed / (V_ed0 + 1e-6) - 1.0)
        return float(Emax_0 * np.clip(mod, 0.3, 2.0))

    def _edv_bounds(self, side: str = "lv") -> tuple[float, float]:
        edv0 = float(self.params["EDV0_lv" if side == "lv" else "EDV0_rv"])
        return max(0.35 * edv0, 0.5), max(1.85 * edv0, 1.0)

    def _esv_lower(self, side: str = "lv") -> float:
        v0 = float(self.params["V0_lv" if side == "lv" else "V0_rv"])
        edv0 = float(self.params["EDV0_lv" if side == "lv" else "EDV0_rv"])
        return max(v0 * 1.03, 0.04 * edv0, 0.15)

    @staticmethod
    def _diastolic_pressure_estimate(MAP: float) -> float:
        return float(max(MAP * 0.73, 12.0))

    # ------------------------------------------------------------------
    # Initialize
    # ------------------------------------------------------------------

    def initialize(self, bus: PhysiologicalBus) -> None:
        HR    = float(bus.get("HR"))
        MAP   = float(bus.get("MAP"))
        PAWP  = float(bus.get("PAWP"))
        CVP   = float(bus.get("CVP"))
        Ppl   = float(bus.get("Ppl"))

        self._T_cycle = 60.0 / max(HR, 20.0)

        # EDV da Frank-Starling
        PAWP_tm = max(PAWP - Ppl * 0.05, 0.0)
        lv_lo, lv_hi = self._edv_bounds("lv")
        rv_lo, rv_hi = self._edv_bounds("rv")
        self._EDV_lv = float(np.clip(
            self.params["EDV0_lv"] * (1 + 0.010 * (PAWP_tm - 8.0)), lv_lo, lv_hi
        ))
        self._EDV_rv = float(np.clip(
            self.params["EDV0_rv"] * (1 + 0.008 * (CVP - 5.0)), rv_lo, rv_hi
        ))

        # Emax effettivo (con FS)
        self._lv_Emax_eff = self._FS_Emax(
            self.params["Emax_lv"], self._EDV_lv, self.params["EDV0_lv"]
        )
        self._rv_Emax_eff = self._FS_Emax(
            self.params["Emax_rv"], self._EDV_rv, self.params["EDV0_rv"]
        )

        # ESV da ESPVR: Emax * (ESV - V0) = P_es ≈ DAP
        DAP_est = self._diastolic_pressure_estimate(MAP)   # DAP ≈ 73% MAP (approssimazione)
        self._ESV_lv = float(np.clip(
            self.params["V0_lv"] + DAP_est / (self._lv_Emax_eff + 1e-6),
            self._esv_lower("lv"), self._EDV_lv * 0.85
        ))
        PAP = float(bus.get("PAP_mean"))
        self._ESV_rv = float(np.clip(
            self.params["V0_rv"] + PAP / (self._rv_Emax_eff + 1e-6),
            self._esv_lower("rv"), self._EDV_rv * 0.85
        ))

        self._SV_lv = max(self._EDV_lv - self._ESV_lv, 1.0)
        self._SV_rv = max(self._EDV_rv - self._ESV_rv, 1.0)
        wt = float(self.params.get("weight_kg", 20.0))
        CO_init = float(np.clip(self._SV_lv * HR / 1000.0, 0.04 * wt, 0.25 * wt))

        # Scrivi output iniziali
        bus.update({
            "P_lv_t":        float(self.params["Emin_lv"] * max(self._EDV_lv - self.params["V0_lv"], 0)),
            "P_rv_t":        float(self.params["Emin_rv"] * max(self._EDV_rv - self.params["V0_rv"], 0)),
            "V_lv_t":        float(self._EDV_lv),
            "V_rv_t":        float(self._EDV_rv),
            "cardiac_phase": "FILL",
            "P_la":          float(self._P_la),
            "P_ra":          float(self._P_ra),
            "Q_ao":          0.0, "Q_pul": 0.0, "Q_mitral": 0.0,
            "dPdt_max":      0.0, "dPdt_min": 0.0,
            "Tau_relax":     0.05, "LVEDP": 4.0,
            "LVESV":         float(self._ESV_lv),
            "Ea":            1.7, "VAC": 1.0,
            "SW_lv":         0.0, "PVA_lv": 0.0, "MVO2_lv": 8.0,
            "CO":            float(CO_init),
            "SV":            float(self._SV_lv),
            "EDV_lv":        float(self._EDV_lv),
            "ESV_lv":        float(self._ESV_lv),
            "EF_lv":         float(self._SV_lv / (self._EDV_lv + 1e-6)),
            "SAP_btb":       float(MAP + 15.0),
            "DAP_btb":       float(DAP_est),
        })

    # ------------------------------------------------------------------
    # Step
    # ------------------------------------------------------------------

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        HR  = float(bus.get("HR")) * float(bus.get("drug_HR_mod"))
        HR  = float(np.clip(HR, 20.0, 250.0))
        MAP = float(bus.get("MAP"))
        CVP = float(bus.get("CVP"))
        PAP = float(bus.get("PAP_mean"))
        PAWP= float(bus.get("PAWP"))
        Ppl = float(bus.get("Ppl"))
        heart_lung_mod = float(bus.get("heart_lung_CO_mod")) if hasattr(bus.state, "heart_lung_CO_mod") else 1.0
        venous_return_mod = float(bus.get("venous_return_mod")) if hasattr(bus.state, "venous_return_mod") else 1.0
        fluid_resp = float(bus.get("fluid_responsiveness")) if hasattr(bus.state, "fluid_responsiveness") else 0.6

        # CVP con correzione fluidi
        fluid_corr = bus.get("fluid_CVP_correction") \
                     if hasattr(bus.state, "fluid_CVP_correction") else 0.0
        CVP = float(np.clip(CVP + fluid_corr, 0.5, 20.0))

        # Aggiorna timing
        self._T_cycle = 60.0 / max(HR, 20.0)
        T = self._T_cycle
        self._t_cycle += dt
        if self._t_cycle >= T:
            self._t_cycle -= T
            self._end_of_beat(bus, HR, MAP, CVP, PAP, PAWP, Ppl, venous_return_mod, fluid_resp)

        t = self._t_cycle

        # Forme d'onda analitiche
        V_lv = self._V_lv_waveform(t, T)
        V_rv = self._V_rv_waveform(t, T)
        E_lv = self._elastance_lv(t, T)
        E_rv = self._elastance_rv(t, T)

        P_lv = float(E_lv * max(V_lv - self.params["V0_lv"], 0.0))
        P_rv = float(E_rv * max(V_rv - self.params["V0_rv"], 0.0))

        Q_ao  = self._Q_ao_waveform(t, T)
        # Q_pul: profilo analogo scalato su SV_rv
        Ts = T * self.params["Ts_frac"]
        T_ivc = T * self.params["T_ivc_frac"]
        T_eject = Ts - T_ivc
        if T_ivc < t <= Ts:
            frac = (t - T_ivc) / T_eject
            Q_pul = float(np.pi / 2.0 * self._SV_rv / T_eject * np.sin(np.pi * frac))
        else:
            Q_pul = 0.0

        Q_mit = Q_ao   # steady-state: flusso transmitralico ≈ Q_ao

        # Pressioni atriali (compliance semplice)
        C_la = self.params["C_la"]
        C_ra = self.params["C_ra"]
        # La LA si riempie con Q_pul e si svuota con Q_mit
        self._V_la = float(np.clip(
            self._V_la + (Q_pul - Q_mit) * dt,
            self.params["V0_la"] * 0.5, 80.0
        ))
        self._V_ra = float(np.clip(
            self._V_ra + (Q_ao - Q_pul) * dt * 0.0 + 0.0,   # costante in ss
            self.params["V0_ra"] * 0.5, 100.0
        ))
        self._P_la = float(max((self._V_la - self.params["V0_la"]) / C_la, 0.5))
        self._P_ra = float(max(CVP * 0.8, 0.5))   # P_ra ≈ CVP

        # Fase cardiaca
        if t <= T_ivc:
            phase = "IVC"
        elif t <= Ts:
            phase = "EJECT"
        elif t <= Ts + T * self.params["T_ivr_frac"]:
            phase = "IVR"
        else:
            phase = "FILL"

        # dP/dt LV
        if hasattr(self, "_P_lv_prev"):
            dPdt = (P_lv - self._P_lv_prev) / (dt + 1e-9)
            self._dPdt_max = max(self._dPdt_max, dPdt)
            self._dPdt_min = min(self._dPdt_min, dPdt)
        self._P_lv_prev = P_lv

        # CO e derivati — limite fisiologico pediatrico alto ma non illimitato
        wt = float(self.params.get("weight_kg", 20.0))
        CO_raw = self._SV_lv * HR / 1000.0
        # L'effetto cuore-polmone applicato qui rende persistente nel battito
        # successivo la penalizzazione generata da CirculationModule.
        CO  = float(np.clip(CO_raw * heart_lung_mod, 0.04 * wt, 0.25 * wt))
        SAP = MAP + max(8.0, 0.23 * MAP)   # stima SAP
        DAP = self._diastolic_pressure_estimate(MAP)

        bus.update({
            "P_lv_t":        float(P_lv),
            "P_rv_t":        float(P_rv),
            "V_lv_t":        float(V_lv),
            "V_rv_t":        float(V_rv),
            "cardiac_phase": phase,
            "P_la":          float(self._P_la),
            "P_ra":          float(self._P_ra),
            "Q_ao":          float(Q_ao),
            "Q_pul":         float(Q_pul),
            "Q_mitral":      float(Q_mit),
            "dPdt_max":      float(self._dPdt_max),
            "dPdt_min":      float(self._dPdt_min),
            "Tau_relax":     float(self._Tau_relax),
            "LVEDP":         float(self._LVEDP),
            "LVESV":         float(self._ESV_lv),
            "Ea":            float(self._Ea),
            "VAC":           float(self._VAC),
            "SW_lv":         float(self._SW_lv),
            "PVA_lv":        float(self._PVA_lv),
            "MVO2_lv":       float(self._MVO2_lv),
            "CO":            float(CO),
            "SV":            float(self._SV_lv),
            "EDV_lv":        float(self._EDV_lv),
            "ESV_lv":        float(self._ESV_lv),
            "EF_lv":         float(self._SV_lv / (self._EDV_lv + 1e-6)),
            "SAP_btb":       float(SAP),
            "DAP_btb":       float(DAP),
        })

    # ------------------------------------------------------------------
    # Fine battito: aggiorna EDV/ESV per prossimo ciclo
    # ------------------------------------------------------------------

    def _end_of_beat(self, bus, HR, MAP, CVP, PAP, PAWP, Ppl, venous_return_mod=1.0, fluid_resp=0.6):
        self._beat_count += 1

        # Frank-Starling: aggiorna Emax_eff e EDV
        PAWP_tm = max(PAWP - Ppl * 0.05, 0.0)
        preload_gain = 0.65 + 0.35 * float(np.clip(fluid_resp, 0.0, 1.0))
        vr = float(np.clip(venous_return_mod, 0.55, 1.10))
        lv_lo, lv_hi = self._edv_bounds("lv")
        rv_lo, rv_hi = self._edv_bounds("rv")
        EDV_new_lv = float(np.clip(
            self.params["EDV0_lv"] * (1 + 0.010 * (PAWP_tm - 8.0) * preload_gain) * vr,
            lv_lo, lv_hi
        ))
        EDV_new_rv = float(np.clip(
            self.params["EDV0_rv"] * (1 + 0.008 * (CVP - 5.0) * preload_gain) * vr,
            rv_lo, rv_hi
        ))

        self._lv_Emax_eff = self._FS_Emax(
            self.params["Emax_lv"], EDV_new_lv, self.params["EDV0_lv"]
        )
        self._rv_Emax_eff = self._FS_Emax(
            self.params["Emax_rv"], EDV_new_rv, self.params["EDV0_rv"]
        )

        # ESV da ESPVR
        DAP_est = self._diastolic_pressure_estimate(MAP)
        ESV_new_lv = float(np.clip(
            self.params["V0_lv"] + DAP_est / (self._lv_Emax_eff + 1e-6),
            self._esv_lower("lv"), EDV_new_lv * 0.85
        ))
        ESV_new_rv = float(np.clip(
            self.params["V0_rv"] + PAP / (self._rv_Emax_eff + 1e-6),
            self._esv_lower("rv"), EDV_new_rv * 0.85
        ))

        self._EDV_lv = EDV_new_lv
        self._ESV_lv = ESV_new_lv
        self._SV_lv  = max(EDV_new_lv - ESV_new_lv, 1.0)
        self._EDV_rv = EDV_new_rv
        self._ESV_rv = ESV_new_rv
        self._SV_rv  = max(EDV_new_rv - ESV_new_rv, 1.0)

        # LVEDP
        self._LVEDP = float(
            self.params["Emin_lv"] * max(EDV_new_lv - self.params["V0_lv"], 0.0)
        )

        # Stroke Work [mJ]: SW ≈ SV × (MAP - LVEDP) × 0.1333
        self._SW_lv = float(self._SV_lv * max(MAP - self._LVEDP, 0.0) * 0.1333)

        # PVA ≈ SW × 1.5
        self._PVA_lv = float(self._SW_lv * 1.5)

        # MVO2
        self._MVO2_lv = float(
            self._PVA_lv * HR / 60.0 / (self.params["MVO2_efficiency"] + 1e-6) / 1000.0 + 2.0
        )

        # Tau_relax: |P_es| / |dPdt_min|
        if abs(self._dPdt_min) > 50:
            self._Tau_relax = float(np.clip(
                abs(DAP_est) / (abs(self._dPdt_min) + 1e-3), 0.02, 0.20
            ))

        # Ea e VAC
        if self._SV_lv > 1.0:
            self._Ea = float(np.clip(DAP_est / self._SV_lv, 0.3, 5.0))
        self._VAC = float(np.clip(self._Ea / (self._lv_Emax_eff + 1e-6), 0.1, 5.0))

        # Reset dPdt per prossimo ciclo
        self._dPdt_max = 0.0
        self._dPdt_min = 0.0
