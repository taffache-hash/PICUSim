"""
ICP & Cerebral Module
======================
Pressione intracranica, perfusione cerebrale e autoregolazione.

Fisica implementata:

MONRO-KELLIE modificato:
  V_total = V_brain + V_CSF + V_blood = costante
  Compliance intracranica non lineare (Avezaat & van Eijndhoven 1984):
    dICP/dV = ICP / PVI
    dove PVI (pressure-volume index) ≈ 26 mL (adulto), 18 mL (bambino 20 kg)

  ICP(V) = ICP_0 × 10^(V_extra / PVI)

AUTOREGOLAZIONE CEREBROVASCOLARE:
  CBF ~ costante per CPP 50-150 mmHg (bambino: 40-120 mmHg)
  Se CPP < CPP_low: vasodilatazione → CBF↓, V_blood↑ → ICP↑ (feedback positivo)
  Se CPP > CPP_high: vasocostrizione → V_blood↓ → ICP↓
  Guadagno autoregolazione: ridotto in TBI, sepsi, ipossemia

RISPOSTA DI CUSHING (tardiva, emergenziale):
  ICP > CPP critica → HR↓ (bradicardia) + MAP↑ (ipertensione)
  Attivata solo se CPP < 20 mmHg per > 30s

TERAPIE:
  Osmoterapia (manitolo/NaCl 3%): riduce V_brain → ICP↓
    τ_osmo = 15 min; effetto max -5 mmHg a 2 ore
  Desametasone: riduce edema vasogenico (effetto lento, da SteroidsModule)
  Iperventilazione: PaCO2↓ → vasocostrizione → V_blood↓ → ICP↓
    ΔV_blood = k_CO2 × ΔPACO2 (2 mL per mmHg)
  Drenaggio CSF: riduzione diretta di V_CSF

Output:
  ICP_mmHg        : pressione intracranica [mmHg]
  CPP_mmHg        : pressione di perfusione cerebrale [mmHg]
  CBF_relative    : flusso ematico cerebrale relativo [0-2] (1=normale)
  V_blood_cc      : volume ematico intracranico [mL]
  PbtO2_mmHg      : pressione parziale O2 cerebrale (stima) [mmHg]
  cushing_active  : bool — risposta di Cushing attiva
  ICP_alert       : bool — ICP > soglia allerta (20 mmHg)
"""

from __future__ import annotations
import numpy as np
from typing import List

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


