"""
Scenario Engine v2 — v3.1 Step 4.44
====================================

Lightweight scenario-pack registry and validator used to hand off a curated
EPALS-oriented teaching set to Codex/UI layers. It does not change clinical
physiology directly; it standardizes scenario metadata, expected decision focus,
critical outputs and safe educational status.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml


SCENARIO_ENGINE_V2_REVISION = 444
_REQUIRED_TOP_LEVEL = {"name", "patient", "simulation_time_s"}
_REQUIRED_PATIENT = {"age_y", "weight_kg"}


@dataclass(frozen=True)
class ScenarioV2Entry:
    """Catalog entry for an educational scenario."""

    scenario_id: str
    path: str
    phenotype: str
    epals_focus: str
    complexity: str = "intermediate"
    expected_actions: List[str] = field(default_factory=list)
    key_outputs: List[str] = field(default_factory=list)
    debrief_questions: List[str] = field(default_factory=list)
    revision: int = SCENARIO_ENGINE_V2_REVISION


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def load_yaml(path: str | Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Scenario YAML must resolve to a mapping: {path}")
    return data


def validate_scenario_config(config: Dict[str, Any]) -> List[str]:
    """Return validation errors; empty list means suitable for v2 catalog use."""

    errors: List[str] = []
    missing = sorted(_REQUIRED_TOP_LEVEL - set(config.keys()))
    if missing:
        errors.append(f"missing_top_level:{','.join(missing)}")
    patient = config.get("patient", {}) or {}
    if not isinstance(patient, dict):
        errors.append("patient_not_mapping")
        patient = {}
    missing_patient = sorted(_REQUIRED_PATIENT - set(patient.keys()))
    if missing_patient:
        errors.append(f"missing_patient:{','.join(missing_patient)}")
    try:
        if float(config.get("simulation_time_s", 0.0)) <= 0:
            errors.append("simulation_time_nonpositive")
    except (TypeError, ValueError):
        errors.append("simulation_time_invalid")
    outputs = config.get("outputs", []) or []
    if not isinstance(outputs, list) or len(outputs) < 4:
        errors.append("outputs_too_sparse")
    return errors


class ScenarioEngineV2Catalog:
    """Load and validate an explicit scenario-engine v2 manifest."""

    def __init__(self, manifest: Dict[str, Any], root: str | Path):
        self.manifest = manifest
        self.root = Path(root)
        self.revision = int(manifest.get("revision", SCENARIO_ENGINE_V2_REVISION))
        self.entries = [self._entry(item) for item in manifest.get("scenarios", [])]

    @classmethod
    def from_yaml(cls, manifest_path: str | Path, root: str | Path | None = None) -> "ScenarioEngineV2Catalog":
        path = Path(manifest_path)
        return cls(load_yaml(path), root if root is not None else path.parents[1])

    def _entry(self, item: Dict[str, Any]) -> ScenarioV2Entry:
        return ScenarioV2Entry(
            scenario_id=str(item["id"]),
            path=str(item["path"]),
            phenotype=str(item.get("phenotype", "undifferentiated")),
            epals_focus=str(item.get("epals_focus", "ABCDE reassessment")),
            complexity=str(item.get("complexity", "intermediate")),
            expected_actions=_as_list(item.get("expected_actions")),
            key_outputs=_as_list(item.get("key_outputs")),
            debrief_questions=_as_list(item.get("debrief_questions")),
        )

    def scenario_paths(self) -> List[Path]:
        return [self.root / entry.path for entry in self.entries]

    def validate(self) -> Dict[str, List[str]]:
        results: Dict[str, List[str]] = {}
        for entry in self.entries:
            path = self.root / entry.path
            if not path.exists():
                results[entry.scenario_id] = ["missing_file"]
                continue
            errors = validate_scenario_config(load_yaml(path))
            if not entry.expected_actions:
                errors.append("missing_expected_actions")
            if not entry.key_outputs:
                errors.append("missing_key_outputs")
            results[entry.scenario_id] = errors
        return results

    def valid_ids(self) -> List[str]:
        validation = self.validate()
        return [sid for sid, errors in validation.items() if not errors]

    def summary(self) -> Dict[str, Any]:
        validation = self.validate()
        return {
            "scenario_engine_revision": self.revision,
            "scenario_count": len(self.entries),
            "valid_count": sum(1 for errors in validation.values() if not errors),
            "invalid_count": sum(1 for errors in validation.values() if errors),
            "scenario_ids": [entry.scenario_id for entry in self.entries],
            "validation": validation,
            "safety_status": self.manifest.get("safety_status", "educational/research alpha only"),
        }
