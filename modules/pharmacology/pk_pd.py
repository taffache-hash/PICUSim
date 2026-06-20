"""
Pharmacology Module — PK/PD completo
=====================================
Modelli farmacocinetici/farmacodinamici per i farmaci principali in PICU.

Farmaci implementati:
  1. Ketamina        — bicompartimentale, PD su HR/MAP/drive/analgesia
  2. Noradrenalina   — monocompartimentale, PD vasocostrizione α1/β1
  3. Midazolam       — bicompartimentale, PD sedazione → drive_level
  4. Propofol        — bicompartimentale, PD sedazione + vasodilatazione
  5. Rocuronio       — monocompartimentale, PD NMB → Pmus=0
  6. Adrenalina      — monocompartimentale, PD vasoattivo/inotropo qualitativo
  7. Dopamina        — monocompartimentale, PD inotropo/vasopressorio qualitativo
  8. Fentanyl        — monocompartimentale, PD analgesia/respiratory depression
  9. Dexmedetomidina — monocompartimentale, PD sedazione α2/bradicardia
 10. Vancomicina     — monocompartimentale, clearance renale/CRRT e target PK/PD qualitativo
 11. Furosemide      — monocompartimentale, clearance renale e risposta diuretica qualitativa
 12. Morfina         — monocompartimentale, analgesia/respiratory depression e rischio M6G qualitativo
 13. Clonidina       — monocompartimentale, sedazione α2/sympatholysis/withdrawal qualitativo
 14. Insulina        — monocompartimentale, PD glucosio/potassio qualitativa
 15. Piperacillina/Tazobactam — piperacillina monocompartimentale, fT>MIC qualitativo

Modello PK standard: sistema di ODE lineari a 2 compartimenti
  dC1/dt = dose_rate/Vd1 - (k10+k12)*C1 + k21*C2*(Vd2/Vd1)
  dC2/dt = k12*C1*(Vd1/Vd2) - k21*C2

Modello PD: Hill equation (Emax model)
  E(C) = Emax * C^n / (EC50^n + C^n)

Parametri derivati da letteratura pediatrica (v1.01: scaling allometrico
trasparente per clearance e volumi; v1.10: clearance extracorporea CRRT-lite
educativa basata su effluent rate e sieving coefficient; non validato per uso clinico).
Riferimenti di ancoraggio dichiarati:
  - Ketamina: Domino 1992, Herd 2007 (pediatric PK)
  - Norad: Bhatt-Mehta 1992
  - Midazolam: Payne 1989, de Wildt 2003
  - Propofol: Absalom 2003 (Paedfusor)
  - Rocuronio: Driessen 2000
  - Vancomicina: Marsot 2012; Le 2014; Akunne 2021 review (educational scaffold)
  - Furosemide: neonatal/pediatric PK literature; renal secretion and AKI response are educational placeholders
  - Morphine: pediatric critical-care PK literature; M3G/M6G renal-accumulation risk is qualitative
  - Clonidine: pediatric sedative/withdrawal use literature; α2 PD is qualitative
  - Insulin: public educational glucose/potassium PD scaffold; not a dosing model
  - Piperacillin/tazobactam: pediatric beta-lactam PK/PD literature; fT>MIC scaffold only
"""

from __future__ import annotations
import numpy as np
from typing import List, Dict, Any

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


# ---------------------------------------------------------------------------
# Modello bicompartimentale generico
# ---------------------------------------------------------------------------

class TwoCompartmentPK:
    """
    Cinetica bicompartimentale (Euler implicito, stabile per dt piccoli).

    Stato: [C1, C2] — concentrazioni nei compartimenti [mg/L] o [mcg/mL]
    """

    def __init__(self, Vd1: float, Vd2: float,
                 k10: float, k12: float, k21: float):
        """
        Parameters
        ----------
        Vd1, Vd2 : float  Volumi di distribuzione [L]
        k10      : float  Costante di eliminazione dal comp. 1 [s-1]
        k12      : float  Costante di trasferimento 1→2 [s-1]
        k21      : float  Costante di trasferimento 2→1 [s-1]
        """
        self.Vd1 = Vd1
        self.Vd2 = Vd2
        self.k10 = k10
        self.k12 = k12
        self.k21 = k21
        self.C1: float = 0.0   # concentrazione compartimento centrale [mg/L]
        self.C2: float = 0.0   # concentrazione compartimento periferico

    def step(self, infusion_rate_mg_min: float, dt: float, extra_clearance_L_min: float = 0.0) -> None:
        """
        Avanza la PK di dt secondi.
        infusion_rate_mg_min: velocità di infusione [mg/min]
        extra_clearance_L_min: clearance extracorporea aggiuntiva sul compartimento centrale [L/min].
        """
        rate_s = infusion_rate_mg_min / 60.0   # mg/s
        k_extra = max(float(extra_clearance_L_min), 0.0) / max(self.Vd1, 1e-9) / 60.0

        # Euler esplicito (dt << τ di tutti i processi → stabile)
        dC1 = (rate_s / self.Vd1
               - (self.k10 + k_extra + self.k12) * self.C1
               + self.k21 * self.C2 * (self.Vd2 / self.Vd1))
        dC2 = (self.k12 * self.C1 * (self.Vd1 / self.Vd2)
               - self.k21 * self.C2)

        self.C1 = max(self.C1 + dC1 * dt, 0.0)
        self.C2 = max(self.C2 + dC2 * dt, 0.0)

    @property
    def C_plasma(self) -> float:
        return self.C1


class OneCompartmentPK:
    """Cinetica monocompartimentale."""

    def __init__(self, Vd: float, k_elim: float):
        self.Vd = Vd
        self.k_elim = k_elim
        self.C: float = 0.0

    def step(self, infusion_rate_mg_min: float, dt: float, extra_clearance_L_min: float = 0.0) -> None:
        rate_s = infusion_rate_mg_min / 60.0
        k_extra = max(float(extra_clearance_L_min), 0.0) / max(self.Vd, 1e-9) / 60.0
        dC = rate_s / self.Vd - (self.k_elim + k_extra) * self.C
        self.C = max(self.C + dC * dt, 0.0)

    @property
    def C_plasma(self) -> float:
        return self.C


class InsulinOneCompartmentPK:
    """Simple insulin PK using infusion in international units per hour.

    State is plasma insulin proxy [mU/L]. The model is intentionally
    qualitative: it translates an infusion order into a delayed effect signal
    for glucose and potassium modules without attempting clinical dosing.
    """

    def __init__(self, Vd: float, k_elim: float):
        self.Vd = max(float(Vd), 1e-9)
        self.k_elim = max(float(k_elim), 0.0)
        self.C_mU_L: float = 0.0

    def step(self, infusion_U_h: float, dt: float) -> None:
        rate_mU_s = max(float(infusion_U_h), 0.0) * 1000.0 / 3600.0
        dC = rate_mU_s / self.Vd - self.k_elim * self.C_mU_L
        self.C_mU_L = max(self.C_mU_L + dC * float(dt), 0.0)

    @property
    def C_plasma(self) -> float:
        return self.C_mU_L


class RenalDependentOneCompartmentPK:
    """One-compartment PK with dynamic clearance [L/min].

    Used for drugs where renal function is the dominant educational covariate.
    It deliberately remains a transparent scaffold: concentration is total plasma
    concentration, not unbound concentration, and no therapeutic dosing advice is
    implied.
    """

    def __init__(self, Vd: float):
        self.Vd = max(float(Vd), 1e-9)
        self.C: float = 0.0

    def step(self, infusion_rate_mg_min: float, dt: float, clearance_L_min: float, extra_clearance_L_min: float = 0.0) -> None:
        rate_s = float(infusion_rate_mg_min) / 60.0
        cl_total = max(float(clearance_L_min), 0.0) + max(float(extra_clearance_L_min), 0.0)
        k_total = cl_total / self.Vd / 60.0
        dC = rate_s / self.Vd - k_total * self.C
        self.C = max(self.C + dC * float(dt), 0.0)

    @property
    def C_plasma(self) -> float:
        return self.C


# ---------------------------------------------------------------------------
# Hill equation
# ---------------------------------------------------------------------------

def hill(C: float, EC50: float, Emax: float, n: float = 1.0) -> float:
    """Emax model: E = Emax * C^n / (EC50^n + C^n)"""
    if C <= 0:
        return 0.0
    Cn = C ** n
    EC50n = EC50 ** n
    return float(Emax * Cn / (EC50n + Cn))


# ---------------------------------------------------------------------------
# Scaling allometrico PK v1.01
# ---------------------------------------------------------------------------

REF_WEIGHT_KG = 20.0


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(x)))


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def maturation_factor(age_y: float, age_group: str = "child") -> float:
    """
    Fattore prudente di maturazione della clearance per profili pediatrici.

    È un moltiplicatore euristico esplicito: serve a evitare che un neonato
    venga trattato come un piccolo bambino di 20 kg. Non sostituisce modelli
    farmaco-specifici validati.
    """
    age = max(float(age_y), 0.0)
    group = str(age_group or "child").lower()

    if group == "neonate" or age < 0.12:
        return 0.50
    if group == "infant" or age < 1.0:
        return 0.75
    if group == "toddler" or age < 3.0:
        return 0.90
    if group == "adolescent" or age >= 12.0:
        return 1.05
    return 1.00


def allometric_volume(per_kg_value: float, weight_kg: float,
                      ref_weight_kg: float = REF_WEIGHT_KG,
                      exponent: float = 1.0) -> float:
    """Volume [L] = valore per kg al riferimento × W_ref × (W/W_ref)^exp."""
    wt = max(float(weight_kg), 0.5)
    ref = max(float(ref_weight_kg), 0.5)
    return float(per_kg_value) * ref * (wt / ref) ** float(exponent)


