"""
Gas Exchange Module
===================
Public educational gas-exchange model for pediatric critical-care simulation.

v1.06 introduced a transparent three-zone V/Q scaffold: non-ventilated
shunt, ventilated non-perfused dead space, and a ventilated-perfused exchange
zone with log-normal V/Q dispersion. v1.20 adds pathology-adaptive dispersion:
ARDS-like derecruitment, obstructive air trapping, sepsis/shock perfusion stress
and neonatal/RDS-like physiology can now shift shunt, dead space and sigma in a
transparent educational way. The model is qualitative and pedagogical. It is not
patient-specific, not externally validated, and not intended for clinical decision
support.
"""

from __future__ import annotations
import numpy as np
from typing import List

from core.base_module import BaseModule
from core.bus import PhysiologicalBus
from core.profile_scaling import bus_patient_scalars


# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

PATM_CMHG = 760.0     # atmospheric pressure [mmHg]
PH2O_37 = 47.0        # water vapour pressure at 37 deg C [mmHg]
O2_CAPACITY = 1.34    # Hb-bound O2 capacity [mL O2/g Hb]
HENRY_O2 = 0.003      # physically dissolved O2 [mL O2/dL/mmHg]


# ---------------------------------------------------------------------------
# Oxyhaemoglobin dissociation helpers
# ---------------------------------------------------------------------------

def _sat_from_po2(PO2: float, pH: float = 7.40, T: float = 37.0, PaCO2: float = 40.0) -> float:
    """Return Hb oxygen saturation from PO2 [mmHg] using a compact Hill curve."""
    delta_pH = pH - 7.40
    delta_T = T - 37.0
    P50_corr = 26.3 * (10 ** (-0.48 * delta_pH)) * (10 ** (0.024 * delta_T))
    n = 2.7
    if PO2 <= 0:
        return 0.0
    sat = PO2**n / (P50_corr**n + PO2**n)
    return float(np.clip(sat, 0.0, 1.0))


def _po2_from_sat(sat: float, pH: float = 7.40, T: float = 37.0) -> float:
    """Return PO2 [mmHg] from Hb saturation using the inverse compact Hill curve."""
    if sat <= 0:
        return 0.0
    if sat >= 0.999:
        return 500.0
    delta_pH = pH - 7.40
    delta_T = T - 37.0
    P50_corr = 26.3 * (10 ** (-0.48 * delta_pH)) * (10 ** (0.024 * delta_T))
    n = 2.7
    return float(P50_corr * (sat / (1.0 - sat)) ** (1.0 / n))


def _o2_content_from_po2(PO2: float, Hb: float, pH: float, T: float) -> float:
    """Blood oxygen content [mL/dL] from PO2, Hb, pH and temperature."""
    sat = _sat_from_po2(PO2, pH=pH, T=T)
    return float(Hb * O2_CAPACITY * sat + HENRY_O2 * PO2)


def _po2_from_o2_content(content: float, Hb: float, pH: float, T: float) -> float:
    """Invert oxygen content to PO2 [mmHg] by monotonic bisection."""
    target = float(max(content, 0.0))
    lo, hi = 0.01, 650.0
    for _ in range(42):
        mid = 0.5 * (lo + hi)
        val = _o2_content_from_po2(mid, Hb=Hb, pH=pH, T=T)
        if val < target:
            lo = mid
        else:
            hi = mid
    return float(np.clip(0.5 * (lo + hi), 0.0, 650.0))


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------

