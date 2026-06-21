"""
Infection / Antimicrobial Basic Module — v0.26
==============================================

Qualitative infection-control layer for pediatric PICU simulation.

This module is intentionally *not* a detailed antibiotic PK/PD engine.  It
tracks common clinical constructs that are useful for scenario simulation:

  - microbial burden / infection load
  - antibiotic timing and coverage
  - source-control adequacy
  - culture-positivity probability
  - resistance / inadequate-coverage signal
  - escalation and de-escalation readiness
  - infection-resolution trajectory

The outputs feed the existing advanced-sepsis module through the shared
Bus variables `infection_load`, `antibiotic_effect`, and `source_control`.
It is intended for exploratory/educational use, not antimicrobial prescribing.
"""
from __future__ import annotations

import numpy as np
from typing import List

from core.base_module import BaseModule
from core.bus import PhysiologicalBus


class InfectionAntimicrobialModule(BaseModule):
    """Basic infection burden and antimicrobial-response module."""

    DEFAULT_PARAMS = {
        "infection_load": 0.0,
        "pathogen_virulence": 0.45,
        "pathogen_resistance_index": 0.15,
        "source_control": 0.0,
        "antibiotic_coverage": 0.0,
        "antibiotic_started": False,
        "infection_focus": "unknown",  # pneumonia|abdominal|line|urinary|cns|unknown
        "growth_tau_s": 7200.0,
        "kill_tau_s": 3600.0,
        "culture_tau_s": 1800.0,
    }

    def __init__(self, params: dict | None = None):
        merged = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(name="InfectionAntimicrobial", params=merged)
        self._microbial_burden = float(merged["infection_load"])
        self._antibiotic_start_time_s: float | None = None
        self._culture_probability = 0.0
        self._hours_without_effective_antibiotic = 0.0

    @property
    def input_keys(self) -> List[str]:
        return [
            "infection_load", "source_control", "antibiotic_effect",
            "antibiotic_started", "antibiotic_coverage",
            "pathogen_virulence", "pathogen_resistance_index",
            "culture_drawn", "culture_positive", "T_core", "WBC_count",
            "neutrophil_count", "lactate", "MAP", "cytokine_drive",
            "sepsis_severity_score", "procalcitonin_proxy", "CRP_proxy",
        ]

    @property
    def output_keys(self) -> List[str]:
        return [
            "microbial_burden", "infection_load", "antibiotic_effect",
            "antibiotic_coverage", "antibiotic_delay_harm_index",
            "antimicrobial_kill_rate", "infection_resolution_rate",
            "culture_positivity_probability", "culture_positive",
            "source_control_need_index", "antimicrobial_escalation_score",
            "antimicrobial_deescalation_readiness", "inadequate_coverage_index",
            "infection_severity_score", "procalcitonin_proxy", "CRP_proxy",
            "infection_fever_drive", "infection_lactate_mod",
        ]

    @staticmethod
    def _clip01(x: float) -> float:
        return float(np.clip(x, 0.0, 1.0))

    def initialize(self, bus: PhysiologicalBus) -> None:
        self._microbial_burden = float(np.clip(bus.get("infection_load"), 0.0, 1.0))
        if hasattr(bus.state, "microbial_burden"):
            self._microbial_burden = max(self._microbial_burden, float(bus.get("microbial_burden")))
        antibiotic_started = bool(getattr(bus.state, "antibiotic_started", False))
        if antibiotic_started:
            self._antibiotic_start_time_s = 0.0
        self._culture_probability = float(np.clip(getattr(bus.state, "culture_positivity_probability", 0.0), 0.0, 1.0))
        bus.update({
            "microbial_burden": self._microbial_burden,
            "infection_load": self._microbial_burden,
            "infection_focus": str(getattr(bus.state, "infection_focus", self.params.get("infection_focus", "unknown"))),
            "pathogen_virulence": float(np.clip(getattr(bus.state, "pathogen_virulence", self.params["pathogen_virulence"]), 0.0, 1.0)),
            "pathogen_resistance_index": float(np.clip(getattr(bus.state, "pathogen_resistance_index", self.params["pathogen_resistance_index"]), 0.0, 1.0)),
        })

    def step(self, bus: PhysiologicalBus, dt: float) -> None:
        t = float(bus.get("t"))
        # Timeline may directly alter these variables.
        self._microbial_burden = float(np.clip(max(bus.get("infection_load"), getattr(bus.state, "microbial_burden", 0.0)), 0.0, 1.0))
        virulence = float(np.clip(getattr(bus.state, "pathogen_virulence", self.params["pathogen_virulence"]), 0.0, 1.0))
        resistance = float(np.clip(getattr(bus.state, "pathogen_resistance_index", self.params["pathogen_resistance_index"]), 0.0, 1.0))
        source_control = float(np.clip(bus.get("source_control"), 0.0, 1.0))
        antibiotic_started = bool(getattr(bus.state, "antibiotic_started", False))
        coverage = float(np.clip(getattr(bus.state, "antibiotic_coverage", 0.0), 0.0, 1.0))
        culture_drawn = bool(getattr(bus.state, "culture_drawn", False))

        if antibiotic_started and self._antibiotic_start_time_s is None:
            self._antibiotic_start_time_s = t

        effective_coverage = float(np.clip(coverage * (1.0 - 0.72 * resistance), 0.0, 1.0))
        inadequate_coverage = self._clip01(self._microbial_burden * (1.0 - effective_coverage) * (0.55 + 0.45 * resistance))

        if not antibiotic_started or effective_coverage < 0.25:
            self._hours_without_effective_antibiotic += dt / 3600.0
        else:
            self._hours_without_effective_antibiotic = max(0.0, self._hours_without_effective_antibiotic - dt / 5400.0)
        delay_harm = self._clip01(self._hours_without_effective_antibiotic / 0.75 * self._microbial_burden)

        # Microbial trajectory: virulence-driven growth minus antibiotic/source-control effect.
        growth = (0.20 + 0.80 * virulence) * self._microbial_burden * (1.0 - self._microbial_burden) / float(self.params["growth_tau_s"])
        kill_rate = effective_coverage * (0.20 + 0.80 * source_control) / float(self.params["kill_tau_s"])
        resolution_rate = float(np.clip(kill_rate * self._microbial_burden, 0.0, 0.005))
        dB = (growth - resolution_rate) * dt
        self._microbial_burden = float(np.clip(self._microbial_burden + dB, 0.0, 1.0))

        # Culture positivity is a probability proxy, not a stochastic result by default.
        fever_drive = self._clip01((float(bus.get("T_core")) - 37.5) / 2.5)
        lact_drive = self._clip01((float(bus.get("lactate")) - 2.0) / 6.0)
        wbc = float(getattr(bus.state, "WBC_count", 8.0))
        wbc_drive = self._clip01(abs(wbc - 8.0) / 18.0)
        target_culture_prob = self._clip01(0.70 * self._microbial_burden + 0.10 * fever_drive + 0.10 * lact_drive + 0.10 * wbc_drive)
        if culture_drawn:
            alpha_c = 1.0 - np.exp(-dt / float(self.params["culture_tau_s"]))
            self._culture_probability += alpha_c * (target_culture_prob - self._culture_probability)
        else:
            # probability exists biologically, but no culture has been drawn.
            self._culture_probability += (target_culture_prob * 0.25 - self._culture_probability) * (dt / 7200.0)
        self._culture_probability = float(np.clip(self._culture_probability, 0.0, 1.0))

        # Biomarker proxies: slow qualitative signals.
        procal_target = self._clip01(0.80 * self._microbial_burden + 0.15 * lact_drive + 0.05 * delay_harm)
        crp_target = self._clip01(0.65 * self._microbial_burden + 0.25 * fever_drive + 0.10 * wbc_drive)
        procal = float(getattr(bus.state, "procalcitonin_proxy", 0.0))
        crp = float(getattr(bus.state, "CRP_proxy", 0.0))
        procal += (procal_target - procal) * (dt / 1800.0)
        crp += (crp_target - crp) * (dt / 5400.0)
        procal = float(np.clip(procal, 0.0, 1.0))
        crp = float(np.clip(crp, 0.0, 1.0))

        source_need = self._clip01(self._microbial_burden * (1.0 - source_control) * (0.70 + 0.30 * virulence))
        escalation = self._clip01(0.42 * inadequate_coverage + 0.25 * source_need + 0.18 * delay_harm + 0.15 * lact_drive)
        deescalation = self._clip01((1.0 - self._microbial_burden) * effective_coverage * source_control * (1.0 - lact_drive) * (1.0 - fever_drive))
        severity = self._clip01(0.40 * self._microbial_burden + 0.20 * inadequate_coverage + 0.15 * source_need + 0.15 * lact_drive + 0.10 * delay_harm)

        antibiotic_effect_model = float(np.clip(effective_coverage * (0.25 + 0.75 * source_control) * (1.0 - 0.35 * delay_harm), 0.0, 1.0))
        # v3.2 public-polish deviation fix:
        # Timeline scenarios sometimes use `set_antibiotic_effect` as an
        # instructor-level proxy for early antimicrobial effect.  The infection
        # module used to overwrite that direct perturbation on the next step
        # when antibiotic coverage was not also encoded, making the therapeutic
        # event invisible to AdvancedSepsisModule.  Preserve a direct timeline
        # value as a floor, while still allowing the model-derived coverage/
        # source-control effect to exceed it.
        antibiotic_effect_floor = float(np.clip(getattr(bus.state, "antibiotic_effect", 0.0), 0.0, 1.0))
        antibiotic_effect = float(np.clip(max(antibiotic_effect_model, antibiotic_effect_floor), 0.0, 1.0))
        infection_fever_drive = self._clip01(0.55 * self._microbial_burden + 0.25 * procal + 0.20 * crp)
        infection_lactate_mod = float(np.clip(1.0 + 0.45 * severity + 0.30 * delay_harm, 1.0, 2.2))

        bus.update({
            "microbial_burden": self._microbial_burden,
            "infection_load": self._microbial_burden,
            "antibiotic_effect": antibiotic_effect,
            "antibiotic_coverage": coverage,
            "antibiotic_delay_harm_index": delay_harm,
            "antimicrobial_kill_rate": float(kill_rate * 3600.0),  # qualitative /h
            "infection_resolution_rate": float(resolution_rate * 3600.0),
            "culture_positivity_probability": self._culture_probability,
            "culture_positive": bool(self._culture_probability > 0.55 and culture_drawn),
            "source_control_need_index": source_need,
            "antimicrobial_escalation_score": escalation,
            "antimicrobial_deescalation_readiness": deescalation,
            "inadequate_coverage_index": inadequate_coverage,
            "infection_severity_score": severity,
            "procalcitonin_proxy": procal,
            "CRP_proxy": crp,
            "infection_fever_drive": infection_fever_drive,
            "infection_lactate_mod": infection_lactate_mod,
        })