def allometric_clearance(cl_ref_L_min: float, weight_kg: float,
                         ref_weight_kg: float = REF_WEIGHT_KG,
                         exponent: float = 0.75,
                         maturation: float = 1.0) -> float:
    """Clearance [L/min] scalata allometricamente dal riferimento a 20 kg."""
    wt = max(float(weight_kg), 0.5)
    ref = max(float(ref_weight_kg), 0.5)
    return float(cl_ref_L_min) * (wt / ref) ** float(exponent) * float(maturation)


def k_from_clearance(CL_L_min: float, V_L: float) -> float:
    """Converte CL/V in costante di primo ordine [s^-1]."""
    V = max(float(V_L), 1e-9)
    return float(CL_L_min) / V / 60.0


# ---------------------------------------------------------------------------
# CRRT-lite drug clearance v1.10
# ---------------------------------------------------------------------------

# Educational drug-property table. The sieving coefficients are deliberately
# conservative placeholders derived from general CRRT principles: extracorporeal
# removal is higher for low protein binding / low Vd drugs and lower when
# non-renal clearance dominates. These are not drug-dosing recommendations.
CRRT_DRUG_PROPERTIES: Dict[str, Dict[str, float]] = {
    "ketamine":        {"sieving_coefficient": 0.20, "max_fraction_intrinsic": 0.08},
    "noradrenaline":   {"sieving_coefficient": 0.00, "max_fraction_intrinsic": 0.00},
    "adrenaline":      {"sieving_coefficient": 0.00, "max_fraction_intrinsic": 0.00},
    "dopamine":        {"sieving_coefficient": 0.00, "max_fraction_intrinsic": 0.00},
    "midazolam":       {"sieving_coefficient": 0.12, "max_fraction_intrinsic": 0.10},
    "propofol":        {"sieving_coefficient": 0.01, "max_fraction_intrinsic": 0.01},
    "rocuronium":      {"sieving_coefficient": 0.35, "max_fraction_intrinsic": 0.30},
    "fentanyl":        {"sieving_coefficient": 0.02, "max_fraction_intrinsic": 0.02},
    "dexmedetomidine": {"sieving_coefficient": 0.03, "max_fraction_intrinsic": 0.03},
    "vancomycin":      {"sieving_coefficient": 0.75, "max_fraction_intrinsic": 1.00},
    "furosemide":       {"sieving_coefficient": 0.10, "max_fraction_intrinsic": 0.15},
    "morphine":         {"sieving_coefficient": 0.15, "max_fraction_intrinsic": 0.10},
    "clonidine":        {"sieving_coefficient": 0.05, "max_fraction_intrinsic": 0.05},
    "insulin":          {"sieving_coefficient": 0.00, "max_fraction_intrinsic": 0.00},
    "piperacillin":      {"sieving_coefficient": 0.75, "max_fraction_intrinsic": 1.00},
}


# ---------------------------------------------------------------------------
# Modulo principale
# ---------------------------------------------------------------------------