class GasExchangeModule(BaseModule):
    """
    Public three-zone V/Q gas exchange scaffold.

    Zones
    -----
    1. Shunt: perfused but not ventilated. Venous O2 content enters arterial mix.
    2. Dead space: ventilated but poorly/non-perfused. It reduces effective alveolar
       ventilation for CO2 clearance but does not contribute capillary O2 content.
    3. Exchange zone: ventilated and perfused. A small set of log-normal V/Q bins
       represents low, normal and high V/Q heterogeneity.

    This is a transparent educational model. It preserves qualitative physiology
    and numerical stability, but it is not an externally validated patient model.
    """

    DEFAULT_PARAMS = {
        "Qs_Qt": 0.035,
        "Vd_Vt": 0.22,
        "RQ": 0.85,
        "pK_H": 6.10,
        "alpha_CO2": 0.0307,      # mmol/L/mmHg
        "HCO3_baseline": 24.0,    # mmol/L
        "tau_gas_s": 15.0,        # gas equilibration time constant [s]
        "vq_sigma_base": 0.28,    # log-normal dispersion in the exchange zone
        "vq_sigma_recruitment_gain": 0.60,
        "vq_adaptive_enabled": True,
        "vq_ards_sigma_gain": 0.35,
        "vq_obstruction_sigma_gain": 0.40,
        "vq_shock_sigma_gain": 0.25,
        "vq_neonatal_sigma_gain": 0.20,
        "vq_ards_shunt_gain": 0.10,
        "vq_shock_shunt_gain": 0.05,
        "vq_neonatal_shunt_gain": 0.075,
        "vq_obstruction_deadspace_gain": 0.17,
        "vq_shock_deadspace_gain": 0.06,
        "vq_bins": 9,
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="GasExchange", params=merged)

        self._PaO2: float = 90.0
        self._PaCO2: float = 40.0
        self._EtCO2: float = 35.0
        self._SaO2: float = 0.97
        self._pH: float = 7.40
        self._HCO3: float = 24.0

    @property
    def input_keys(self) -> List[str]:
        return [
            "FiO2", "RR", "RR_total", "Vt", "EELV", "recruited_frac",
            "Hb", "CO", "VO2", "T_core", "Ppl", "ino_Qs_Qt_mod",
            "respiratory_quotient", "VCO2_mod", "airway_shunt_add",
            "airway_VdVt_add", "air_trapping_index", "airway_obstruction_index",
            "sepsis_severity_score", "infection_severity_score", "lactate",
            "weight_kg", "age_y", "FiO2_delivered", "HFNC_deadspace_washout",
            "NIV_deadspace_washout", "tube_VdVt_add",
        ]

    @property
    def output_keys(self) -> List[str]:
        return [
            "PaO2", "PaCO2", "EtCO2", "EtCO2_proxy", "etco2_pa_gradient",
            "etco2_perfusion_factor", "etco2_deadspace_factor", "etco2_source",
            "SaO2", "PvO2", "SvO2", "ScvO2", "ScvO2_source", "ScvO2_revision", "DO2", "ERO2",
            "vq_shunt_frac", "vq_deadspace_frac", "vq_exchange_frac",
            "vq_logsd", "vq_adaptive_sigma", "vq_ards_weight",
            "vq_obstruction_weight", "vq_shock_weight", "vq_neonatal_weight",
            "vq_pathology_driver", "vq_low_vq_burden", "vq_high_vq_burden",
            "alveolar_ventilation_L_min", "gas_exchange_revision", "vq_adaptive_revision",
            "FiO2_delivered",
        ]

    def initialize(self, bus: PhysiologicalBus) -> None:
        self._PaO2 = float(bus.get("PaO2"))
        self._PaCO2 = float(bus.get("PaCO2"))
        self._EtCO2 = float(getattr(bus.state, "EtCO2", max(self._PaCO2 - 5.0, 5.0)))
        self._SaO2 = float(bus.get("SaO2"))
        self._pH = float(bus.get("pH_a"))
        self._HCO3 = float(self.params["HCO3_baseline"])
        self._HCO3 = (
            self.params["alpha_CO2"]
            * self._PaCO2
            * 10 ** (self._pH - self.params["pK_H"])
        )
        bus.update({"gas_exchange_revision": "v1.20_adaptive_three_zone_vq_etco2_v316_v3.2_public_polish_v320", "vq_adaptive_revision": 320})

    def _alveolar_PO2(self, FiO2: float, local_PCO2: float, RQ: float) -> float:
        """Alveolar gas equation: PAO2 = FiO2*(Patm-PH2O) - PACO2/RQ."""
        return float(FiO2 * (PATM_CMHG - PH2O_37) - local_PCO2 / max(RQ, 0.50))

    def _henderson_hasselbalch(self, PaCO2: float, HCO3: float) -> float:
        denom = self.params["alpha_CO2"] * max(PaCO2, 1.0)
        return float(self.params["pK_H"] + np.log10(max(HCO3, 1e-6) / denom))

    def _update_HCO3(self, dt: float) -> float:
        # Slow renal compensation; essentially static over short simulations.
        tau_renal = 720.0 * 60.0
        HCO3_target = (
            self.params["alpha_CO2"]
            * self._PaCO2
            * 10 ** (7.40 - self.params["pK_H"])
        )
        delta = (HCO3_target - self._HCO3) * dt / tau_renal
        return float(max(self._HCO3 + delta, 5.0))

    def _adaptive_vq_drivers(
        self,
        bus: PhysiologicalBus,
        derecruitment: float,
        airway_shunt_add: float,
        airway_vd_add: float,
        obstruction: float,
        air_trap: float,
    ) -> dict[str, float | str]:
        """Return transparent pathology weights for adaptive V/Q dispersion.

        The weights are unitless educational drivers, not diagnoses. They keep the
        three-zone model responsive to pathology family: parenchymal/derecruitment
        states increase low-V/Q and shunt burden, obstructive states mainly increase
        dead space/high-V/Q burden, and sepsis/shock adds perfusion heterogeneity.
        """
        sepsis = float(bus.get("sepsis_severity_score")) if hasattr(bus.state, "sepsis_severity_score") else 0.0
        infection = float(bus.get("infection_severity_score")) if hasattr(bus.state, "infection_severity_score") else 0.0
        lactate = float(bus.get("lactate")) if hasattr(bus.state, "lactate") else 1.0
        weight_kg = float(bus.get("weight_kg")) if hasattr(bus.state, "weight_kg") else 20.0
        age_y = float(bus.get("age_y")) if hasattr(bus.state, "age_y") else 6.0

        lactate_weight = float(np.clip((lactate - 2.0) / 6.0, 0.0, 1.0))
        ards_weight = float(np.clip(1.15 * derecruitment + 0.60 * airway_shunt_add, 0.0, 1.0))
        obstruction_weight = float(np.clip(0.70 * obstruction + 0.65 * air_trap + 0.75 * airway_vd_add, 0.0, 1.0))
        shock_weight = float(np.clip(0.45 * sepsis + 0.35 * infection + 0.45 * lactate_weight, 0.0, 1.0))
        neonatal_base = 1.0 if (weight_kg <= 4.5 or age_y < 0.2) else 0.0
        neonatal_weight = float(np.clip(neonatal_base * (0.35 + 0.90 * derecruitment + 0.25 * airway_shunt_add), 0.0, 1.0))

        weights = {
            "ards": ards_weight,
            "obstruction": obstruction_weight,
            "shock": shock_weight,
            "neonatal": neonatal_weight,
        }
        dominant = max(weights, key=weights.get)
        if max(weights.values()) < 0.08:
            driver = "none"
        elif sum(1 for v in weights.values() if v >= 0.35) >= 2:
            driver = "mixed"
        else:
            driver = dominant

        return {
            "ards_weight": ards_weight,
            "obstruction_weight": obstruction_weight,
            "shock_weight": shock_weight,
            "neonatal_weight": neonatal_weight,
            "driver": driver,
        }

    def _effective_vq_fractions(self, bus: PhysiologicalBus, rec_frac: float, base_vdvt: float) -> tuple[float, float, float, float, dict[str, float | str]]:
        """Return effective shunt, dead-space, exchange fraction, V/Q log-SD and drivers."""
        ino_qs_mod = float(bus.get("ino_Qs_Qt_mod")) if hasattr(bus.state, "ino_Qs_Qt_mod") else 1.0
        airway_shunt_add = float(bus.get("airway_shunt_add")) if hasattr(bus.state, "airway_shunt_add") else 0.0
        airway_vd_add = float(bus.get("airway_VdVt_add")) if hasattr(bus.state, "airway_VdVt_add") else 0.0
        air_trap = float(bus.get("air_trapping_index")) if hasattr(bus.state, "air_trapping_index") else 0.0
        obstruction = float(bus.get("airway_obstruction_index")) if hasattr(bus.state, "airway_obstruction_index") else 0.0

        derecruitment = float(np.clip(1.0 - rec_frac, 0.0, 1.0))
        drivers = self._adaptive_vq_drivers(
            bus=bus,
            derecruitment=derecruitment,
            airway_shunt_add=airway_shunt_add,
            airway_vd_add=airway_vd_add,
            obstruction=obstruction,
            air_trap=air_trap,
        )
        adaptive = bool(self.params.get("vq_adaptive_enabled", True))
        ards_w = float(drivers["ards_weight"]) if adaptive else 0.0
        obstruction_w = float(drivers["obstruction_weight"]) if adaptive else 0.0
        shock_w = float(drivers["shock_weight"]) if adaptive else 0.0
        neonatal_w = float(drivers["neonatal_weight"]) if adaptive else 0.0

        shunt = (
            float(self.params["Qs_Qt"])
            + 0.18 * derecruitment
            + airway_shunt_add
            + float(self.params["vq_ards_shunt_gain"]) * ards_w
            + float(self.params["vq_shock_shunt_gain"]) * shock_w
            + float(self.params["vq_neonatal_shunt_gain"]) * neonatal_w
        ) * ino_qs_mod
        shunt = float(np.clip(shunt, 0.01, 0.82))

        deadspace = (
            base_vdvt
            + 0.07 * derecruitment
            + 0.10 * air_trap
            + airway_vd_add
            + float(self.params["vq_obstruction_deadspace_gain"]) * obstruction_w
            + float(self.params["vq_shock_deadspace_gain"]) * shock_w
        )
        deadspace = float(np.clip(deadspace, 0.05, 0.88))

        exchange = float(np.clip(1.0 - shunt, 0.02, 0.99))
        sigma = (
            float(self.params["vq_sigma_base"])
            + float(self.params["vq_sigma_recruitment_gain"]) * derecruitment
            + 0.40 * obstruction
            + 0.25 * air_trap
            + float(self.params["vq_ards_sigma_gain"]) * ards_w
            + float(self.params["vq_obstruction_sigma_gain"]) * obstruction_w
            + float(self.params["vq_shock_sigma_gain"]) * shock_w
            + float(self.params["vq_neonatal_sigma_gain"]) * neonatal_w
        )
        sigma = float(np.clip(sigma, 0.20, 1.80))
        return shunt, deadspace, exchange, sigma, drivers

    def _obstructive_ventilation_factor(self, bus: PhysiologicalBus) -> float:
        air_trap = float(bus.get("air_trapping_index")) if hasattr(bus.state, "air_trapping_index") else 0.0
        obstruction = float(bus.get("airway_obstruction_index")) if hasattr(bus.state, "airway_obstruction_index") else 0.0
        return float(np.clip(1.0 - 1.10 * air_trap - 0.55 * obstruction, 0.30, 1.0))

    def _vq_exchange_content(
        self,
        PAO2_mean: float,
        PaCO2_target: float,
        FiO2: float,
        RQ: float,
        Hb: float,
        pH: float,
        T: float,
        sigma: float,
    ) -> tuple[float, float, float]:
        """Mean end-capillary O2 content across log-normal V/Q bins."""
        n_bins = int(np.clip(int(self.params.get("vq_bins", 9)), 5, 17))
        z = np.linspace(-2.0, 2.0, n_bins)
        ratios = np.exp(z * sigma)
        weights = np.exp(-0.5 * z**2)
        weights = weights / weights.sum()

        contents = []
        low_burden = 0.0
        high_burden = 0.0
        for ratio, w in zip(ratios, weights):
            # Low V/Q units have higher local CO2 and lower PAO2; high V/Q units the opposite.
            local_PCO2 = float(np.clip(PaCO2_target / max(ratio, 0.08), 12.0, 110.0))
            local_PAO2 = self._alveolar_PO2(FiO2, local_PCO2, RQ)
            local_PAO2 = float(np.clip(local_PAO2, 15.0, 650.0))
            contents.append(w * _o2_content_from_po2(local_PAO2, Hb=Hb, pH=pH, T=T))
            if ratio < 0.5:
                low_burden += float(w)
            elif ratio > 2.0:
                high_burden += float(w)

        mean_content = float(np.sum(contents))
        # Keep mean PAO2 available for sanity cap; do not allow heterogeneity to exceed mean gas equation.
        mean_content = min(mean_content, _o2_content_from_po2(PAO2_mean, Hb=Hb, pH=pH, T=T))
        return mean_content, float(low_burden), float(high_burden)

    def _expected_co_l_min(self, bus: PhysiologicalBus, weight_kg: float) -> float:
        """Return a stable pediatric reference CO for EtCO2 perfusion coupling."""
        # Approximate educational baseline: pediatric cardiac index ~3.5-4.0 L/min/m2.
        bsa = float(getattr(bus.state, "BSA_m2", 0.0))
        if bsa > 0.15:
            return float(np.clip(3.8 * bsa, 0.6, 8.5))
        return float(np.clip(0.18 * max(weight_kg, 1.0), 0.6, 8.5))

    def _end_tidal_co2_target(
        self,
        bus: PhysiologicalBus,
        PaCO2: float,
        deadspace: float,
        shunt: float,
        sigma: float,
        VA_dot: float,
        VCO2: float,
        CO: float,
        weight_kg: float,
    ) -> tuple[float, float, float]:
        """Return model-coupled EtCO2, Pa-Et gradient and perfusion factor.

        The old bedside profile used a fixed PaCO2-5 proxy.  This contract keeps
        EtCO2 educational rather than clinical: it follows PaCO2 through effective
        alveolar ventilation, but widens the Pa-Et gradient with dead space/VQ
        dispersion/shunt and attenuates the capnogram when pulmonary blood-flow
        delivery is low.  This makes EtCO2 respond qualitatively to RSI, weaning,
        obstructive dead space and low-output/RCP-like states without adding a new
        complex compartment model.
        """
        expected_co = self._expected_co_l_min(bus, weight_kg)
        co_ratio = float(np.clip(CO / max(expected_co, 0.05), 0.05, 2.0))
        perfusion_factor = float(np.clip(0.35 + 0.65 * co_ratio, 0.18, 1.12))

        # Effective ventilation is already reflected in PaCO2.  Keep an explicit
        # alveolar ventilation term so sudden very low VA states widen the gradient
        # faster than PaCO2 equilibration alone.
        va_ref = float(np.clip(0.863 * max(VCO2, 1.0) / 40.0, 0.20, 10.0))
        ventilation_ratio = float(np.clip(VA_dot / max(va_ref, 1e-3), 0.15, 3.0))
        low_vent_gradient = 3.0 * max(1.0 - ventilation_ratio, 0.0)

        gradient = (
            1.8
            + 9.0 * np.clip(deadspace, 0.0, 0.90)
            + 3.5 * np.clip(shunt, 0.0, 0.85)
            + 2.5 * np.clip(sigma, 0.0, 2.0)
            + 12.0 * max(1.0 - perfusion_factor, 0.0)
            + low_vent_gradient
        )
        gradient = float(np.clip(gradient, 2.0, 45.0))
        etco2 = float(np.clip(PaCO2 - gradient, 3.0, 95.0))
        if PaCO2 >= 8.0:
            etco2 = min(etco2, PaCO2 - 1.0)
        return float(etco2), float(max(PaCO2 - etco2, 0.0)), perfusion_factor

    def _venous_o2(self, Hb: float, CO: float, VO2: float, T: float) -> tuple[float, float, float]:
        """Estimate venous O2 content, saturation and PO2 from Fick balance."""
        CaO2_curr = Hb * O2_CAPACITY * self._SaO2 + HENRY_O2 * self._PaO2
        VO2_dL = VO2 / (max(CO, 0.05) * 10.0)
        CvO2 = float(max(CaO2_curr - VO2_dL, 0.0))
        PvO2 = _po2_from_o2_content(CvO2, Hb=Hb, pH=self._pH, T=T)
        SvO2 = _sat_from_po2(PvO2, pH=self._pH, T=T)
        return CvO2, float(SvO2), float(PvO2)

    def _central_venous_o2(self, SaO2: float, Hb: float, CO: float, VO2: float) -> float:
        """Estimate ScvO2 from arterial saturation and systemic O2 extraction."""
        o2_capacity_flow = max(CO * Hb * O2_CAPACITY * 10.0, 1e-6)
        extraction = VO2 / o2_capacity_flow
        return float(np.clip(SaO2 - extraction, 0.05, 0.98))

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        FiO2 = float(bus.get("FiO2_delivered")) if hasattr(bus.state, "FiO2_delivered") else float(bus.get("FiO2"))
        RR = float(bus.get("RR_total")) if hasattr(bus.state, "RR_total") and float(bus.get("RR_total")) > 0 else float(bus.get("RR"))
        Vt = float(bus.get("Vt"))
        rec_frac = float(bus.get("recruited_frac"))
        Hb = float(bus.get("Hb"))
        CO = float(bus.get("CO"))
        VO2 = float(bus.get("VO2"))
        T_core = float(bus.get("T_core"))
        weight_kg = float(bus.get("weight_kg")) if hasattr(bus.state, "weight_kg") else 20.0
        RQ = float(getattr(bus.state, "respiratory_quotient", self.params["RQ"]))
        VCO2_mod = float(getattr(bus.state, "VCO2_mod", 1.0))
        tau = float(self.params["tau_gas_s"])

        info = bus_patient_scalars(bus, self.params)
        prof = info["profile"]
        base_vdvt = float(prof.get("Vd_Vt", self.params["Vd_Vt"]))

        shunt, deadspace, exchange, sigma, vq_drivers = self._effective_vq_fractions(bus, rec_frac, base_vdvt)
        hfnc_washout = float(bus.get("HFNC_deadspace_washout")) if hasattr(bus.state, "HFNC_deadspace_washout") else 0.0
        niv_washout = float(bus.get("NIV_deadspace_washout")) if hasattr(bus.state, "NIV_deadspace_washout") else 0.0
        tube_vd_add = float(bus.get("tube_VdVt_add")) if hasattr(bus.state, "tube_VdVt_add") else 0.0
        deadspace = float(np.clip(
            (deadspace + np.clip(tube_vd_add, 0.0, 0.25))
            * (1.0 - 0.45 * np.clip(hfnc_washout, 0.0, 0.6))
            * (1.0 - 0.35 * np.clip(niv_washout, 0.0, 0.5)),
            0.03,
            0.88,
        ))
        obstructive_factor = self._obstructive_ventilation_factor(bus)
        VA_dot = RR * Vt * (1.0 - deadspace) * obstructive_factor / 1000.0
        VA_dot = float(max(VA_dot, 0.02))

        VCO2 = VO2 * RQ * VCO2_mod
        PaCO2_target_raw = 0.863 * VCO2 / (VA_dot + 1e-3)
        PaCO2_target_raw *= (1.0 + 0.30 * shunt + 0.08 * sigma)

        # v3.2 public-polish: avoid a visually obvious hard PaCO2 wall.
        # Severe obstruction/shock should still generate marked hypercapnia,
        # but public demo scenarios should not all converge to the same
        # repeated 105 mmHg value.  Use a soft upper transition that preserves
        # the low/mid-range response and asymptotically compresses extremes.
        soft_start = 78.0
        soft_span = 21.5
        if PaCO2_target_raw > soft_start:
            PaCO2_target = soft_start + soft_span * (1.0 - np.exp(-(PaCO2_target_raw - soft_start) / max(soft_span, 1.0)))
        else:
            PaCO2_target = PaCO2_target_raw
        PaCO2_target = float(np.clip(PaCO2_target, 15.0, 103.0))

        PAO2_mean = self._alveolar_PO2(FiO2, PaCO2_target, RQ)
        PAO2_mean = float(np.clip(PAO2_mean, 15.0, 650.0))

        CvO2, SvO2_prev, PvO2_prev = self._venous_o2(Hb=Hb, CO=CO, VO2=VO2, T=T_core)
        CcO2_mean, low_vq_burden, high_vq_burden = self._vq_exchange_content(
            PAO2_mean=PAO2_mean,
            PaCO2_target=PaCO2_target,
            FiO2=FiO2,
            RQ=RQ,
            Hb=Hb,
            pH=self._pH,
            T=T_core,
            sigma=sigma,
        )

        CaO2_target = shunt * CvO2 + exchange * CcO2_mean
        PaO2_target = _po2_from_o2_content(CaO2_target, Hb=Hb, pH=self._pH, T=T_core)
        PaO2_target = float(np.clip(min(PaO2_target, PAO2_mean), 18.0, 520.0))

        alpha_dt = 1.0 - np.exp(-dt / max(tau, dt))
        self._PaCO2 += alpha_dt * (PaCO2_target - self._PaCO2)
        self._PaO2 += alpha_dt * (PaO2_target - self._PaO2)
        self._PaCO2 = float(np.clip(self._PaCO2, 10.0, 120.0))
        self._PaO2 = float(np.clip(self._PaO2, 10.0, 560.0))

        self._SaO2 = _sat_from_po2(self._PaO2, pH=self._pH, T=T_core)
        self._HCO3 = self._update_HCO3(dt)
        self._pH = self._henderson_hasselbalch(self._PaCO2, self._HCO3)

        EtCO2_target, etco2_gradient, etco2_perfusion_factor = self._end_tidal_co2_target(
            bus=bus,
            PaCO2=self._PaCO2,
            deadspace=deadspace,
            shunt=shunt,
            sigma=sigma,
            VA_dot=VA_dot,
            VCO2=VCO2,
            CO=CO,
            weight_kg=weight_kg,
        )
        # Capnography responds faster than arterial gas equilibration but remains
        # smoothed for monitor readability.
        et_alpha_dt = 1.0 - np.exp(-dt / max(4.0, dt))
        self._EtCO2 += et_alpha_dt * (EtCO2_target - self._EtCO2)
        self._EtCO2 = float(np.clip(self._EtCO2, 2.0, 100.0))
        etco2_gradient = float(max(self._PaCO2 - self._EtCO2, 0.0))

        CaO2_new = Hb * O2_CAPACITY * self._SaO2 + HENRY_O2 * self._PaO2
        DO2 = CaO2_new * CO * 10.0
        ERO2 = float(np.clip(VO2 / (DO2 + 1e-3), 0.0, 0.95))
        SvO2 = float(np.clip(1.0 - ERO2, 0.0, 0.98))
        ScvO2 = self._central_venous_o2(SaO2=self._SaO2, Hb=Hb, CO=CO, VO2=VO2)
        PvO2 = float(_po2_from_sat(SvO2, pH=self._pH, T=T_core))

        bus.update({
            "PaO2": float(self._PaO2),
            "PaCO2": float(self._PaCO2),
            "EtCO2": float(self._EtCO2),
            "EtCO2_proxy": float(self._EtCO2),
            "etco2_pa_gradient": float(etco2_gradient),
            "etco2_perfusion_factor": float(etco2_perfusion_factor),
            "etco2_deadspace_factor": float(deadspace),
            "etco2_source": "gas_exchange_v316_model_coupled",
            "SaO2": float(self._SaO2),
            "PvO2": float(PvO2),
            "SvO2": float(SvO2),
            "ScvO2": float(ScvO2),
            "ScvO2_source": "gas_exchange_SaO2_VO2_CO_Hb_proxy",
            "ScvO2_revision": 420,
            "DO2": float(DO2),
            "ERO2": float(ERO2),
            "vq_shunt_frac": float(shunt),
            "vq_deadspace_frac": float(deadspace),
            "vq_exchange_frac": float(exchange),
            "vq_logsd": float(sigma),
            "vq_adaptive_sigma": float(sigma),
            "vq_ards_weight": float(vq_drivers.get("ards_weight", 0.0)),
            "vq_obstruction_weight": float(vq_drivers.get("obstruction_weight", 0.0)),
            "vq_shock_weight": float(vq_drivers.get("shock_weight", 0.0)),
            "vq_neonatal_weight": float(vq_drivers.get("neonatal_weight", 0.0)),
            "vq_pathology_driver": str(vq_drivers.get("driver", "none")),
            "vq_low_vq_burden": float(low_vq_burden),
            "vq_high_vq_burden": float(high_vq_burden),
            "alveolar_ventilation_L_min": float(VA_dot),
            "gas_exchange_revision": "v1.20_adaptive_three_zone_vq_etco2_v316_v3.2_public_polish_v320",
            "vq_adaptive_revision": 320,
            "FiO2_delivered": float(FiO2),
        })
