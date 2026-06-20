"""
Airway Interface Module — v1.23.3
==================================

Public educational airway-interface scaffold.

v1.23 separated intubated/connected patients from spontaneous unassisted
breathing. v1.23.1 added conservative oxygen delivery for extubated children;
v1.23.2 added non-invasive ventilation interfaces; v1.23.3 adds
artificial-airway proxies for ETT/tracheostomy resistance, dead space, cuff leak
and tube obstruction:

- UNASSISTED / ROOM_AIR: no active pressure; FiO2 is ambient unless overridden.
- LOW_FLOW_OXYGEN / SIMPLE_MASK: non-pressurised oxygen with limited delivery
  efficiency.
- HFNC: non-invasive high-flow oxygen with effective FiO2, a small CPAP-like
  distending-pressure proxy, and dead-space washout.
- NIV_CPAP / NIV_BIPAP: mask-based pressure delivery with leak, delivered
  pressure, oxygen efficiency and failure-risk proxies.
- ETT / TRACHEOSTOMY: connected artificial airway with tube resistance,
  apparatus dead-space, cuff leak and obstruction proxies.

This is an educational interface model. It is not a clinical oxygen-delivery
calculator and does not model cannula size, exact entrainment physics, or patient-
specific leak, airway-device sizing or pressure-drop physics.
"""

from __future__ import annotations
from typing import List

import numpy as np

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