class PharmacologyModule(BaseModule):
    """
    PK/PD completo per 15 farmaci PICU.

    Il modulo:
    1. Legge le dosi dal Bus (mcg/kg/min o mg/kg/h)
    2. Integra la PK per ogni farmaco
    3. Calcola gli effetti PD e li scrive nel Bus come modificatori

    Effetti PD scritti nel Bus
    --------------------------
    drug_MAP_mod    : moltiplicatore su MAP (da norad, propofol)
    drug_HR_mod     : moltiplicatore su HR (da ketamina, norad)
    drug_drive_mod  : moltiplicatore su drive/Pmus (da midazolam, propofol)
    drug_Pmus_add   : aggiunta assoluta su Pmus (ketamina → dissociativo)
    drug_NMB_frac   : frazione di blocco neuromuscolare [0-1] (rocuronio)
    drug_SVR_mod    : moltiplicatore su SVR (norad già in Circulation;
                      questo è per propofol/midazolam)

    Concentrazioni plasmatiche (output informativi)
    -----------------------------------------------
    C_ketamine_mg_L, C_norad_ng_mL, C_midazolam_ng_mL,
    C_propofol_mg_L, C_rocuronium_ng_mL, C_adrenaline_ng_mL,
    C_dopamine_ng_mL, C_fentanyl_ng_mL, C_dexmedetomidine_ng_mL,
    C_morphine_ng_mL, C_clonidine_ng_mL, C_insulin_mU_L, C_piperacillin_mg_L
    """

    DEFAULT_PARAMS = {
        # Paziente — aggiornato dal ScenarioLoader
        "weight_kg": 20.0,
        "age_y": 6.0,
        "age_group": "child",
        "patient_profile": "child_20kg",

        # v1.01 scaling PK: 20 kg resta il riferimento numerico.
        # Volumi ~ W^1.0, clearance ~ W^0.75 × maturazione età.
        "pk_ref_weight_kg": REF_WEIGHT_KG,
        "pk_volume_exponent": 1.0,
        "pk_clearance_exponent": 0.75,
        "pk_intercompartment_exponent": 0.75,
        "pk_apply_maturation": True,

        # PK Ketamina (bicompartimentale, parametri ancorati a 20 kg)
        # Herd 2007: Cl=18 mL/kg/min, Vd1=0.5 L/kg, Vd2=2.5 L/kg
        "ket_Vd1_per_kg":  0.50,   # L/kg al riferimento 20 kg
        "ket_Vd2_per_kg":  2.50,   # L/kg al riferimento 20 kg
        "ket_CL_mL_kg_min": 18.0,  # clearance di riferimento
        "ket_k10":         0.000600,  # s-1 legacy @20 kg
        "ket_k12":         0.008333,  # s-1
        "ket_k21":         0.001667,  # s-1
        # PD Ketamina
        "ket_EC50_sed":    1.20,   # mg/L (sedazione/amnesia)
        "ket_EC50_anal":   0.20,   # mg/L (analgesia)
        "ket_Emax_HR":     0.25,   # +25% HR a concentrazione satura
        "ket_Emax_MAP":    0.20,   # +20% MAP
        "ket_n":           1.5,    # Hill coefficient

        # PK Noradrenalina (monocompartimentale)
        # Bhatt-Mehta 1992: t1/2 ~ 3-4 min, Vd ~ 0.4 L/kg
        "nor_Vd_per_kg":   0.40,   # L/kg al riferimento 20 kg
        "nor_CL_mL_kg_min": None,   # None → derivata dal k_elim legacy @20 kg
        "nor_k_elim":      0.002917, # s-1 legacy @20 kg (t1/2 ~ 4 min)
        # PD Noradrenalina (già in Circulation con gain semplificato)
        # Qui manteniamo il modello PK per output informativi
        "nor_EC50_vaso":   1.5,    # ng/mL
        "nor_Emax_SVR":    0.60,   # +60% SVR max
        "nor_Emax_HR":    -0.10,   # -10% HR (effetto baroriflessivo)

        # PK Adrenalina / epinephrine (monocompartimentale, educational placeholder)
        "adr_Vd_per_kg":   0.35,
        "adr_CL_mL_kg_min": None,
        "adr_k_elim":      0.00462,   # s-1, t1/2 ~2.5 min
        "adr_EC50_vaso":   0.40,      # ng/mL, qualitative
        "adr_Emax_MAP":    0.45,
        "adr_Emax_HR":     0.22,
        "adr_Emax_CO":     0.35,

        # PK Dopamina (monocompartimentale, educational placeholder)
        "dop_Vd_per_kg":   1.00,
        "dop_CL_mL_kg_min": None,
        "dop_k_elim":      0.00385,   # s-1, t1/2 ~3 min
        "dop_EC50_inotropy": 20.0,    # ng/mL, qualitative
        "dop_Emax_MAP":    0.22,
        "dop_Emax_HR":     0.18,
        "dop_Emax_CO":     0.35,

        # PK Midazolam (bicompartimentale)
        # de Wildt 2003: Cl=10 mL/kg/min, Vd1=0.3 L/kg, Vd2=1.0 L/kg
        "mid_Vd1_per_kg":  0.30,
        "mid_Vd2_per_kg":  1.00,
        "mid_CL_mL_kg_min": 10.0,
        "mid_k10":         0.000556,  # s-1 legacy @20 kg
        "mid_k12":         0.003333,
        "mid_k21":         0.001000,
        # PD Midazolam
        "mid_EC50_sed":    150.0,  # ng/mL (sedazione, scala 0-1)
        "mid_Emax_sed":    1.0,    # riduzione drive a saturazione (GABA)
        "mid_Emax_vaso":   0.15,   # vasodilatazione lieve
        "mid_n":           1.8,

        # PK Propofol (bicompartimentale, Paedfusor)
        # Absalom 2003: Cl scalata per età/peso
        "pro_Vd1_per_kg":  0.80,
        "pro_Vd2_per_kg":  5.00,
        "pro_CL_mL_kg_min": None,     # None → derivata dal k10 legacy @20 kg
        "pro_k10":         0.000625,  # s-1 legacy @20 kg
        "pro_k12":         0.005556,
        "pro_k21":         0.000889,
        # PD Propofol
        "pro_EC50_sed":    2.0,    # mg/L
        "pro_Emax_sed":    1.0,    # riduzione drive
        "pro_Emax_vaso":   0.30,   # vasodilatazione significativa
        "pro_Emax_HR":    -0.15,   # bradicardia
        "pro_n":           2.0,

        # PK Rocuronio (monocompartimentale)
        # Driessen 2000: t1/2 ~ 20 min, Vd ~ 0.2 L/kg
        "roc_Vd_per_kg":   0.20,
        "roc_CL_mL_kg_min": None,     # None → derivata dal k_elim legacy @20 kg
        "roc_k_elim":      0.000578,  # s-1 legacy @20 kg (t1/2 ~ 20 min)
        # PD Rocuronio: blocco NMB (Hill sigmoide)
        "roc_EC50_NMB":    500.0,  # ng/mL (95% blocco ~ 3×EC50)
        "roc_n_NMB":       4.0,    # Hill molto ripido (NMJ)

        # PK Fentanyl (monocompartimentale, aligned with analgosedation module)
        "fen_Vd_per_kg":   4.00,
        "fen_CL_mL_kg_min": None,
        "fen_k_elim":      0.0000963, # s-1, t1/2 ~120 min
        "fen_EC50_anal":   1.50,      # ng/mL, qualitative
        "fen_EC50_resp":   3.00,      # ng/mL, qualitative

        # PK Morphine (monocompartimentale, public educational scaffold)
        # Pediatric morphine PK is age/weight dependent; active glucuronide
        # metabolites may accumulate with renal impairment. Not a dosing model.
        "mor_Vd_per_kg":   3.00,
        "mor_CL_mL_kg_min": None,
        "mor_k_elim":      0.000193,  # s-1, t1/2 ~60 min educational anchor
        "mor_EC50_anal":   20.0,      # ng/mL, qualitative
        "mor_EC50_resp":   45.0,      # ng/mL, qualitative
        "mor_Emax_resp":   0.45,
        "mor_Emax_anal":   0.75,

        # PK Clonidine (monocompartimentale, public educational scaffold)
        # Clonidine is represented as a slow α2-agonist sedative/sympatholytic.
        # This is a qualitative teaching model, not a dosing model.
        "clo_Vd_per_kg":   2.00,
        "clo_CL_mL_kg_min": None,
        "clo_k_elim":      0.0000385, # s-1, t1/2 ~300 min educational anchor
        "clo_EC50_sed":    0.80,
        "clo_EC50_hemo":   1.00,
        "clo_Emax_sed":    0.45,
        "clo_Emax_hemo":   0.18,
        "clo_Emax_withdrawal": 0.55,

        # PK Insulin (monocompartimentale, public educational scaffold)
        # Infusion input is insulin_UI_h [U/h]. C_insulin_mU_L is a delayed
        # plasma-effect proxy. Glucose/K effects are qualitative only.
        "ins_Vd_per_kg":   0.10,
        "ins_k_elim":      0.00231,  # s-1, t1/2 ~5 min educational anchor
        "ins_EC50_glucose_mU_L": 25.0,
        "ins_EC50_K_mU_L": 35.0,
        "ins_Emax_glucose": 1.0,
        "ins_Emax_K": 1.0,
        "ins_max_clearance_mmol_L_h": 4.0,
        "ins_max_potassium_shift_mmol_L_h": 0.65,

        # PK Piperacillin/Tazobactam (public educational beta-lactam scaffold)
        # Piperacillin is modelled as the active beta-lactam driver. The tazobactam
        # component is represented only as a qualitative beta-lactamase-support term.
        # PK/PD output is based on fT>MIC concepts and is not a dosing model.
        "pip_Vd_per_kg":   0.35,
        "pip_CL_mL_kg_min": 4.80,
        "pip_MIC_mg_L":    16.0,
        "pip_target_fT_MIC": 0.50,
        "pip_Emax_coverage": 0.85,
        "pip_ft_memory_tau_s": 900.0,
        "taz_beta_lactamase_support": 0.20,

        # PK Dexmedetomidina (monocompartimentale, aligned with analgosedation module)
        "dex_Vd_per_kg":   1.50,
        "dex_CL_mL_kg_min": None,
        "dex_k_elim":      0.0000963, # s-1, t1/2 ~120 min
        "dex_EC50_sed":    0.60,      # ng/mL, qualitative
        "dex_EC50_hemo":   0.80,      # ng/mL, qualitative

        # PK Vancomicina (monocompartimentale, clearance renal-function dependent)
        # Educational anchor: pediatric Vd commonly ~0.5-0.9 L/kg; clearance varies strongly
        # with age, renal function, critical illness and CRRT. This is not a dosing model.
        "van_Vd_per_kg":   0.70,
        "van_CL_mL_kg_min": 2.50,     # reference renal CL at 20 kg and baseline GFR
        "van_MIC_mg_L":    1.0,       # qualitative target organism MIC placeholder
        "van_EC50_multiple_MIC": 4.0, # concentration/MIC for coverage sigmoid midpoint
        "van_Emax_coverage": 0.85,

        # PK Furosemide (monocompartimentale, renal-function dependent)
        # Educational anchor: small Vd, renal tubular secretion, prolonged half-life in neonates/AKI.
        # The PD output is a qualitative diuretic-effect signal, not a prescribing model.
        "fur_Vd_per_kg":   0.25,
        "fur_CL_mL_kg_min": 1.20,     # reference renal/secretory CL at 20 kg and baseline GFR
        "fur_EC50_diuresis_mg_L": 1.00,
        "fur_Emax_diuresis": 1.00,
        "fur_n_diuresis": 1.35,
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="Pharmacology", params=merged)

        # Istanze PK (inizializzate in initialize())
        self._pk_ket: TwoCompartmentPK | None = None
        self._pk_nor: OneCompartmentPK | None = None
        self._pk_mid: TwoCompartmentPK | None = None
        self._pk_pro: TwoCompartmentPK | None = None
        self._pk_roc: OneCompartmentPK | None = None
        self._pk_adr: OneCompartmentPK | None = None
        self._pk_dop: OneCompartmentPK | None = None
        self._pk_fen: OneCompartmentPK | None = None
        self._pk_mor: OneCompartmentPK | None = None
        self._pk_clo: OneCompartmentPK | None = None
        self._pk_ins: InsulinOneCompartmentPK | None = None
        self._pk_pip: RenalDependentOneCompartmentPK | None = None
        self._pk_dex: OneCompartmentPK | None = None
        self._pk_van: RenalDependentOneCompartmentPK | None = None
        self._pk_fur: RenalDependentOneCompartmentPK | None = None
        self._van_base_CL_L_min: float = 0.0
        self._fur_base_CL_L_min: float = 0.0
        self._pip_base_CL_L_min: float = 0.0
        self._pip_ft_above_MIC: float = 0.0
        self._last_furosemide_mg_kg_counter: float = 0.0
        self._pk_scaling_audit: Dict[str, Any] = {}
        self._pk_intrinsic_clearance_L_min: Dict[str, float] = {}
        self._pk_crrt_last: Dict[str, float] = {}

    @property
    def input_keys(self) -> List[str]:
        return ["ketamine_mg_kg_h", "norad_mcg_kg_min",
                "midazolam_mcg_kg_h", "propofol_mg_kg_h",
                "rocuronium_mg_kg_h", "adrenaline_mcg_kg_min",
                "dopamine_mcg_kg_min", "fentanyl_mcg_kg_h",
                "morphine_mcg_kg_h", "clonidine_mcg_kg_h", "insulin_UI_h",
                "dexmedetomidine_mcg_kg_h", "vancomycin_mg_kg_h",
                "furosemide_mg_kg", "furosemide_mg_kg_h",
                "piperacillin_mg_kg_h"]

    @property
    def output_keys(self) -> List[str]:
        return [
            "C_ketamine_mg_L", "C_norad_ng_mL",
            "C_midazolam_ng_mL", "C_propofol_mg_L",
            "C_rocuronium_ng_mL", "C_adrenaline_ng_mL",
            "C_dopamine_ng_mL", "C_fentanyl_ng_mL",
            "C_morphine_ng_mL", "C_clonidine_ng_mL", "C_insulin_mU_L", "C_piperacillin_mg_L", "C_dexmedetomidine_ng_mL", "C_vancomycin_mg_L", "C_furosemide_mg_L",
            "drug_MAP_mod", "drug_HR_mod", "drug_drive_mod",
            "drug_SVR_mod", "drug_NMB_frac", "drug_inotropy_mod",
            "pk_scaling_weight_kg", "pk_scaling_age_y",
            "pk_scaling_maturation_factor", "pk_scaling_revision",
            "pk_extension_revision", "pk_supported_drug_count",
            "pk_crrt_revision", "pk_crrt_active", "pk_crrt_effluent_L_min",
            "pk_crrt_total_extra_clearance_L_min",
            "pk_crrt_midazolam_CL_L_min", "pk_crrt_rocuronium_CL_L_min",
            "pk_crrt_vancomycin_CL_L_min", "pk_crrt_furosemide_CL_L_min",
            "pk_crrt_morphine_CL_L_min", "pk_crrt_clonidine_CL_L_min",
            "pk_crrt_insulin_CL_L_min", "pk_crrt_piperacillin_CL_L_min",
            "vancomycin_target_attainment",
            "vancomycin_coverage_mod", "vancomycin_renal_clearance_factor",
            "furosemide_effect_signal", "furosemide_diuresis_signal", "furosemide_tubular_delivery_factor", "furosemide_renal_clearance_factor",
            "ketamine_sympathomimetic_signal", "ketamine_hemodynamic_support_signal",
            "fentanyl_analgesia_signal", "fentanyl_resp_depression_signal",
            "morphine_analgesia_signal", "morphine_resp_depression_signal",
            "morphine_renal_accumulation_risk", "M6G_accumulation_proxy",
            "clonidine_sedation_signal", "clonidine_sympatholysis_signal",
            "clonidine_bradycardia_risk", "clonidine_hypotension_risk",
            "clonidine_withdrawal_mod",
            "C_insulin_mU_L", "insulin_glucose_clearance_signal",
            "insulin_potassium_shift_signal", "insulin_hypoglycemia_risk",
            "insulin_effect_revision", "insulin_effective_clearance_mmol_L_h",
            "insulin_effective_potassium_shift_mmol_L_h",
            "insulin_glucose_safety_factor", "insulin_potassium_safety_factor",
            "insulin_action_signal",
            "piperacillin_ft_above_MIC", "piperacillin_target_attainment",
            "piperacillin_kill_signal", "piperacillin_coverage_mod",
            "piperacillin_renal_clearance_factor", "piperacillin_MIC_mg_L",
        ]

    def _maturation(self) -> float:
        if not bool(self.params.get("pk_apply_maturation", True)):
            return 1.0
        return maturation_factor(
            float(self.params.get("age_y", 6.0)),
            str(self.params.get("age_group", "child")),
        )

    def _central_clearance(self, drug_prefix: str, Vd1_ref_L: float, legacy_k_s: float) -> float:
        """Ritorna CL_ref [L/min] a 20 kg da CL dichiarata o dal k legacy."""
        cl_key = f"{drug_prefix}_CL_mL_kg_min"
        cl_mL_kg_min = self.params.get(cl_key)
        ref = float(self.params.get("pk_ref_weight_kg", REF_WEIGHT_KG))
        if cl_mL_kg_min is None:
            return float(legacy_k_s) * float(Vd1_ref_L) * 60.0
        return float(cl_mL_kg_min) * ref / 1000.0

    def _scale_transfer_k(self, legacy_k_s: float, V_ref_L: float, V_scaled_L: float,
                          wt: float, ref: float) -> float:
        q_ref_L_min = float(legacy_k_s) * float(V_ref_L) * 60.0
        q_scaled = q_ref_L_min * (wt / ref) ** float(self.params.get("pk_intercompartment_exponent", 0.75))
        return k_from_clearance(q_scaled, V_scaled_L)

    def _scale_pk(self) -> None:
        """
        Crea le istanze PK con scaling allometrico trasparente.

        A 20 kg / profilo child le costanti restano praticamente identiche alla
        v1.0-alpha; nei profili piccoli la clearance/kg non resta artificiosamente
        costante, ma segue W^0.75 più maturazione età.
        """
        wt = max(float(self.params["weight_kg"]), 0.5)
        ref = max(float(self.params.get("pk_ref_weight_kg", REF_WEIGHT_KG)), 0.5)
        v_exp = float(self.params.get("pk_volume_exponent", 1.0))
        cl_exp = float(self.params.get("pk_clearance_exponent", 0.75))
        mat = _clamp(self._maturation(), 0.25, 1.25)

        def vol(per_kg: float) -> float:
            return allometric_volume(per_kg, wt, ref, v_exp)

        def vol_ref(per_kg: float) -> float:
            return allometric_volume(per_kg, ref, ref, v_exp)

        def cl(cl_ref: float) -> float:
            return allometric_clearance(cl_ref, wt, ref, cl_exp, mat)

        # Ketamina
        Vd1_k = vol(self.params["ket_Vd1_per_kg"])
        Vd2_k = vol(self.params["ket_Vd2_per_kg"])
        Vd1_k_ref = vol_ref(self.params["ket_Vd1_per_kg"])
        Vd2_k_ref = vol_ref(self.params["ket_Vd2_per_kg"])
        CL_k = cl(self._central_clearance("ket", Vd1_k_ref, self.params["ket_k10"]))
        self._pk_ket = TwoCompartmentPK(
            Vd1=Vd1_k, Vd2=Vd2_k,
            k10=k_from_clearance(CL_k, Vd1_k),
            k12=self._scale_transfer_k(self.params["ket_k12"], Vd1_k_ref, Vd1_k, wt, ref),
            k21=self._scale_transfer_k(self.params["ket_k21"], Vd2_k_ref, Vd2_k, wt, ref),
        )

        # Noradrenalina
        Vd_n = vol(self.params["nor_Vd_per_kg"])
        Vd_n_ref = vol_ref(self.params["nor_Vd_per_kg"])
        CL_n = cl(self._central_clearance("nor", Vd_n_ref, self.params["nor_k_elim"]))
        self._pk_nor = OneCompartmentPK(Vd=Vd_n, k_elim=k_from_clearance(CL_n, Vd_n))

        # Adrenalina
        Vd_a = vol(self.params["adr_Vd_per_kg"])
        Vd_a_ref = vol_ref(self.params["adr_Vd_per_kg"])
        CL_a = cl(self._central_clearance("adr", Vd_a_ref, self.params["adr_k_elim"]))
        self._pk_adr = OneCompartmentPK(Vd=Vd_a, k_elim=k_from_clearance(CL_a, Vd_a))

        # Dopamina
        Vd_dop = vol(self.params["dop_Vd_per_kg"])
        Vd_dop_ref = vol_ref(self.params["dop_Vd_per_kg"])
        CL_dop = cl(self._central_clearance("dop", Vd_dop_ref, self.params["dop_k_elim"]))
        self._pk_dop = OneCompartmentPK(Vd=Vd_dop, k_elim=k_from_clearance(CL_dop, Vd_dop))

        # Midazolam
        Vd1_m = vol(self.params["mid_Vd1_per_kg"])
        Vd2_m = vol(self.params["mid_Vd2_per_kg"])
        Vd1_m_ref = vol_ref(self.params["mid_Vd1_per_kg"])
        Vd2_m_ref = vol_ref(self.params["mid_Vd2_per_kg"])
        CL_m = cl(self._central_clearance("mid", Vd1_m_ref, self.params["mid_k10"]))
        self._pk_mid = TwoCompartmentPK(
            Vd1=Vd1_m, Vd2=Vd2_m,
            k10=k_from_clearance(CL_m, Vd1_m),
            k12=self._scale_transfer_k(self.params["mid_k12"], Vd1_m_ref, Vd1_m, wt, ref),
            k21=self._scale_transfer_k(self.params["mid_k21"], Vd2_m_ref, Vd2_m, wt, ref),
        )

        # Propofol
        Vd1_p = vol(self.params["pro_Vd1_per_kg"])
        Vd2_p = vol(self.params["pro_Vd2_per_kg"])
        Vd1_p_ref = vol_ref(self.params["pro_Vd1_per_kg"])
        Vd2_p_ref = vol_ref(self.params["pro_Vd2_per_kg"])
        CL_p = cl(self._central_clearance("pro", Vd1_p_ref, self.params["pro_k10"]))
        self._pk_pro = TwoCompartmentPK(
            Vd1=Vd1_p, Vd2=Vd2_p,
            k10=k_from_clearance(CL_p, Vd1_p),
            k12=self._scale_transfer_k(self.params["pro_k12"], Vd1_p_ref, Vd1_p, wt, ref),
            k21=self._scale_transfer_k(self.params["pro_k21"], Vd2_p_ref, Vd2_p, wt, ref),
        )

        # Rocuronio
        Vd_r = vol(self.params["roc_Vd_per_kg"])
        Vd_r_ref = vol_ref(self.params["roc_Vd_per_kg"])
        CL_r = cl(self._central_clearance("roc", Vd_r_ref, self.params["roc_k_elim"]))
        self._pk_roc = OneCompartmentPK(Vd=Vd_r, k_elim=k_from_clearance(CL_r, Vd_r))

        # Fentanyl
        Vd_f = vol(self.params["fen_Vd_per_kg"])
        Vd_f_ref = vol_ref(self.params["fen_Vd_per_kg"])
        CL_f = cl(self._central_clearance("fen", Vd_f_ref, self.params["fen_k_elim"]))
        self._pk_fen = OneCompartmentPK(Vd=Vd_f, k_elim=k_from_clearance(CL_f, Vd_f))

        # Morphine
        Vd_mor = vol(self.params["mor_Vd_per_kg"])
        Vd_mor_ref = vol_ref(self.params["mor_Vd_per_kg"])
        CL_mor = cl(self._central_clearance("mor", Vd_mor_ref, self.params["mor_k_elim"]))
        self._pk_mor = OneCompartmentPK(Vd=Vd_mor, k_elim=k_from_clearance(CL_mor, Vd_mor))

        # Clonidine
        Vd_clo = vol(self.params["clo_Vd_per_kg"])
        Vd_clo_ref = vol_ref(self.params["clo_Vd_per_kg"])
        CL_clo = cl(self._central_clearance("clo", Vd_clo_ref, self.params["clo_k_elim"]))
        self._pk_clo = OneCompartmentPK(Vd=Vd_clo, k_elim=k_from_clearance(CL_clo, Vd_clo))

        # Insulin
        Vd_ins = vol(self.params["ins_Vd_per_kg"])
        self._pk_ins = InsulinOneCompartmentPK(Vd=Vd_ins, k_elim=float(self.params["ins_k_elim"]))

        # Piperacillin/Tazobactam — renal-function dependent beta-lactam scaffold.
        Vd_pip = vol(self.params["pip_Vd_per_kg"])
        CL_pip_ref = float(self.params["pip_CL_mL_kg_min"]) * ref / 1000.0
        CL_pip_base = cl(CL_pip_ref)
        self._pk_pip = RenalDependentOneCompartmentPK(Vd=Vd_pip)
        self._pip_base_CL_L_min = float(CL_pip_base)
        self._pip_ft_above_MIC = 0.0

        # Dexmedetomidina
        Vd_dx = vol(self.params["dex_Vd_per_kg"])
        Vd_dx_ref = vol_ref(self.params["dex_Vd_per_kg"])
        CL_dx = cl(self._central_clearance("dex", Vd_dx_ref, self.params["dex_k_elim"]))
        self._pk_dex = OneCompartmentPK(Vd=Vd_dx, k_elim=k_from_clearance(CL_dx, Vd_dx))

        # Vancomicina — Vd allometrico, clearance di base allometrica;
        # la clearance effettiva viene ricalcolata dinamicamente da GFR nel step().
        Vd_van = vol(self.params["van_Vd_per_kg"])
        CL_van_ref = float(self.params["van_CL_mL_kg_min"]) * ref / 1000.0
        CL_van_base = cl(CL_van_ref)
        self._pk_van = RenalDependentOneCompartmentPK(Vd=Vd_van)
        self._van_base_CL_L_min = float(CL_van_base)

        # Furosemide — Vd allometrico, clearance renal-function dependent.
        Vd_fur = vol(self.params["fur_Vd_per_kg"])
        CL_fur_ref = float(self.params["fur_CL_mL_kg_min"]) * ref / 1000.0
        CL_fur_base = cl(CL_fur_ref)
        self._pk_fur = RenalDependentOneCompartmentPK(Vd=Vd_fur)
        self._fur_base_CL_L_min = float(CL_fur_base)
        self._last_furosemide_mg_kg_counter = 0.0

        self._pk_intrinsic_clearance_L_min = {
            "ketamine": float(CL_k),
            "noradrenaline": float(CL_n),
            "adrenaline": float(CL_a),
            "dopamine": float(CL_dop),
            "midazolam": float(CL_m),
            "propofol": float(CL_p),
            "rocuronium": float(CL_r),
            "fentanyl": float(CL_f),
            "morphine": float(CL_mor),
            "clonidine": float(CL_clo),
            "insulin": 0.0,
            "piperacillin": float(CL_pip_base),
            "dexmedetomidine": float(CL_dx),
            "vancomycin": float(CL_van_base),
            "furosemide": float(CL_fur_base),
        }
        self._pk_crrt_last = {name: 0.0 for name in self._pk_intrinsic_clearance_L_min}

        self._pk_scaling_audit = {
            "weight_kg": wt,
            "age_y": float(self.params.get("age_y", 6.0)),
            "age_group": str(self.params.get("age_group", "child")),
            "maturation_factor": mat,
            "ref_weight_kg": ref,
            "clearance_exponent": cl_exp,
            "volume_exponent": v_exp,
        }

    def initialize(self, bus: PhysiologicalBus) -> None:
        # Prende il peso dallo scenario se disponibile
        # (BusState non ha 'weight_kg', ma il param può essere passato)
        self._scale_pk()

        # Inizializza gli output a valori neutrali
        bus.update({
            "C_ketamine_mg_L":  0.0,
            "C_norad_ng_mL":    0.0,
            "C_midazolam_ng_mL": 0.0,
            "C_propofol_mg_L":  0.0,
            "C_rocuronium_ng_mL": 0.0,
            "C_adrenaline_ng_mL": 0.0,
            "C_dopamine_ng_mL": 0.0,
            "C_fentanyl_ng_mL": 0.0,
            "C_morphine_ng_mL": 0.0,
            "C_clonidine_ng_mL": 0.0,
            "C_insulin_mU_L": 0.0,
            "C_piperacillin_mg_L": 0.0,
            "C_dexmedetomidine_ng_mL": 0.0,
            "C_vancomycin_mg_L": 0.0,
            "C_furosemide_mg_L": 0.0,
            "drug_MAP_mod":     1.0,
            "drug_HR_mod":      1.0,
            "drug_drive_mod":   1.0,
            "drug_SVR_mod":     1.0,
            "drug_NMB_frac":    0.0,
            "drug_inotropy_mod": 1.0,
            "midazolam_sedation_signal": 0.0,
            "midazolam_vasodilation_signal": 0.0,
            "propofol_sedation_signal": 0.0,
            "propofol_vasodilation_signal": 0.0,
            "gaba_sedation_signal": 0.0,
            "sedative_drive_depression_signal": 0.0,
            "sedation_non_gaba_resp_signal": 0.0,
            "ketamine_sympathomimetic_signal": 0.0,
            "ketamine_hemodynamic_support_signal": 0.0,
            "pk_scaling_weight_kg": float(self._pk_scaling_audit.get("weight_kg", self.params["weight_kg"])),
            "pk_scaling_age_y": float(self._pk_scaling_audit.get("age_y", self.params.get("age_y", 6.0))),
            "pk_scaling_maturation_factor": float(self._pk_scaling_audit.get("maturation_factor", 1.0)),
            "pk_scaling_revision": 101,
            "pk_extension_revision": 117,
            "pk_supported_drug_count": 15,
            "pk_crrt_revision": 110,
            "pk_crrt_active": False,
            "pk_crrt_effluent_L_min": 0.0,
            "pk_crrt_total_extra_clearance_L_min": 0.0,
            "pk_crrt_midazolam_CL_L_min": 0.0,
            "pk_crrt_rocuronium_CL_L_min": 0.0,
            "pk_crrt_vancomycin_CL_L_min": 0.0,
            "pk_crrt_furosemide_CL_L_min": 0.0,
            "pk_crrt_morphine_CL_L_min": 0.0,
            "pk_crrt_clonidine_CL_L_min": 0.0,
            "pk_crrt_insulin_CL_L_min": 0.0,
            "pk_crrt_piperacillin_CL_L_min": 0.0,
            "vancomycin_target_attainment": 0.0,
            "vancomycin_coverage_mod": 0.0,
            "vancomycin_renal_clearance_factor": 1.0,
            "furosemide_effect_signal": 0.0,
            "furosemide_renal_clearance_factor": 1.0,
            "fentanyl_analgesia_signal": 0.0,
            "fentanyl_resp_depression_signal": 0.0,
            "morphine_analgesia_signal": 0.0,
            "morphine_resp_depression_signal": 0.0,
            "morphine_renal_accumulation_risk": 0.0,
            "M6G_accumulation_proxy": 0.0,
            "clonidine_sedation_signal": 0.0,
            "clonidine_sympatholysis_signal": 0.0,
            "clonidine_bradycardia_risk": 0.0,
            "clonidine_hypotension_risk": 0.0,
            "clonidine_withdrawal_mod": 0.0,
            "insulin_glucose_clearance_signal": 0.0,
            "insulin_potassium_shift_signal": 0.0,
            "insulin_hypoglycemia_risk": 0.0,
            "insulin_effect_revision": 319,
            "insulin_effective_clearance_mmol_L_h": 0.0,
            "insulin_effective_potassium_shift_mmol_L_h": 0.0,
            "insulin_glucose_safety_factor": 1.0,
            "insulin_potassium_safety_factor": 1.0,
            "insulin_action_signal": 0.0,
            "piperacillin_ft_above_MIC": 0.0,
            "piperacillin_target_attainment": 0.0,
            "piperacillin_kill_signal": 0.0,
            "piperacillin_coverage_mod": 0.0,
            "piperacillin_renal_clearance_factor": 1.0,
            "piperacillin_MIC_mg_L": _safe_float(getattr(bus.state, "piperacillin_MIC_mg_L", self.params.get("pip_MIC_mg_L", 16.0)), self.params.get("pip_MIC_mg_L", 16.0)),
        })

    def _crrt_extra_clearances(self, bus: PhysiologicalBus, wt: float) -> Dict[str, float]:
        """Return CRRT extra clearances [L/min] for each supported drug.

        Public educational CRRT-lite formula:
            CL_crrt = effluent_rate_L_min × sieving_coefficient
        capped as a fraction of intrinsic non-CRRT clearance to avoid implying
        drug-specific clinical dosing validity.
        """
        active = bool(getattr(bus.state, "CRRT_active", False))
        effluent_mL_kg_h = _safe_float(getattr(bus.state, "CRRT_effluent_mL_kg_h", 0.0), 0.0) if active else 0.0
        effluent_L_min = max(effluent_mL_kg_h, 0.0) * max(wt, 0.5) / 1000.0 / 60.0
        out: Dict[str, float] = {}
        for drug, intrinsic in self._pk_intrinsic_clearance_L_min.items():
            props = CRRT_DRUG_PROPERTIES.get(drug, {})
            sc = _clamp(props.get("sieving_coefficient", 0.0), 0.0, 1.0)
            max_frac = _clamp(props.get("max_fraction_intrinsic", 0.0), 0.0, 1.0)
            raw = effluent_L_min * sc
            cap = max(float(intrinsic), 0.0) * max_frac
            out[drug] = float(min(raw, cap)) if active and effluent_L_min > 0.0 else 0.0
        self._pk_crrt_last = out
        return out

    def _vancomycin_renal_factor(self, bus: PhysiologicalBus) -> float:
        """Dynamic renal-function multiplier for vancomycin clearance.

        Uses the simulated GFR relative to a profile-consistent baseline when
        available. AKI and severe shock can further reduce clearance. Bounds are
        intentionally broad enough to represent augmented renal clearance and
        severe AKI without implying dose recommendations.
        """
        current_gfr = _safe_float(getattr(bus.state, "GFR", 70.0), 70.0)
        baseline_gfr = max(_safe_float(getattr(bus.state, "GFR_baseline", 70.0), 70.0), 1.0)
        gfr_frac = _clamp(current_gfr / baseline_gfr, 0.05, 2.0)
        aki_stage = int(_clamp(_safe_float(getattr(bus.state, "AKI_stage", 0), 0), 0, 3))
        shock_penalty = 1.0 - 0.20 * _clamp((_safe_float(getattr(bus.state, "lactate", 1.0), 1.0) - 2.0) / 6.0, 0.0, 1.0)
        aki_penalty = [1.0, 0.75, 0.50, 0.25][aki_stage]
        return float(_clamp(gfr_frac * aki_penalty * shock_penalty, 0.05, 2.0))

    def _piperacillin_renal_factor(self, bus: PhysiologicalBus) -> float:
        """Dynamic renal-function multiplier for piperacillin clearance.

        Piperacillin is represented as a predominantly renal beta-lactam.
        Simulated GFR, AKI stage and shock burden modify clearance so that
        augmented clearance and organ failure can be explored qualitatively.
        """
        current_gfr = _safe_float(getattr(bus.state, "GFR", 70.0), 70.0)
        baseline_gfr = max(_safe_float(getattr(bus.state, "GFR_baseline", 70.0), 70.0), 1.0)
        gfr_frac = _clamp(current_gfr / baseline_gfr, 0.05, 2.5)
        aki_stage = int(_clamp(_safe_float(getattr(bus.state, "AKI_stage", 0), 0), 0, 3))
        shock_penalty = 1.0 - 0.20 * _clamp((_safe_float(getattr(bus.state, "lactate", 1.0), 1.0) - 2.0) / 6.0, 0.0, 1.0)
        aki_penalty = [1.0, 0.70, 0.45, 0.25][aki_stage]
        return float(_clamp(gfr_frac * aki_penalty * shock_penalty, 0.05, 2.5))

    def _furosemide_renal_factor(self, bus: PhysiologicalBus) -> float:
        """Dynamic renal-function multiplier for furosemide clearance/effect.

        Furosemide reaches the tubular lumen through renal handling. This public
        scaffold therefore ties both clearance and PD response to simulated GFR,
        AKI stage and shock burden. It is intentionally qualitative.
        """
        current_gfr = _safe_float(getattr(bus.state, "GFR", 70.0), 70.0)
        baseline_gfr = max(_safe_float(getattr(bus.state, "GFR_baseline", 70.0), 70.0), 1.0)
        gfr_frac = _clamp(current_gfr / baseline_gfr, 0.02, 2.0)
        aki_stage = int(_clamp(_safe_float(getattr(bus.state, "AKI_stage", 0), 0), 0, 3))
        shock_penalty = 1.0 - 0.30 * _clamp((_safe_float(getattr(bus.state, "lactate", 1.0), 1.0) - 2.0) / 6.0, 0.0, 1.0)
        aki_penalty = [1.0, 0.60, 0.35, 0.15][aki_stage]
        return float(_clamp(gfr_frac * aki_penalty * shock_penalty, 0.02, 2.0))


    def _morphine_renal_metabolite_factor(self, bus: PhysiologicalBus) -> float:
        """Renal clearance proxy for morphine glucuronide metabolites.

        Parent morphine is primarily handled by hepatic glucuronidation in this
        scaffold, while the active M6G-like burden is treated as renally cleared.
        The output is qualitative and exists to teach why renal impairment/CRRT
        matter during prolonged morphine exposure.
        """
        current_gfr = _safe_float(getattr(bus.state, "GFR", 70.0), 70.0)
        baseline_gfr = max(_safe_float(getattr(bus.state, "GFR_baseline", 70.0), 70.0), 1.0)
        gfr_frac = _clamp(current_gfr / baseline_gfr, 0.05, 2.0)
        aki_stage = int(_clamp(_safe_float(getattr(bus.state, "AKI_stage", 0), 0), 0, 3))
        aki_penalty = [1.0, 0.70, 0.45, 0.20][aki_stage]
        return float(_clamp(gfr_frac * aki_penalty, 0.05, 2.0))

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        wt = float(self.params["weight_kg"])

        # --- 1. Lettura dosi dal Bus ---
        ket_dose  = bus.get("ketamine_mg_kg_h")   * wt / 60.0  # mg/min
        nor_dose  = bus.get("norad_mcg_kg_min")   * wt / 1000.0  # mg/min (da mcg)
        mid_dose  = bus.get("midazolam_mcg_kg_h") * wt / 1000.0 / 60.0  # mg/min
        pro_dose  = bus.get("propofol_mg_kg_h")   * wt / 60.0   # mg/min
        roc_dose  = bus.get("rocuronium_mg_kg_h") * wt / 60.0   # mg/min
        adr_dose  = bus.get("adrenaline_mcg_kg_min") * wt / 1000.0  # mg/min
        dop_dose  = bus.get("dopamine_mcg_kg_min") * wt / 1000.0    # mg/min
        fen_dose  = bus.get("fentanyl_mcg_kg_h") * wt / 1000.0 / 60.0  # mg/min
        mor_dose  = bus.get("morphine_mcg_kg_h") * wt / 1000.0 / 60.0  # mg/min
        clo_dose  = bus.get("clonidine_mcg_kg_h") * wt / 1000.0 / 60.0  # mg/min
        ins_dose_U_h = bus.get("insulin_UI_h") if hasattr(bus.state, "insulin_UI_h") else 0.0
        pip_dose  = bus.get("piperacillin_mg_kg_h") * wt / 60.0  # mg/min, piperacillin component
        dex_dose  = bus.get("dexmedetomidine_mcg_kg_h") * wt / 1000.0 / 60.0  # mg/min
        van_dose  = bus.get("vancomycin_mg_kg_h") * wt / 60.0  # mg/min
        fur_infusion_dose = bus.get("furosemide_mg_kg_h") * wt / 60.0  # mg/min
        fur_counter = bus.get("furosemide_mg_kg")
        d_fur_mg_kg = max(float(fur_counter) - float(self._last_furosemide_mg_kg_counter), 0.0)
        self._last_furosemide_mg_kg_counter = float(fur_counter)
        fur_bolus_rate = (d_fur_mg_kg * wt) / max(float(dt) / 60.0, 1e-9) if d_fur_mg_kg > 0.0 else 0.0
        fur_dose = fur_infusion_dose + fur_bolus_rate

        # --- 2. Step PK ---
        crrt_cl = self._crrt_extra_clearances(bus, wt)
        self._pk_ket.step(ket_dose, dt, crrt_cl.get("ketamine", 0.0))
        self._pk_nor.step(nor_dose, dt, crrt_cl.get("noradrenaline", 0.0))
        self._pk_mid.step(mid_dose, dt, crrt_cl.get("midazolam", 0.0))
        self._pk_pro.step(pro_dose, dt, crrt_cl.get("propofol", 0.0))
        self._pk_roc.step(roc_dose, dt, crrt_cl.get("rocuronium", 0.0))
        self._pk_adr.step(adr_dose, dt, crrt_cl.get("adrenaline", 0.0))
        self._pk_dop.step(dop_dose, dt, crrt_cl.get("dopamine", 0.0))
        self._pk_fen.step(fen_dose, dt, crrt_cl.get("fentanyl", 0.0))
        self._pk_mor.step(mor_dose, dt, crrt_cl.get("morphine", 0.0))
        self._pk_clo.step(clo_dose, dt, crrt_cl.get("clonidine", 0.0))
        self._pk_ins.step(ins_dose_U_h, dt)
        pip_renal_factor = self._piperacillin_renal_factor(bus)
        pip_CL_dynamic = self._pip_base_CL_L_min * pip_renal_factor
        self._pk_pip.step(pip_dose, dt, pip_CL_dynamic, crrt_cl.get("piperacillin", 0.0))
        self._pk_dex.step(dex_dose, dt, crrt_cl.get("dexmedetomidine", 0.0))
        van_renal_factor = self._vancomycin_renal_factor(bus)
        van_CL_dynamic = self._van_base_CL_L_min * van_renal_factor
        self._pk_van.step(van_dose, dt, van_CL_dynamic, crrt_cl.get("vancomycin", 0.0))
        fur_renal_factor = self._furosemide_renal_factor(bus)
        fur_CL_dynamic = self._fur_base_CL_L_min * fur_renal_factor
        self._pk_fur.step(fur_dose, dt, fur_CL_dynamic, crrt_cl.get("furosemide", 0.0))

        # --- 3. Concentrazioni plasmatiche ---
        C_ket = self._pk_ket.C_plasma          # mg/L
        C_nor = self._pk_nor.C_plasma * 1000.0  # mg/L → ng/mL (÷ Vd già in L)
        # Nota: nor è in mg/L nello step, convertiamo per PD
        C_nor_mgL = self._pk_nor.C_plasma       # mg/L
        C_nor_ngmL = C_nor_mgL * 1000.0         # ng/mL
        C_mid = self._pk_mid.C_plasma * 1000.0  # mg/L → ng/mL
        C_pro = self._pk_pro.C_plasma            # mg/L
        C_adr_ngmL = self._pk_adr.C_plasma * 1000.0
        C_dop_ngmL = self._pk_dop.C_plasma * 1000.0
        C_fen_ngmL = self._pk_fen.C_plasma * 1000.0
        C_mor_ngmL = self._pk_mor.C_plasma * 1000.0
        C_clo_ngmL = self._pk_clo.C_plasma * 1000.0
        C_ins_mUL = self._pk_ins.C_plasma
        C_pip_mgL = self._pk_pip.C_plasma
        C_dex_ngmL = self._pk_dex.C_plasma * 1000.0
        C_van_mgL = self._pk_van.C_plasma
        C_fur_mgL = self._pk_fur.C_plasma

        # --- 4. Effetti PD (Hill equation) ---

        # KETAMINA — dissociative sedative/analgesic with limited direct
        # respiratory depression in this educational scaffold. Respiratory
        # depression is intentionally not added to drug_drive_mod; analgesia and
        # dissociation are handled by PainStressSedationModule.
        E_ket_HR  = hill(C_ket, self.params["ket_EC50_sed"],
                         self.params["ket_Emax_HR"], self.params["ket_n"])
        E_ket_MAP = hill(C_ket, self.params["ket_EC50_sed"],
                         self.params["ket_Emax_MAP"], self.params["ket_n"])
        E_ket_sym = hill(C_ket, self.params["ket_EC50_sed"],
                         1.0, self.params["ket_n"])

        # NORADRENALINA — vascular tone is handled by Circulation.
        # Keep only a small concentration-linked baroreflex/bradycardic signal.
        E_nor_HR  = hill(C_nor_ngmL, self.params["nor_EC50_vaso"],
                         abs(self.params["nor_Emax_HR"]),
                         1.0)

        # MIDAZOLAM — sedazione → riduce drive respiratorio (GABA)
        E_mid_sed = hill(C_mid, self.params["mid_EC50_sed"],
                         self.params["mid_Emax_sed"], self.params["mid_n"])
        E_mid_vaso = hill(C_mid, self.params["mid_EC50_sed"],
                          self.params["mid_Emax_vaso"], self.params["mid_n"])

        # PROPOFOL — sedazione profonda + vasodilatazione
        E_pro_sed  = hill(C_pro, self.params["pro_EC50_sed"],
                          self.params["pro_Emax_sed"], self.params["pro_n"])
        E_pro_vaso = hill(C_pro, self.params["pro_EC50_sed"],
                          self.params["pro_Emax_vaso"], self.params["pro_n"])
        E_pro_HR   = hill(C_pro, self.params["pro_EC50_sed"],
                          abs(self.params["pro_Emax_HR"]), self.params["pro_n"])

        # ROCURONIO — neuromuscular blockade only.
        # Step 3.5 contract: rocuronium blocks motor output/triggering through
        # drug_NMB_frac. It must not be treated as a sedative or as an automatic
        # oxygenation/ventilation improvement; it does not improve gas exchange by itself.
        # Conversione corretta: 1 mg/L = 1000 mcg/L = 1000 ng/mL
        # (non 1e6: quella sarebbe la conversione mg/L → pg/mL)
        C_roc_ngmL = self._pk_roc.C_plasma * 1000.0   # mg/L → ng/mL
        E_roc_NMB = hill(C_roc_ngmL, self.params["roc_EC50_NMB"],
                         1.0, self.params["roc_n_NMB"])

        # ADRENALINA / DOPAMINA — vasoattivi e inotropi qualitativi
        E_adr_HR = hill(C_adr_ngmL, self.params["adr_EC50_vaso"],
                        self.params["adr_Emax_HR"], 1.2)
        E_adr_MAP = hill(C_adr_ngmL, self.params["adr_EC50_vaso"],
                         self.params["adr_Emax_MAP"], 1.1)
        E_adr_CO = hill(C_adr_ngmL, self.params["adr_EC50_vaso"],
                        self.params["adr_Emax_CO"], 1.1)
        E_dop_HR = hill(C_dop_ngmL, self.params["dop_EC50_inotropy"],
                        self.params["dop_Emax_HR"], 1.2)
        E_dop_MAP = hill(C_dop_ngmL, self.params["dop_EC50_inotropy"],
                         self.params["dop_Emax_MAP"], 1.1)
        E_dop_CO = hill(C_dop_ngmL, self.params["dop_EC50_inotropy"],
                        self.params["dop_Emax_CO"], 1.1)

        # FENTANYL / MORPHINE — PK-owned concentration and audit PD signals.
        # Step 3.4A: opioid respiratory-drive coupling is owned by
        # PainStressSedationModule via sed_resp_mod/opioid_resp_depression.
        # PharmacologyModule exposes signals but no longer depresses drug_drive_mod
        # directly, avoiding duplicate respiratory depression.
        E_fen_anal = hill(C_fen_ngmL, self.params["fen_EC50_anal"], 0.85, 1.3)
        E_fen_resp = hill(C_fen_ngmL, self.params["fen_EC50_resp"], 0.55, 1.4)
        E_mor_anal = hill(C_mor_ngmL, self.params["mor_EC50_anal"], self.params["mor_Emax_anal"], 1.2)
        E_mor_resp = hill(C_mor_ngmL, self.params["mor_EC50_resp"], self.params["mor_Emax_resp"], 1.2)
        mor_metab_factor = self._morphine_renal_metabolite_factor(bus)
        mor_accumulation_risk = float(np.clip((C_mor_ngmL / max(float(self.params["mor_EC50_resp"]), 1e-6)) * (1.0 / max(mor_metab_factor, 0.05) - 0.5), 0.0, 1.0))
        M6G_proxy = float(np.clip(C_mor_ngmL * (0.20 + 0.80 * mor_accumulation_risk), 0.0, 500.0))
        E_clo_sed = hill(C_clo_ngmL, self.params["clo_EC50_sed"], self.params["clo_Emax_sed"], 1.4)
        E_clo_hemo = hill(C_clo_ngmL, self.params["clo_EC50_hemo"], self.params["clo_Emax_hemo"], 1.3)
        E_clo_withdrawal = hill(C_clo_ngmL, self.params["clo_EC50_sed"], self.params["clo_Emax_withdrawal"], 1.2)
        E_dex_sed = hill(C_dex_ngmL, self.params["dex_EC50_sed"], 0.70, 1.7)
        E_dex_hemo = hill(C_dex_ngmL, self.params["dex_EC50_hemo"], 0.22, 1.6)

        # INSULIN — qualitative glucose and potassium uptake signal
        E_ins_glucose = hill(C_ins_mUL, self.params["ins_EC50_glucose_mU_L"],
                             self.params["ins_Emax_glucose"], 1.35)
        E_ins_K = hill(C_ins_mUL, self.params["ins_EC50_K_mU_L"],
                       self.params["ins_Emax_K"], 1.20)
        current_glucose = _safe_float(getattr(bus.state, "glucose_mmol_L", 5.0), 5.0)
        current_K = _safe_float(getattr(bus.state, "K_mmol_L", 4.0), 4.0)
        # Step 3.9: insulin dose is translated into delayed PK/PD signals.
        # GlucoseModule owns final glucose; AcidBaseElectrolyteModule owns final K.
        # Safety factors taper the effect near hypoglycemia/hypokalemia so insulin
        # does not behave like an instantaneous numeric override.
        glucose_safety = float(np.clip((current_glucose - 2.8) / 5.2, 0.0, 1.0))
        potassium_safety = float(np.clip((current_K - 2.8) / 1.7, 0.0, 1.0))
        insulin_hypo_risk = float(np.clip(E_ins_glucose * (1.0 - glucose_safety), 0.0, 1.0))
        insulin_effective_clearance = float(np.clip(
            float(self.params.get("ins_max_clearance_mmol_L_h", 4.0)) * E_ins_glucose * glucose_safety, 0.0, 6.0))
        insulin_effective_K_shift = float(np.clip(
            float(self.params.get("ins_max_potassium_shift_mmol_L_h", 0.65)) * E_ins_K * potassium_safety, 0.0, 1.0))
        insulin_action_signal = float(np.clip(max(E_ins_glucose, E_ins_K), 0.0, 1.0))

        # VANCOMICINA — qualitative PK/PD target attainment and coverage contribution
        van_MIC = max(float(self.params.get("van_MIC_mg_L", 1.0)), 0.05)
        van_ratio = C_van_mgL / van_MIC
        van_target = hill(van_ratio, float(self.params.get("van_EC50_multiple_MIC", 4.0)), 1.0, 1.4)
        van_coverage = float(self.params.get("van_Emax_coverage", 0.85)) * van_target

        # PIPERACILLIN/TAZOBACTAM — qualitative time-dependent beta-lactam effect
        pip_MIC = max(_safe_float(getattr(bus.state, "piperacillin_MIC_mg_L", self.params.get("pip_MIC_mg_L", 16.0)), self.params.get("pip_MIC_mg_L", 16.0)), 0.05)
        pip_above = 1.0 if C_pip_mgL >= pip_MIC else 0.0
        pip_tau = max(float(self.params.get("pip_ft_memory_tau_s", 3600.0)), 60.0)
        pip_alpha = float(np.clip(float(dt) / pip_tau, 0.0, 1.0))
        self._pip_ft_above_MIC = float(np.clip(self._pip_ft_above_MIC + pip_alpha * (pip_above - self._pip_ft_above_MIC), 0.0, 1.0))
        pip_target = hill(self._pip_ft_above_MIC, float(self.params.get("pip_target_fT_MIC", 0.50)), 1.0, 2.0)
        taz_support = _clamp(float(self.params.get("taz_beta_lactamase_support", 0.20)), 0.0, 0.4)
        pip_coverage = float(self.params.get("pip_Emax_coverage", 0.85)) * pip_target * (1.0 + taz_support)
        pip_kill = float(np.clip(pip_target * (0.50 + 0.50 * min(C_pip_mgL / max(pip_MIC, 1e-9), 2.0) / 2.0), 0.0, 1.0))

        # FUROSEMIDE — qualitative concentration-effect signal for renal modules
        fur_pd_raw = hill(C_fur_mgL,
                         float(self.params.get("fur_EC50_diuresis_mg_L", 1.0)),
                         float(self.params.get("fur_Emax_diuresis", 1.0)),
                         float(self.params.get("fur_n_diuresis", 1.35)))
        fur_effect_signal = float(np.clip(fur_pd_raw * fur_renal_factor, 0.0, 1.0))

        # --- 5. Composizione effetti ---
        # MAP modifier: sedatives/ketamine only. Step 3.3 removes direct
        # catecholamine MAP effects here to avoid double-counting with
        # CirculationModule vasoactive tone.
        MAP_mod = 1.0 + E_ket_MAP - E_pro_vaso * 0.3 - E_mid_vaso * 0.2

        # HR modifier: ketamina/adrenalina/dopamina +, propofol/norad -.
        # Step 3.4D removes alpha-2 bradycardia from drug_HR_mod to avoid
        # duplicate HR suppression with PainStressSedationModule.sed_HR_mod.
        HR_mod = 1.0 + E_ket_HR + E_adr_HR + E_dop_HR - E_pro_HR - E_nor_HR

        # Drive modifier: GABA sedatives only.
        # Step 3.4A keeps opioid respiratory depression in sed_resp_mod, written by
        # PainStressSedationModule, so fentanyl/morphine are not applied twice.
        # Step 3.4B keeps midazolam/propofol respiratory-drive depression here
        # only. Step 3.4C explicitly keeps ketamine out of this pathway.
        # Step 3.4D keeps alpha-2 agonists out of drug_drive_mod; dexmedetomidine
        # and clonidine provide cooperative sedation/sympatholysis audit signals
        # and hemodynamic coupling through PainStressSedationModule, not primary
        # respiratory-drive depression.
        # 1.0 = drive normale, 0 = apnea.
        gaba_sed = 1.0 - (1.0 - E_mid_sed) * (1.0 - E_pro_sed)
        alpha2_sedation_signal = 1.0 - (1.0 - E_dex_sed) * (1.0 - E_clo_sed)
        alpha2_sympatholysis_signal = 1.0 - (1.0 - E_dex_hemo) * (1.0 - E_clo_hemo)
        drive_depression = 1.0 - (1.0 - 0.70 * E_mid_sed) * (1.0 - 0.80 * E_pro_sed)
        drive_mod = max((1.0 - drive_depression), 0.02)

        # SVR modifier (farmaci vasoattivi/sedativi). Step 3.4D removes
        # alpha-2 sympatholysis from drug_SVR_mod to avoid double counting with
        # PainStressSedationModule.sed_SVR_mod.
        SVR_mod = 1.0 - E_pro_vaso * 0.30 - E_mid_vaso * 0.15
        # Inotropy is consumed by HeartModule from v3.1 Step 3.3 onward.
        inotropy_mod = 1.0 + E_adr_CO + E_dop_CO

        # --- 6. Scrittura nel Bus ---
        bus.update({
            "C_ketamine_mg_L":    float(C_ket),
            "C_norad_ng_mL":      float(C_nor_ngmL),
            "C_midazolam_ng_mL":  float(C_mid),
            "C_propofol_mg_L":    float(C_pro),
            "C_rocuronium_ng_mL": float(C_roc_ngmL),
            "C_adrenaline_ng_mL": float(C_adr_ngmL),
            "C_dopamine_ng_mL": float(C_dop_ngmL),
            "C_fentanyl_ng_mL": float(C_fen_ngmL),
            "C_morphine_ng_mL": float(C_mor_ngmL),
            "C_clonidine_ng_mL": float(C_clo_ngmL),
            "C_insulin_mU_L": float(C_ins_mUL),
            "C_piperacillin_mg_L": float(C_pip_mgL),
            "C_dexmedetomidine_ng_mL": float(C_dex_ngmL),
            "C_vancomycin_mg_L": float(C_van_mgL),
            "C_furosemide_mg_L": float(C_fur_mgL),
            "drug_MAP_mod":   float(np.clip(MAP_mod,   0.5, 2.0)),
            "drug_HR_mod":    float(np.clip(HR_mod,    0.5, 2.0)),
            "drug_drive_mod": float(np.clip(drive_mod, 0.0, 1.5)),
            "drug_SVR_mod":   float(np.clip(SVR_mod,   0.3, 1.2)),
            "drug_NMB_frac":  float(np.clip(E_roc_NMB, 0.0, 1.0)),
            "drug_inotropy_mod": float(np.clip(inotropy_mod, 1.0, 1.4)),
            "rocuronium_nmb_signal": float(np.clip(E_roc_NMB, 0.0, 1.0)),
            "neuromuscular_blockade_active": bool(E_roc_NMB >= 0.90),
            "spontaneous_effort_available": float(np.clip(1.0 - E_roc_NMB, 0.0, 1.0)),
            "nmb_trigger_block_active": bool(E_roc_NMB >= 0.90),
            "midazolam_sedation_signal": float(np.clip(E_mid_sed, 0.0, 1.0)),
            "midazolam_vasodilation_signal": float(np.clip(E_mid_vaso, 0.0, 1.0)),
            "propofol_sedation_signal": float(np.clip(E_pro_sed, 0.0, 1.0)),
            "propofol_vasodilation_signal": float(np.clip(E_pro_vaso, 0.0, 1.0)),
            "gaba_sedation_signal": float(np.clip(gaba_sed, 0.0, 1.0)),
            "sedative_drive_depression_signal": float(np.clip(drive_depression, 0.0, 1.0)),
            "ketamine_sympathomimetic_signal": float(np.clip(E_ket_sym, 0.0, 1.0)),
            "ketamine_hemodynamic_support_signal": float(np.clip(E_ket_sym, 0.0, 1.0)),
            "pk_scaling_weight_kg": float(self._pk_scaling_audit.get("weight_kg", wt)),
            "pk_scaling_age_y": float(self._pk_scaling_audit.get("age_y", self.params.get("age_y", 6.0))),
            "pk_scaling_maturation_factor": float(self._pk_scaling_audit.get("maturation_factor", 1.0)),
            "pk_scaling_revision": 101,
            "pk_extension_revision": 117,
            "pk_supported_drug_count": 15,
            "pk_crrt_revision": 110,
            "pk_crrt_active": bool(getattr(bus.state, "CRRT_active", False) and _safe_float(getattr(bus.state, "CRRT_effluent_mL_kg_h", 0.0)) > 0.0),
            "pk_crrt_effluent_L_min": float(_safe_float(getattr(bus.state, "CRRT_effluent_mL_kg_h", 0.0)) * wt / 1000.0 / 60.0) if bool(getattr(bus.state, "CRRT_active", False)) else 0.0,
            "pk_crrt_total_extra_clearance_L_min": float(sum(self._pk_crrt_last.values())),
            "pk_crrt_midazolam_CL_L_min": float(self._pk_crrt_last.get("midazolam", 0.0)),
            "pk_crrt_rocuronium_CL_L_min": float(self._pk_crrt_last.get("rocuronium", 0.0)),
            "pk_crrt_vancomycin_CL_L_min": float(self._pk_crrt_last.get("vancomycin", 0.0)),
            "pk_crrt_furosemide_CL_L_min": float(self._pk_crrt_last.get("furosemide", 0.0)),
            "pk_crrt_morphine_CL_L_min": float(self._pk_crrt_last.get("morphine", 0.0)),
            "pk_crrt_clonidine_CL_L_min": float(self._pk_crrt_last.get("clonidine", 0.0)),
            "pk_crrt_insulin_CL_L_min": float(self._pk_crrt_last.get("insulin", 0.0)),
            "pk_crrt_piperacillin_CL_L_min": float(self._pk_crrt_last.get("piperacillin", 0.0)),
            "vancomycin_target_attainment": float(np.clip(van_target, 0.0, 1.0)),
            "vancomycin_coverage_mod": float(np.clip(van_coverage, 0.0, 1.0)),
            "vancomycin_renal_clearance_factor": float(van_renal_factor),
            "furosemide_effect_signal": float(fur_effect_signal),
            "furosemide_diuresis_signal": float(fur_effect_signal),
            "furosemide_tubular_delivery_factor": float(fur_renal_factor),
            "furosemide_renal_clearance_factor": float(fur_renal_factor),
            "fentanyl_analgesia_signal": float(np.clip(E_fen_anal, 0.0, 1.0)),
            "fentanyl_resp_depression_signal": float(np.clip(E_fen_resp, 0.0, 1.0)),
            "morphine_analgesia_signal": float(np.clip(E_mor_anal, 0.0, 1.0)),
            "morphine_resp_depression_signal": float(np.clip(E_mor_resp, 0.0, 1.0)),
            "morphine_renal_accumulation_risk": float(mor_accumulation_risk),
            "M6G_accumulation_proxy": float(M6G_proxy),
            "dexmedetomidine_sedation_signal": float(np.clip(E_dex_sed, 0.0, 1.0)),
            "dexmedetomidine_sympatholysis_signal": float(np.clip(E_dex_hemo, 0.0, 1.0)),
            "dexmedetomidine_bradycardia_risk": float(np.clip(E_dex_hemo / 0.22, 0.0, 1.0)),
            "dexmedetomidine_hypotension_risk": float(np.clip((E_dex_hemo / 0.22) * max(65.0 - float(getattr(bus.state, "MAP", 65.0)), 0.0) / 30.0, 0.0, 1.0)),
            "clonidine_sedation_signal": float(np.clip(E_clo_sed, 0.0, 1.0)),
            "clonidine_sympatholysis_signal": float(np.clip(E_clo_hemo, 0.0, 1.0)),
            "clonidine_bradycardia_risk": float(np.clip(E_clo_hemo / max(float(self.params["clo_Emax_hemo"]), 1e-6), 0.0, 1.0)),
            "clonidine_hypotension_risk": float(np.clip((E_clo_hemo / max(float(self.params["clo_Emax_hemo"]), 1e-6)) * max(65.0 - float(getattr(bus.state, "MAP", 65.0)), 0.0) / 30.0, 0.0, 1.0)),
            "clonidine_withdrawal_mod": float(np.clip(E_clo_withdrawal, 0.0, 1.0)),
            "alpha2_sedation_signal": float(np.clip(alpha2_sedation_signal, 0.0, 1.0)),
            "alpha2_sympatholysis_signal": float(np.clip(alpha2_sympatholysis_signal, 0.0, 1.0)),
            "insulin_glucose_clearance_signal": float(np.clip(E_ins_glucose, 0.0, 1.0)),
            "insulin_potassium_shift_signal": float(np.clip(E_ins_K, 0.0, 1.0)),
            "insulin_hypoglycemia_risk": float(insulin_hypo_risk),
            "insulin_effect_revision": 319,
            "insulin_effective_clearance_mmol_L_h": float(insulin_effective_clearance),
            "insulin_effective_potassium_shift_mmol_L_h": float(insulin_effective_K_shift),
            "insulin_glucose_safety_factor": float(glucose_safety),
            "insulin_potassium_safety_factor": float(potassium_safety),
            "insulin_action_signal": float(insulin_action_signal),
            "piperacillin_ft_above_MIC": float(np.clip(self._pip_ft_above_MIC, 0.0, 1.0)),
            "piperacillin_target_attainment": float(np.clip(pip_target, 0.0, 1.0)),
            "piperacillin_kill_signal": float(np.clip(pip_kill, 0.0, 1.0)),
            "piperacillin_coverage_mod": float(np.clip(pip_coverage, 0.0, 1.0)),
            "piperacillin_renal_clearance_factor": float(pip_renal_factor),
            "piperacillin_MIC_mg_L": float(pip_MIC),
            "antibiotic_started": bool(getattr(bus.state, "antibiotic_started", False) or van_dose > 0.0 or C_van_mgL > 0.5 or pip_dose > 0.0 or C_pip_mgL > 0.5),
            "antibiotic_coverage": float(max(np.clip(getattr(bus.state, "antibiotic_coverage", 0.0), 0.0, 1.0), np.clip(van_coverage, 0.0, 1.0), np.clip(pip_coverage, 0.0, 1.0))),
        })
