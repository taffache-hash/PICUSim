"""
EPALS-like Decision Engine — v3.1 Step 4.40
===========================================

Educational pattern-recognition layer for pediatric emergency simulation.
It reads physiological state and intervention markers, then writes ABCDE
priority, pattern labels, contextual prompts and incoherence warnings.

This module is not a clinical decision support system. Outputs are intended
for simulation debriefing and instructor feedback only.
"""

from __future__ import annotations

from typing import List

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


class EPALSDecisionModule(BaseModule):
    """Rule-bounded EPALS-style educational decision layer."""

    REVISION = 440

    def __init__(self, params: dict | None = None):
        defaults = {
            "severe_hypoxemia_sao2": 0.88,
            "hypotension_map": 55.0,
            "severe_hyperkalemia": 6.5,
            "severe_hypoglycemia": 45.0,
            "severe_hypercarbia": 70.0,
            "high_lactate": 4.0,
        }
        super().__init__(name="EPALSDecisionEngine", params={**defaults, **(params or {})})

    @property
    def input_keys(self) -> List[str]:
        return [
            "SaO2", "PaCO2", "EtCO2", "MAP", "HR", "RR_total", "pH_a", "K_mmol_L",
            "glucose_mg_dL", "lactate", "shock_type", "shock_stage", "shock_severity",
            "shock_decompensation_index", "airway_interface", "intubated", "ventilator_connected",
            "cardiac_rhythm", "has_pulse", "cardiac_arrest_active", "shockable_rhythm",
            "CPR_active", "epinephrine_bolus_count", "norad_mcg_kg_min",
            "adrenaline_mcg_kg_min", "dopamine_mcg_kg_min", "milrinone_mcg_kg_min",
            "cumulative_fluid_input_mL", "antibiotic_started", "antibiotic_coverage",
            "infection_load", "seizure_active", "ICP_mmHg", "tamponade_index",
        ]

    @property
    def output_keys(self) -> List[str]:
        return [
            "decision_engine_revision", "decision_priority", "decision_pattern",
            "decision_pattern_confidence", "decision_recommendation_primary",
            "decision_recommendation_secondary", "decision_warning",
            "decision_warning_level", "decision_abcde_step", "decision_escalation_needed",
            "decision_context_flags", "decision_last_update_s",
        ]

    @staticmethod
    def _get(bus: PhysiologicalBus, key: str, default=0.0):
        return bus.get(key) if hasattr(bus.state, key) else default

    @staticmethod
    def _clip(x: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, float(x)))

    def initialize(self, bus: PhysiologicalBus) -> None:
        self.step(bus, 0.0)

    def _context_flags(self, bus: PhysiologicalBus) -> list[str]:
        flags: list[str] = []
        if float(self._get(bus, "SaO2", 0.97)) < self.params["severe_hypoxemia_sao2"]:
            flags.append("hypoxemia")
        if float(self._get(bus, "PaCO2", 40.0)) >= self.params["severe_hypercarbia"]:
            flags.append("hypercarbia")
        if float(self._get(bus, "MAP", 65.0)) < self.params["hypotension_map"]:
            flags.append("hypotension")
        if float(self._get(bus, "lactate", 1.0)) >= self.params["high_lactate"]:
            flags.append("hyperlactatemia")
        if float(self._get(bus, "K_mmol_L", 4.0)) >= self.params["severe_hyperkalemia"]:
            flags.append("hyperkalemia")
        if float(self._get(bus, "glucose_mg_dL", 90.0)) <= self.params["severe_hypoglycemia"]:
            flags.append("hypoglycemia")
        if bool(self._get(bus, "cardiac_arrest_active", False)):
            flags.append("cardiac_arrest")
        shock_type = str(self._get(bus, "shock_type", "none"))
        if shock_type not in ("none", "normal", ""):
            flags.append(f"shock:{shock_type}")
        if bool(self._get(bus, "seizure_active", False)):
            flags.append("seizure")
        if float(self._get(bus, "ICP_mmHg", 10.0)) >= 25.0:
            flags.append("raised_icp")
        return flags

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        flags = self._context_flags(bus)
        sao2 = float(self._get(bus, "SaO2", 0.97))
        map_mmHg = float(self._get(bus, "MAP", 65.0))
        lactate = float(self._get(bus, "lactate", 1.0))
        k = float(self._get(bus, "K_mmol_L", 4.0))
        glucose = float(self._get(bus, "glucose_mg_dL", 90.0))
        pco2 = float(self._get(bus, "PaCO2", 40.0))
        shock_type = str(self._get(bus, "shock_type", "none"))
        shock_stage = str(self._get(bus, "shock_stage", "none"))
        shock_sev = self._clip(float(self._get(bus, "shock_severity", 0.0)), 0.0, 1.0)
        arrest = bool(self._get(bus, "cardiac_arrest_active", False))
        shockable = bool(self._get(bus, "shockable_rhythm", False))
        cpr = bool(self._get(bus, "CPR_active", False))
        intubated = bool(self._get(bus, "intubated", True))
        vent_connected = bool(self._get(bus, "ventilator_connected", True))
        airway_interface = str(self._get(bus, "airway_interface", "ETT"))
        norad = float(self._get(bus, "norad_mcg_kg_min", 0.0))
        adrenaline = float(self._get(bus, "adrenaline_mcg_kg_min", 0.0))
        dopamine = float(self._get(bus, "dopamine_mcg_kg_min", 0.0))
        fluids = float(self._get(bus, "cumulative_fluid_input_mL", 0.0))
        antibiotic_started = bool(self._get(bus, "antibiotic_started", False))
        infection_load = float(self._get(bus, "infection_load", 0.0))

        priority = "routine_monitoring"
        abcde = "E"
        pattern = "stable"
        confidence = 0.30
        primary = "Continue monitoring and reassess trends."
        secondary = "Review scenario objectives and recent interventions."
        warning = ""
        warning_level = "none"
        escalation = False

        if arrest:
            abcde = "C"
            priority = "cardiac_arrest_algorithm"
            pattern = "shockable_arrest" if shockable else "nonshockable_arrest"
            confidence = 0.95
            primary = "Start/continue high-quality CPR and follow arrest rhythm branch."
            secondary = "Defibrillate shockable rhythms; give epinephrine for non-shockable or ongoing arrest context."
            escalation = True
            if not cpr:
                warning = "Cardiac arrest detected but CPR_active is false."
                warning_level = "critical"
        elif sao2 < self.params["severe_hypoxemia_sao2"] or (not intubated and airway_interface in {"NONE", "UNASSISTED"}):
            abcde = "A/B"
            priority = "airway_breathing_first"
            pattern = "severe_hypoxemia" if sao2 < self.params["severe_hypoxemia_sao2"] else "unsecured_airway"
            confidence = self._clip(0.60 + (self.params["severe_hypoxemia_sao2"] - sao2) * 2.0, 0.60, 0.95)
            primary = "Open airway, optimize oxygen delivery, ventilation and call for advanced airway help."
            secondary = "Check interface, FiO2/PEEP, chest movement, capnography and reversible obstruction."
            escalation = True
            if intubated and not vent_connected:
                warning = "Patient is intubated but ventilator_connected is false during hypoxemia."
                warning_level = "high"
        elif shock_sev >= 0.35 or map_mmHg < self.params["hypotension_map"] or lactate >= self.params["high_lactate"]:
            abcde = "C"
            priority = "circulation_shock"
            pattern = f"{shock_type}_shock" if shock_type not in ("none", "normal", "") else "undifferentiated_shock"
            confidence = self._clip(0.45 + 0.45 * max(shock_sev, (self.params["hypotension_map"] - map_mmHg) / 35.0, lactate / 10.0), 0.45, 0.93)
            primary = "Treat shock phenotype: vascular access, fluid/vasoactive strategy and frequent reassessment."
            secondary = "Use ABCDE, lactate/perfusion trend and phenotype-specific reversible causes."
            escalation = shock_stage in {"decompensated", "critical"} or map_mmHg < self.params["hypotension_map"]
            vasoactive_running = max(norad, adrenaline, dopamine) > 0.0
            if shock_type in {"distributive", "septic"} and infection_load >= 0.4 and not antibiotic_started:
                warning = "Distributive/septic shock pattern without antibiotic_started flag."
                warning_level = "high"
            elif shock_type == "hypovolemic" and fluids <= 0.0 and not vasoactive_running:
                warning = "Hypovolemic shock pattern without fluid or vasoactive response marker."
                warning_level = "medium"
            elif shock_type == "cardiogenic" and fluids > 40.0 * max(float(self._get(bus, "weight_kg", 20.0)), 1.0):
                warning = "Large cumulative fluids in cardiogenic shock pattern; reassess overload risk."
                warning_level = "medium"
        elif k >= self.params["severe_hyperkalemia"]:
            abcde = "C/D"
            priority = "electrolyte_emergency"
            pattern = "hyperkalemia_risk"
            confidence = 0.85
            primary = "Stabilize myocardium and shift/remove potassium per scenario protocol."
            secondary = "Check ECG/rhythm, renal failure context, acidosis and potassium trend."
            escalation = True
        elif glucose <= self.params["severe_hypoglycemia"]:
            abcde = "D"
            priority = "neurologic_metabolic"
            pattern = "hypoglycemia"
            confidence = 0.88
            primary = "Treat glucose emergency and reassess neurologic status."
            secondary = "Look for insulin exposure, sepsis, adrenal/endocrine triggers."
            escalation = True
        elif pco2 >= self.params["severe_hypercarbia"]:
            abcde = "B"
            priority = "ventilation_failure"
            pattern = "hypercarbic_failure"
            confidence = 0.80
            primary = "Increase effective ventilation and check airway resistance/dead space."
            secondary = "Review ventilator settings, obstruction, sedation and respiratory muscle fatigue."
            escalation = True

        bus.update({
            "decision_engine_revision": self.REVISION,
            "decision_priority": priority,
            "decision_pattern": pattern,
            "decision_pattern_confidence": float(confidence),
            "decision_recommendation_primary": primary,
            "decision_recommendation_secondary": secondary,
            "decision_warning": warning,
            "decision_warning_level": warning_level,
            "decision_abcde_step": abcde,
            "decision_escalation_needed": bool(escalation),
            "decision_context_flags": ",".join(flags),
            "decision_last_update_s": float(self._get(bus, "t", 0.0)),
        })