class ICPModule(BaseModule):
    """
    Modulo ICP e autoregolazione cerebrovascolare.

    Parametri
    ---------
    ICP_baseline      : float  ICP baseline [mmHg] (10.0)
    PVI               : float  Pressure-volume index [mL] (18.0 per bambino)
    V_blood_baseline  : float  Volume ematico intracranico baseline [mL] (100.0)
    V_CSF_baseline    : float  Volume CSF baseline [mL] (80.0 per bambino 20 kg)
    V_brain_baseline  : float  Volume cerebrale [mL] (1100.0 per bambino 20 kg)

    CPP_low           : float  Soglia inf. autoregolazione [mmHg] (45.0)
    CPP_high          : float  Soglia sup. autoregolazione [mmHg] (110.0)
    autoregulation_gain : float  Guadagno autoregolazione [0-1] (1.0 = intatta)

    Osmoterapia:
    osmo_active       : bool   Osmoterapia in corso
    osmo_effect_mL    : float  Riduzione V_brain da osmoterapia [mL]
    tau_osmo_s        : float  Costante di tempo osmoterapia [s] (900 = 15 min)

    Risposta di Cushing:
    cushing_CPP_thresh: float  CPP sotto cui attiva Cushing [mmHg] (20.0)
    cushing_MAP_rise  : float  Aumento MAP per Cushing [mmHg] (20.0)
    cushing_HR_fall   : float  Riduzione HR per Cushing [bpm] (20.0)
    cushing_latency_s : float  Latenza risposta [s] (30.0)

    CO2 reattività:
    k_CO2_mL_mmHg    : float  Variazione V_blood per ΔPaCO2 [mL/mmHg] (2.0)
    PaCO2_ref         : float  PaCO2 di riferimento [mmHg] (40.0)

    Allerta:
    ICP_alert_thresh  : float  [mmHg] (20.0)
    """

    DEFAULT_PARAMS = {
        # Volumi intracranici (bambino 20 kg)
        "ICP_baseline":      10.0,
        "PVI":               18.0,
        "V_blood_baseline": 100.0,
        "V_CSF_baseline":    80.0,
        "V_edema_baseline":   0.0,   # edema iniziale [mL]

        # Autoregolazione
        "CPP_low":           45.0,
        "CPP_high":         110.0,
        "autoregulation_gain": 1.0,
        "tau_vasc_s":        30.0,   # costante di tempo vasoregolazione

        # CO2 reattività
        "k_CO2_mL_mmHg":     2.0,
        "PaCO2_ref":         40.0,

        # Osmoterapia
        "osmo_active":       False,
        "osmo_max_effect_mL": 8.0,
        "tau_osmo_s":        900.0,

        # Drenaggio CSF
        "CSF_drainage_mL_h": 0.0,

        # Risposta di Cushing
        "cushing_CPP_thresh": 20.0,
        "cushing_MAP_rise":   20.0,
        "cushing_HR_fall":    20.0,
        "cushing_latency_s":  30.0,

        # Allerta
        "ICP_alert_thresh":   20.0,

        # Effetto steroidi (dexa)
        "steroid_ICP_gain":   0.3,
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="ICP", params=merged)

        self._ICP:         float = merged["ICP_baseline"]
        self._V_blood:     float = merged["V_blood_baseline"]
        self._V_edema:     float = merged["V_edema_baseline"]
        self._V_osmo_red:  float = 0.0    # riduzione V_brain da osmoterapia [mL]
        self._CBF_rel:     float = 1.0
        self._cushing_t:   float = 0.0    # tempo in Cushing [s]
        self._cushing_active: bool = False

    @property
    def input_keys(self) -> List[str]:
        return ["MAP", "PaCO2", "SaO2", "DO2",
                "steroid_ICP_mod", "HR"]

    @property
    def output_keys(self) -> List[str]:
        return ["ICP_mmHg", "CPP_mmHg", "CBF_relative",
                "V_blood_cc", "PbtO2_mmHg",
                "cushing_active", "ICP_alert"]

    def initialize(self, bus: PhysiologicalBus) -> None:
        self._ICP       = self.params["ICP_baseline"]
        self._V_blood   = self.params["V_blood_baseline"]
        self._V_edema   = self.params["V_edema_baseline"]
        self._V_osmo_red = 0.0
        self._CBF_rel   = 1.0
        self._cushing_t = 0.0
        self._cushing_active = False

        CPP = bus.get("MAP") - self._ICP
        bus.update({
            "ICP_mmHg":      self._ICP,
            "CPP_mmHg":      float(CPP),
            "CBF_relative":  1.0,
            "V_blood_cc":    self._V_blood,
            "PbtO2_mmHg":    25.0,
            "cushing_active": False,
            "ICP_alert":     self._ICP > self.params["ICP_alert_thresh"],
        })

    # ------------------------------------------------------------------
    # Calcolo ICP da Monro-Kellie + Avezaat
    # ------------------------------------------------------------------

    def _compute_ICP(self, V_extra: float) -> float:
        """
        ICP = ICP_0 × 10^(V_extra / PVI)
        V_extra: volume extra intracranico rispetto al baseline [mL]
        """
        PVI    = self.params["PVI"]
        ICP_0  = self.params["ICP_baseline"]
        return float(ICP_0 * 10.0 ** (V_extra / PVI))

    # ------------------------------------------------------------------
    # Autoregolazione cerebrovascolare
    # ------------------------------------------------------------------

    def _CBF_target(self, CPP: float) -> float:
        """
        CBF relativo target [0-2] in funzione di CPP.
        Plateau tra CPP_low e CPP_high.
        """
        lo  = self.params["CPP_low"]
        hi  = self.params["CPP_high"]
        gain = self.params["autoregulation_gain"]

        if CPP >= lo and CPP <= hi:
            CBF_t = 1.0   # plateau autoregolazione
        elif CPP < lo:
            CBF_t = max(0.1, CPP / lo)   # cade linearmente
        else:
            CBF_t = max(0.5, 1.0 - (CPP - hi) / hi * 0.3)

        return float(np.clip(CBF_t, 0.05, 2.0))

    def _V_blood_target(self, CBF_rel: float) -> float:
        """
        V_blood varia inversamente al tono vascolare.
        CBF basso (vasodilatazione) → V_blood aumenta.
        """
        # Vasodilazione: CBF↓ ma V_blood ↑ (paradosso di autoregolazione fallita)
        # CBF normale → V_blood baseline
        return float(self.params["V_blood_baseline"] *
                     (2.0 - CBF_rel) * 0.5 + self.params["V_blood_baseline"] * 0.5)

    # ------------------------------------------------------------------
    # Step
    # ------------------------------------------------------------------

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        MAP    = bus.get("MAP")
        PaCO2  = bus.get("PaCO2")
        SaO2   = bus.get("SaO2")
        DO2    = bus.get("DO2")

        # --- Effetto steroidi su edema ---
        steroid_ICP_mod = bus.get("steroid_ICP_mod") \
                          if hasattr(bus.state, "steroid_ICP_mod") else 1.0
        edema_gain = self.params["steroid_ICP_gain"]
        V_edema_target = self._V_edema * steroid_ICP_mod
        tau_edema = 21600.0  # 6h costante di tempo desametasone su edema
        self._V_edema += (V_edema_target - self._V_edema) * dt / tau_edema

        # --- Effetto CO2 su V_blood ---
        k_CO2 = self.params["k_CO2_mL_mmHg"]
        V_blood_CO2_corr = (self.params["V_blood_baseline"] +
                            k_CO2 * (PaCO2 - self.params["PaCO2_ref"]))

        # --- Osmoterapia (legge dal Bus — perturbazione YAML) ---
        osmo_active = bus.get("osmo_active") \
                      if hasattr(bus.state, "osmo_active") else self.params["osmo_active"]
        if osmo_active:
            osmo_max = self.params["osmo_max_effect_mL"]
            tau_osmo = self.params["tau_osmo_s"]
            self._V_osmo_red += (osmo_max - self._V_osmo_red) * dt / tau_osmo
        else:
            self._V_osmo_red = max(self._V_osmo_red - dt / 14400.0, 0.0)

        # --- Drenaggio CSF (legge dal Bus) ---
        csf_rate = bus.get("csf_drain_mL_h") \
                   if hasattr(bus.state, "csf_drain_mL_h") \
                   else self.params["CSF_drainage_mL_h"]
        V_CSF_drain = csf_rate * dt / 3600.0

        # --- ICP corrente ---
        # V_extra = variazione rispetto al baseline
        V_blood_curr = np.clip(V_blood_CO2_corr, 50.0, 200.0)

        # Autoregolazione → aggiorna V_blood verso target
        CPP_curr = MAP - self._ICP
        CBF_t    = self._CBF_target(CPP_curr)
        tau_vasc = self.params["tau_vasc_s"]
        V_blood_auto = self._V_blood_target(CBF_t)
        self._V_blood += (min(V_blood_auto, V_blood_curr) - self._V_blood) * dt / tau_vasc

        # Volume extra totale
        V_extra = (self._V_blood - self.params["V_blood_baseline"] +
                   self._V_edema - self.params["V_edema_baseline"] -
                   self._V_osmo_red - V_CSF_drain)

        self._ICP = float(np.clip(self._compute_ICP(V_extra), 5.0, 100.0))
        CPP = float(np.clip(MAP - self._ICP, -20.0, 150.0))

        # --- CBF relativo (per output e PbtO2) ---
        self._CBF_rel = self._CBF_target(CPP)

        # --- PbtO2 (stima) ---
        # PbtO2 ≈ f(CBF, SaO2, Hb) — modello semplificato
        PbtO2 = float(np.clip(
            25.0 * self._CBF_rel * SaO2 / 0.97,
            2.0, 60.0
        ))

        # --- Risposta di Cushing ---
        if CPP < self.params["cushing_CPP_thresh"]:
            self._cushing_t += dt
        else:
            self._cushing_t = max(self._cushing_t - dt * 2, 0.0)

        cushing_latency = self.params["cushing_latency_s"]
        if self._cushing_t > cushing_latency and not self._cushing_active:
            self._cushing_active = True
            # Attiva risposta: MAP↑, HR↓
            bus.set("MAP", float(np.clip(
                bus.get("MAP") + self.params["cushing_MAP_rise"], 0, 200
            )))
            bus.set("HR", float(np.clip(
                bus.get("HR") - self.params["cushing_HR_fall"], 20, 220
            )))
        elif self._cushing_t < cushing_latency * 0.3:
            self._cushing_active = False

        bus.update({
            "ICP_mmHg":      float(self._ICP),
            "CPP_mmHg":      float(CPP),
            "CBF_relative":  float(self._CBF_rel),
            "V_blood_cc":    float(self._V_blood),
            "PbtO2_mmHg":    float(PbtO2),
            "cushing_active": bool(self._cushing_active),
            "ICP_alert":     bool(self._ICP > self.params["ICP_alert_thresh"]),
        })