class AirwayInterfaceModule(BaseModule):
    """Airway-interface normalizer, oxygen-delivery proxy and audit writer."""

    DEFAULT_PARAMS = {
        "default_interface": "ETT",
        "ambient_airway_pressure_cmH2O": 0.0,
        "room_air_FiO2": 0.21,
        "low_flow_efficiency_base": 0.38,
        "simple_mask_efficiency_base": 0.62,
        "hfnc_efficiency_base": 0.92,
        "hfnc_pressure_per_L_kg_min": 1.8,   # qualitative cmH2O at 1 L/kg/min before leak scaling
        "hfnc_pressure_cap_cmH2O": 6.0,
        "hfnc_deadspace_washout_gain": 0.35,
        "niv_pressure_efficiency_base": 0.86,
        "niv_fio2_efficiency_base": 0.88,
        "niv_leak_default": 0.28,
        "niv_deadspace_washout_gain": 0.18,
        "niv_pressure_cap_cmH2O": 24.0,
        "ett_resistance_ref_ID_mm": 5.0,
        "ett_resistance_ref_cmH2O_L_s": 6.0,
        "ett_default_length_cm": 16.0,
        "ett_deadspace_connector_mL": 2.0,
        "tube_obstruction_resistance_gain": 3.0,
        "cuff_leak_pressure_loss_gain": 0.45,
        "cuff_leak_fio2_loss_gain": 0.12,
        "trach_resistance_multiplier": 0.70,
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="AirwayInterface", params=merged)

    @property
    def input_keys(self) -> List[str]:
        return [
            "airway_interface", "oxygen_interface", "vent_mode", "intubated",
            "ventilator_connected", "airway_pressure_delivery_enabled", "PEEP",
            "Paw", "Paw_current", "FiO2", "FiO2_delivered", "oxygen_flow_L_min",
            "oxygen_FiO2_set", "HFNC_flow_L_min", "HFNC_FiO2_set",
            "NIV_mode", "NIV_CPAP_cmH2O", "NIV_IPAP_cmH2O", "NIV_EPAP_cmH2O",
            "NIV_pressure_support_cmH2O", "NIV_FiO2_set", "NIV_leak_fraction",
            "mask_leak_fraction", "mouth_leak_fraction", "weight_kg", "RR_total",
            "Pmus", "SaO2", "PaCO2", "airway_obstruction_index", "air_trapping_index",
            "tube_internal_diameter_mm", "tube_length_cm", "tube_obstruction_score",
            "cuff_leak_fraction", "cuff_pressure_cmH2O", "ETT_position_score",
            "Vt", "airway_resistance_mod",
            "manual_ventilation_active", "bag_mask_ventilation_active", "bag_mask_quality",
            "airway_protection_score", "aspiration_risk", "laryngospasm_score",
            "upper_airway_obstruction_score", "airway_event_revision",
        ]

    @property
    def output_keys(self) -> List[str]:
        return [
            "airway_interface", "intubated", "ventilator_connected",
            "airway_pressure_delivery_enabled", "unassisted_breathing_active",
            "spontaneous_airway_mode", "ambient_airway_pressure_cmH2O",
            "effective_external_PEEP_cmH2O", "airway_pressure_source",
            "airway_interface_revision", "airway_interface_note",
            "oxygen_interface", "oxygen_flow_L_min", "oxygen_FiO2_set",
            "FiO2", "FiO2_delivered", "FiO2_delivery_efficiency",
            "HFNC_flow_L_min", "HFNC_FiO2_set", "HFNC_distending_pressure_cmH2O",
            "HFNC_deadspace_washout", "HFNC_failure_risk", "mouth_leak_fraction",
            "NIV_mode", "NIV_CPAP_cmH2O", "NIV_IPAP_cmH2O", "NIV_EPAP_cmH2O",
            "NIV_pressure_support_cmH2O", "NIV_FiO2_set", "NIV_leak_fraction",
            "NIV_delivered_PEEP_cmH2O", "NIV_delivered_PS_cmH2O",
            "NIV_delivered_PIP_cmH2O", "NIV_deadspace_washout", "NIV_failure_risk",
            "oxygen_delivery_revision",
            "tube_internal_diameter_mm", "tube_length_cm", "tube_resistance_cmH2O_L_s",
            "tube_resistance_factor", "tube_dead_space_mL", "tube_VdVt_add",
            "tube_obstruction_score", "cuff_leak_fraction", "cuff_pressure_cmH2O",
            "ETT_position_score", "ETT_pressure_delivery_efficiency",
            "ETT_FiO2_delivery_efficiency", "ETT_failure_risk", "artificial_airway_revision",
            "airway_resistance_mod",
            "manual_ventilation_active", "bag_mask_ventilation_active", "bag_mask_quality",
            "airway_protection_score", "aspiration_risk", "laryngospasm_score",
            "upper_airway_obstruction_score", "airway_event_revision",
        ]

    def initialize(self, bus: PhysiologicalBus) -> None:
        self.step(bus, dt=0.0)

    def _normalize_interface(self, value: str) -> str:
        v = str(value or self.params["default_interface"]).upper()
        aliases = {
            "NO_VENTILATOR": "UNASSISTED",
            "SPONTANEOUS": "UNASSISTED",
            "EXTUBATED": "UNASSISTED",
            "NONE": "UNASSISTED",
            "ROOM_AIR": "UNASSISTED",
            "LOW_FLOW": "LOW_FLOW_OXYGEN",
            "NASAL_CANNULA": "LOW_FLOW_OXYGEN",
            "NC": "LOW_FLOW_OXYGEN",
            "OXYGEN_MASK": "SIMPLE_MASK",
            "MASK": "SIMPLE_MASK",
            "HIGH_FLOW": "HFNC",
            "HIGH_FLOW_NASAL_CANNULA": "HFNC",
            "NIV": "NIV_BIPAP",
            "BIPAP": "NIV_BIPAP",
            "NIV_BILEVEL": "NIV_BIPAP",
            "NONINVASIVE_BIPAP": "NIV_BIPAP",
            "BAG_MASK": "NIV_BIPAP",
            "BVM": "NIV_BIPAP",
            "MANUAL_VENTILATION": "NIV_BIPAP",
            "NONINVASIVE_CPAP": "NIV_CPAP",
            "MASK_CPAP": "NIV_CPAP",
            "INTUBATED": "ETT",
            "ENDOTRACHEAL_TUBE": "ETT",
            "ENDOTRACHEAL": "ETT",
            "TUBE": "ETT",
            "TRACH": "TRACHEOSTOMY",
            "TRACHEAL_CANNULA": "TRACHEOSTOMY",
        }
        return aliases.get(v, v)

    def _oxygen_interface_for(self, interface: str, bus: PhysiologicalBus) -> str:
        raw = str(bus.get("oxygen_interface")) if hasattr(bus.state, "oxygen_interface") else ""
        raw = raw.upper()
        if raw and raw not in ("VENTILATOR", "ROOM_AIR"):
            return self._normalize_interface(raw)
        if interface in ("LOW_FLOW_OXYGEN", "SIMPLE_MASK", "HFNC"):
            return interface
        if interface in ("NIV_CPAP", "NIV_BIPAP"):
            return "NIV"
        if interface in ("UNASSISTED", "NONE"):
            return "ROOM_AIR" if float(bus.get("FiO2")) <= 0.22 else "LOW_FLOW_OXYGEN"
        return "VENTILATOR"

    def _compute_oxygen_delivery(self, interface: str, oxygen_interface: str, bus: PhysiologicalBus) -> dict[str, float | str]:
        weight = max(float(bus.get("weight_kg")) if hasattr(bus.state, "weight_kg") else 20.0, 0.5)
        leak = float(bus.get("mouth_leak_fraction")) if hasattr(bus.state, "mouth_leak_fraction") else 0.25
        leak = float(np.clip(leak, 0.0, 0.90))
        current_fio2 = float(bus.get("FiO2")) if hasattr(bus.state, "FiO2") else 0.21
        oxygen_set = float(bus.get("oxygen_FiO2_set")) if hasattr(bus.state, "oxygen_FiO2_set") else current_fio2
        oxygen_flow = float(bus.get("oxygen_flow_L_min")) if hasattr(bus.state, "oxygen_flow_L_min") else 0.0
        hfnc_flow = float(bus.get("HFNC_flow_L_min")) if hasattr(bus.state, "HFNC_flow_L_min") else 0.0
        hfnc_set = float(bus.get("HFNC_FiO2_set")) if hasattr(bus.state, "HFNC_FiO2_set") else oxygen_set
        room = float(self.params["room_air_FiO2"])

        oxygen_interface = self._normalize_interface(oxygen_interface)
        if oxygen_interface == "HFNC" or interface == "HFNC":
            oxygen_interface = "HFNC"
            hfnc_flow = max(hfnc_flow, oxygen_flow, 1.0 * weight)
            flow_per_kg = hfnc_flow / weight
            pressure = float(np.clip(
                self.params["hfnc_pressure_per_L_kg_min"] * flow_per_kg * (1.0 - 0.65 * leak),
                0.0,
                self.params["hfnc_pressure_cap_cmH2O"],
            ))
            washout = float(np.clip(self.params["hfnc_deadspace_washout_gain"] * flow_per_kg * (1.0 - 0.40 * leak), 0.0, 0.45))
            efficiency = float(np.clip(self.params["hfnc_efficiency_base"] - 0.35 * leak + 0.05 * min(flow_per_kg, 2.0), 0.35, 0.99))
            target_fio2 = float(np.clip(hfnc_set if hfnc_set > 0.21 else current_fio2, 0.21, 1.0))
            delivered = float(np.clip(room + (target_fio2 - room) * efficiency, 0.21, 1.0))
            rr = float(bus.get("RR_total")) if hasattr(bus.state, "RR_total") else float(bus.get("RR"))
            pco2 = float(bus.get("PaCO2")) if hasattr(bus.state, "PaCO2") else 40.0
            spo2 = float(bus.get("SaO2")) if hasattr(bus.state, "SaO2") else 0.97
            obstruction = float(bus.get("airway_obstruction_index")) if hasattr(bus.state, "airway_obstruction_index") else 0.0
            failure = float(np.clip(0.35 * max(rr - 45.0, 0.0) / 40.0 + 0.35 * max(pco2 - 55.0, 0.0) / 45.0 + 0.35 * max(0.92 - spo2, 0.0) / 0.18 + 0.25 * obstruction - 0.25 * washout, 0.0, 1.0))
            return {
                "oxygen_interface": "HFNC",
                "oxygen_flow_L_min": hfnc_flow,
                "oxygen_FiO2_set": target_fio2,
                "FiO2_delivered": delivered,
                "FiO2_delivery_efficiency": efficiency,
                "HFNC_flow_L_min": hfnc_flow,
                "HFNC_FiO2_set": target_fio2,
                "HFNC_distending_pressure_cmH2O": pressure,
                "HFNC_deadspace_washout": washout,
                "HFNC_failure_risk": failure,
                "mouth_leak_fraction": leak,
            }

        if oxygen_interface in ("LOW_FLOW_OXYGEN", "SIMPLE_MASK"):
            oxygen_flow = max(oxygen_flow, 1.0)
            target_fio2 = float(np.clip(oxygen_set if oxygen_set > 0.21 else current_fio2, 0.21, 1.0))
            if oxygen_interface == "LOW_FLOW_OXYGEN":
                flow_factor = float(np.clip(oxygen_flow / max(0.35 * weight, 1.0), 0.0, 1.0))
                efficiency = float(np.clip(self.params["low_flow_efficiency_base"] * flow_factor * (1.0 - 0.35 * leak), 0.12, 0.70))
            else:
                flow_factor = float(np.clip(oxygen_flow / max(0.55 * weight, 2.0), 0.0, 1.0))
                efficiency = float(np.clip(self.params["simple_mask_efficiency_base"] * flow_factor * (1.0 - 0.25 * leak), 0.20, 0.85))
            delivered = float(np.clip(room + (target_fio2 - room) * efficiency, 0.21, 0.85))
            return {
                "oxygen_interface": oxygen_interface,
                "oxygen_flow_L_min": oxygen_flow,
                "oxygen_FiO2_set": target_fio2,
                "FiO2_delivered": delivered,
                "FiO2_delivery_efficiency": efficiency,
                "HFNC_flow_L_min": 0.0,
                "HFNC_FiO2_set": target_fio2,
                "HFNC_distending_pressure_cmH2O": 0.0,
                "HFNC_deadspace_washout": 0.0,
                "HFNC_failure_risk": 0.0,
                "mouth_leak_fraction": leak,
            }

        if oxygen_interface == "ROOM_AIR":
            return {
                "oxygen_interface": "ROOM_AIR",
                "oxygen_flow_L_min": 0.0,
                "oxygen_FiO2_set": room,
                "FiO2_delivered": room,
                "FiO2_delivery_efficiency": 1.0,
                "HFNC_flow_L_min": 0.0,
                "HFNC_FiO2_set": room,
                "HFNC_distending_pressure_cmH2O": 0.0,
                "HFNC_deadspace_washout": 0.0,
                "HFNC_failure_risk": 0.0,
                "mouth_leak_fraction": leak,
            }

        # Ventilator/ETT path: delivered FiO2 equals ventilator FiO2 in this layer.
        return {
            "oxygen_interface": "VENTILATOR",
            "oxygen_flow_L_min": oxygen_flow,
            "oxygen_FiO2_set": float(np.clip(current_fio2, 0.21, 1.0)),
            "FiO2_delivered": float(np.clip(current_fio2, 0.21, 1.0)),
            "FiO2_delivery_efficiency": 1.0,
            "HFNC_flow_L_min": 0.0,
            "HFNC_FiO2_set": float(np.clip(current_fio2, 0.21, 1.0)),
            "HFNC_distending_pressure_cmH2O": 0.0,
            "HFNC_deadspace_washout": 0.0,
            "HFNC_failure_risk": 0.0,
            "mouth_leak_fraction": leak,
        }


    def _compute_niv_delivery(self, interface: str, bus: PhysiologicalBus) -> dict[str, float | str]:
        """Return leak-adjusted NIV pressure/oxygen proxies for CPAP or bilevel NIV."""
        weight = max(float(bus.get("weight_kg")) if hasattr(bus.state, "weight_kg") else 20.0, 0.5)
        leak = float(bus.get("NIV_leak_fraction")) if hasattr(bus.state, "NIV_leak_fraction") else (
            float(bus.get("mask_leak_fraction")) if hasattr(bus.state, "mask_leak_fraction") else float(self.params["niv_leak_default"])
        )
        leak = float(np.clip(leak, 0.0, 0.90))
        current_fio2 = float(bus.get("FiO2")) if hasattr(bus.state, "FiO2") else 0.21
        niv_fio2 = float(bus.get("NIV_FiO2_set")) if hasattr(bus.state, "NIV_FiO2_set") else current_fio2
        niv_fio2 = float(np.clip(niv_fio2 if niv_fio2 > 0.21 else current_fio2, 0.21, 1.0))
        peep_existing = float(bus.get("PEEP")) if hasattr(bus.state, "PEEP") else 5.0
        cpap = float(bus.get("NIV_CPAP_cmH2O")) if hasattr(bus.state, "NIV_CPAP_cmH2O") else peep_existing
        epap = float(bus.get("NIV_EPAP_cmH2O")) if hasattr(bus.state, "NIV_EPAP_cmH2O") else peep_existing
        ipap = float(bus.get("NIV_IPAP_cmH2O")) if hasattr(bus.state, "NIV_IPAP_cmH2O") else max(epap + float(bus.get("PS_cmH2O") if hasattr(bus.state, "PS_cmH2O") else 8.0), epap)
        ps = float(bus.get("NIV_pressure_support_cmH2O")) if hasattr(bus.state, "NIV_pressure_support_cmH2O") else max(ipap - epap, 0.0)
        pressure_eff = float(np.clip(self.params["niv_pressure_efficiency_base"] - 0.55 * leak, 0.30, 0.98))
        fio2_eff = float(np.clip(self.params["niv_fio2_efficiency_base"] - 0.28 * leak, 0.45, 0.98))
        delivered_fio2 = float(np.clip(float(self.params["room_air_FiO2"]) + (niv_fio2 - float(self.params["room_air_FiO2"])) * fio2_eff, 0.21, 1.0))
        if interface == "NIV_CPAP":
            niv_mode = "CPAP"
            delivered_peep = float(np.clip(cpap * pressure_eff, 0.0, self.params["niv_pressure_cap_cmH2O"]))
            delivered_ps = 0.0
        else:
            niv_mode = "BIPAP"
            delivered_peep = float(np.clip(epap * pressure_eff, 0.0, self.params["niv_pressure_cap_cmH2O"]))
            delivered_ps = float(np.clip(ps * pressure_eff, 0.0, max(self.params["niv_pressure_cap_cmH2O"] - delivered_peep, 0.0)))
        delivered_pip = float(np.clip(delivered_peep + delivered_ps, 0.0, self.params["niv_pressure_cap_cmH2O"]))
        flow_proxy_L_min = max(float(bus.get("oxygen_flow_L_min")) if hasattr(bus.state, "oxygen_flow_L_min") else 0.0, 0.8 * weight)
        washout = float(np.clip(self.params["niv_deadspace_washout_gain"] * (delivered_ps / 10.0 + delivered_peep / 8.0) * (1.0 - 0.55 * leak), 0.0, 0.35))
        rr = float(bus.get("RR_total")) if hasattr(bus.state, "RR_total") else float(bus.get("RR"))
        pco2 = float(bus.get("PaCO2")) if hasattr(bus.state, "PaCO2") else 40.0
        spo2 = float(bus.get("SaO2")) if hasattr(bus.state, "SaO2") else 0.97
        obstruction = float(bus.get("airway_obstruction_index")) if hasattr(bus.state, "airway_obstruction_index") else 0.0
        failure = float(np.clip(
            0.30 * max(rr - 45.0, 0.0) / 40.0
            + 0.32 * max(pco2 - 55.0, 0.0) / 45.0
            + 0.35 * max(0.92 - spo2, 0.0) / 0.18
            + 0.25 * leak
            + 0.20 * obstruction
            - 0.20 * washout,
            0.0,
            1.0,
        ))
        return {
            "oxygen_interface": "NIV",
            "oxygen_flow_L_min": flow_proxy_L_min,
            "oxygen_FiO2_set": niv_fio2,
            "FiO2_delivered": delivered_fio2,
            "FiO2_delivery_efficiency": fio2_eff,
            "HFNC_flow_L_min": 0.0,
            "HFNC_FiO2_set": niv_fio2,
            "HFNC_distending_pressure_cmH2O": 0.0,
            "HFNC_deadspace_washout": 0.0,
            "HFNC_failure_risk": 0.0,
            "mouth_leak_fraction": leak,
            "NIV_mode": niv_mode,
            "NIV_CPAP_cmH2O": cpap,
            "NIV_IPAP_cmH2O": ipap,
            "NIV_EPAP_cmH2O": epap,
            "NIV_pressure_support_cmH2O": ps,
            "NIV_FiO2_set": niv_fio2,
            "NIV_leak_fraction": leak,
            "NIV_delivered_PEEP_cmH2O": delivered_peep,
            "NIV_delivered_PS_cmH2O": delivered_ps,
            "NIV_delivered_PIP_cmH2O": delivered_pip,
            "NIV_deadspace_washout": washout,
            "NIV_failure_risk": failure,
        }


    def _default_tube_geometry(self, interface: str, bus: PhysiologicalBus) -> tuple[float, float]:
        """Return conservative default ID/length when a scenario does not provide them."""
        age = float(bus.get("age_y")) if hasattr(bus.state, "age_y") else 6.0
        weight = max(float(bus.get("weight_kg")) if hasattr(bus.state, "weight_kg") else 20.0, 0.5)
        if interface == "TRACHEOSTOMY":
            tube_id = float(np.clip(3.0 + 0.035 * weight, 3.0, 6.5))
            length = float(np.clip(5.0 + 0.25 * age, 4.0, 9.0))
        else:
            # Cuffed pediatric ETT educational approximation, capped for neonate/adolescent profiles.
            tube_id = float(np.clip(3.5 + max(age, 0.0) / 4.0, 3.0, 7.5))
            length = float(np.clip(10.5 + 0.55 * age + 0.10 * weight, 8.5, 24.0))
        return tube_id, length

    def _compute_artificial_airway(self, interface: str, bus: PhysiologicalBus) -> dict[str, float | int]:
        """Return ETT/tracheostomy resistance, dead-space, leak and obstruction proxies.

        This is an educational scaffold. It deliberately exports transparent bounded
        proxies rather than clinical pressure-drop calculations. Tube resistance is
        scaled with an ID^-4 relationship to make small pediatric tubes visibly more
        resistive while remaining numerically stable.
        """
        default_id, default_len = self._default_tube_geometry(interface, bus)
        tube_id = float(bus.get("tube_internal_diameter_mm")) if hasattr(bus.state, "tube_internal_diameter_mm") else default_id
        tube_len = float(bus.get("tube_length_cm")) if hasattr(bus.state, "tube_length_cm") else default_len
        # A default BusState has a child-sized ETT. If the active profile is not explicitly
        # configured and the default is implausible, pull it toward the age/weight estimate.
        if tube_id <= 0.0:
            tube_id = default_id
        if tube_len <= 0.0:
            tube_len = default_len
        tube_id = float(np.clip(tube_id, 2.5, 8.5))
        tube_len = float(np.clip(tube_len, 4.0 if interface == "TRACHEOSTOMY" else 8.0, 26.0))

        obstruction = float(bus.get("tube_obstruction_score")) if hasattr(bus.state, "tube_obstruction_score") else 0.0
        cuff_leak = float(bus.get("cuff_leak_fraction")) if hasattr(bus.state, "cuff_leak_fraction") else 0.0
        cuff_pressure = float(bus.get("cuff_pressure_cmH2O")) if hasattr(bus.state, "cuff_pressure_cmH2O") else 20.0
        position = float(bus.get("ETT_position_score")) if hasattr(bus.state, "ETT_position_score") else 1.0
        obstruction = float(np.clip(obstruction, 0.0, 1.0))
        cuff_leak = float(np.clip(cuff_leak, 0.0, 0.90))
        position = float(np.clip(position, 0.0, 1.0))

        ref_id = float(self.params["ett_resistance_ref_ID_mm"])
        ref_r = float(self.params["ett_resistance_ref_cmH2O_L_s"])
        ref_len = float(self.params["ett_default_length_cm"])
        resistance = ref_r * (ref_id / max(tube_id, 0.1)) ** 4 * (tube_len / ref_len)
        if interface == "TRACHEOSTOMY":
            resistance *= float(self.params["trach_resistance_multiplier"])
        resistance *= (1.0 + float(self.params["tube_obstruction_resistance_gain"]) * obstruction)
        resistance = float(np.clip(resistance, 0.5, 120.0))

        tube_r_factor = float(np.clip(1.0 + 0.035 * resistance + 1.20 * obstruction, 1.0, 7.0))
        existing_r_mod = float(bus.get("airway_resistance_mod")) if hasattr(bus.state, "airway_resistance_mod") else 1.0
        combined_r_mod = float(np.clip(max(existing_r_mod, 1.0) * tube_r_factor, 1.0, 12.0))

        radius_cm = tube_id / 20.0
        tube_volume_mL = float(np.pi * radius_cm * radius_cm * tube_len)
        connector = float(self.params["ett_deadspace_connector_mL"])
        if interface == "TRACHEOSTOMY":
            connector *= 0.65
        deadspace = float(np.clip(tube_volume_mL + connector, 1.0, 35.0))
        vt = max(float(bus.get("Vt")) if hasattr(bus.state, "Vt") else 120.0, 20.0)
        vdvt_add = float(np.clip(deadspace / vt + 0.07 * obstruction, 0.0, 0.25))

        pressure_eff = float(np.clip(
            1.0
            - float(self.params["cuff_leak_pressure_loss_gain"]) * cuff_leak
            - 0.22 * obstruction
            - 0.25 * (1.0 - position),
            0.35,
            1.0,
        ))
        fio2_eff = float(np.clip(1.0 - float(self.params["cuff_leak_fio2_loss_gain"]) * cuff_leak, 0.75, 1.0))
        failure = float(np.clip(0.45 * obstruction + 0.25 * cuff_leak + 0.30 * (1.0 - position), 0.0, 1.0))

        return {
            "tube_internal_diameter_mm": tube_id,
            "tube_length_cm": tube_len,
            "tube_resistance_cmH2O_L_s": resistance,
            "tube_resistance_factor": tube_r_factor,
            "tube_dead_space_mL": deadspace,
            "tube_VdVt_add": vdvt_add,
            "tube_obstruction_score": obstruction,
            "cuff_leak_fraction": cuff_leak,
            "cuff_pressure_cmH2O": cuff_pressure,
            "ETT_position_score": position,
            "ETT_pressure_delivery_efficiency": pressure_eff,
            "ETT_FiO2_delivery_efficiency": fio2_eff,
            "ETT_failure_risk": failure,
            "artificial_airway_revision": 1233,
            "airway_resistance_mod": combined_r_mod,
        }

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        mode = str(bus.get("vent_mode")).upper() if hasattr(bus.state, "vent_mode") else "PCV"
        interface = self._normalize_interface(bus.get("airway_interface"))
        oxygen_interface = self._oxygen_interface_for(interface, bus)
        oxygen = self._compute_niv_delivery(interface, bus) if interface in ("NIV_CPAP", "NIV_BIPAP") else self._compute_oxygen_delivery(interface, oxygen_interface, bus)

        if mode in ("NONE", "UNASSISTED") and interface not in ("HFNC", "LOW_FLOW_OXYGEN", "SIMPLE_MASK"):
            interface = "UNASSISTED"

        # Non-pressurised or HFNC spontaneous interfaces.
        spontaneous_nonvent = interface in ("UNASSISTED", "NONE", "LOW_FLOW_OXYGEN", "SIMPLE_MASK", "HFNC") or mode in ("NONE", "UNASSISTED")
        ambient = float(bus.get("ambient_airway_pressure_cmH2O")) if hasattr(bus.state, "ambient_airway_pressure_cmH2O") else float(self.params["ambient_airway_pressure_cmH2O"])

        if spontaneous_nonvent and interface in ("UNASSISTED", "NONE", "LOW_FLOW_OXYGEN", "SIMPLE_MASK", "HFNC"):
            effective_peep = float(oxygen["HFNC_distending_pressure_cmH2O"]) if interface == "HFNC" else 0.0
            pressure_source = "HFNC_flow" if interface == "HFNC" else ("oxygen_interface" if interface in ("LOW_FLOW_OXYGEN", "SIMPLE_MASK") else "ambient")
            note = "hfnc_oxygen_delivery_base" if interface == "HFNC" else "spontaneous_oxygen_delivery_base"
            bus.update({
                "airway_interface": "HFNC" if interface == "HFNC" else (interface if interface in ("LOW_FLOW_OXYGEN", "SIMPLE_MASK") else "UNASSISTED"),
                "intubated": False,
                "ventilator_connected": False,
                "airway_pressure_delivery_enabled": False,
                "unassisted_breathing_active": True,
                "spontaneous_airway_mode": True,
                "ambient_airway_pressure_cmH2O": ambient,
                "effective_external_PEEP_cmH2O": effective_peep,
                "airway_pressure_source": pressure_source,
                "airway_interface_revision": 1231,
                "airway_interface_note": note,
                "vent_mode": "NONE",
                "PEEP": effective_peep,
                "Paw": ambient + effective_peep,
                "Paw_current": ambient + effective_peep,
                "FiO2": float(oxygen["FiO2_delivered"]),
                "oxygen_delivery_revision": 1231,
                **oxygen,
            })
            return

        # Connected interfaces. v1.23.2 adds NIV mask proxies; v1.23.3 adds
        # ETT/tracheostomy resistance, cuff-leak and apparatus dead-space proxies.
        intubated = interface in ("ETT", "TRACHEOSTOMY")
        connected = interface in ("ETT", "TRACHEOSTOMY", "NIV_CPAP", "NIV_BIPAP")
        artificial = self._compute_artificial_airway(interface, bus) if intubated else {}
        peep = float(bus.get("PEEP"))
        if interface in ("NIV_CPAP", "NIV_BIPAP"):
            peep = float(oxygen.get("NIV_delivered_PEEP_cmH2O", peep))
        delivered_fio2 = float(oxygen.get("FiO2_delivered", bus.get("FiO2")))
        if intubated:
            delivered_fio2 = float(np.clip(delivered_fio2 * float(artificial.get("ETT_FiO2_delivery_efficiency", 1.0)), 0.21, 1.0))
        bus.update({
            "airway_interface": interface,
            "intubated": bool(intubated),
            "ventilator_connected": bool(connected),
            "airway_pressure_delivery_enabled": bool(connected),
            "unassisted_breathing_active": False,
            "spontaneous_airway_mode": interface in ("HFNC", "NIV_CPAP", "NIV_BIPAP"),
            "effective_external_PEEP_cmH2O": peep,
            "airway_pressure_source": "NIV_mask" if interface in ("NIV_CPAP", "NIV_BIPAP") else ("artificial_airway" if intubated else "ambient"),
            "airway_interface_revision": 1233 if intubated else (1232 if interface in ("NIV_CPAP", "NIV_BIPAP") else 1231),
            "airway_interface_note": "artificial_airway_resistance_deadspace_proxy" if intubated else ("niv_mask_pressure_leak_proxy" if interface in ("NIV_CPAP", "NIV_BIPAP") else "connected_interface_base"),
            "PEEP": float(peep),
            "PS_cmH2O": float(oxygen.get("NIV_delivered_PS_cmH2O", bus.get("PS_cmH2O") if hasattr(bus.state, "PS_cmH2O") else 0.0)),
            "Pinsp_cmH2O": float(oxygen.get("NIV_delivered_PS_cmH2O", bus.get("Pinsp_cmH2O") if hasattr(bus.state, "Pinsp_cmH2O") else 0.0)),
            "FiO2": delivered_fio2,
            "FiO2_delivered": delivered_fio2,
            "oxygen_delivery_revision": 1233 if intubated else (1232 if interface in ("NIV_CPAP", "NIV_BIPAP") else 1231),
            **oxygen,
            **artificial,
        })
