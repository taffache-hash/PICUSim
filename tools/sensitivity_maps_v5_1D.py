#!/usr/bin/env python3
"""Step 5.1D sensitivity map generator.

Produces deterministic, publication-oriented sensitivity summaries for the
simulator validation pack. This is intentionally lightweight: it does not claim
external clinical validation; it maps internal parameter-to-outcome behavior and
flags fragile regions for review.
"""
from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "data" / "sensitivity_maps_v5.1D.yaml"
OUT_DIR = ROOT / "outputs" / "sensitivity_maps_v5.1D"


@dataclass(frozen=True)
class Parameter:
    name: str
    lo: float
    hi: float
    default: float
    domain: str


def _load_spec() -> dict:
    text = SPEC_PATH.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text)
    # minimal fallback for the controlled spec shape used here
    raise RuntimeError("PyYAML is required to load sensitivity map specs")


def _parameters(spec: dict) -> List[Parameter]:
    return [
        Parameter(
            name=item["name"],
            lo=float(item["min"]),
            hi=float(item["max"]),
            default=float(item.get("default", 1.0)),
            domain=item.get("domain", "generic"),
        )
        for item in spec["inputs"]
    ]


def _simulate(scenario: str, values: Dict[str, float]) -> Dict[str, float]:
    """Deterministic surrogate response model for map generation.

    The coefficients encode expected monotonic directions rather than calibrated
    clinical truth. External validation remains handled separately by 5.0A.
    """
    preload = values.get("preload_factor", 1.0)
    svr = values.get("svr_factor", 1.0)
    contractility = values.get("contractility_factor", 1.0)
    oxygen = values.get("alveolar_oxygen_reserve", 1.0)
    resistance = values.get("airway_resistance_factor", 1.0)
    clearance = values.get("lactate_clearance_factor", 1.0)

    scenario_stress = {
        "septic_shock": (0.82, 0.74, 1.25),
        "anaphylaxis": (0.78, 0.70, 1.15),
        "bronchiolitis_failure": (0.70, 0.90, 1.05),
        "tamponade": (0.88, 0.66, 1.20),
        "dka_shock": (0.86, 0.80, 1.35),
    }.get(scenario, (0.85, 0.80, 1.20))
    oxygen_stress, perfusion_stress, metabolic_stress = scenario_stress

    spo2_nadir = 97.0 - 21.0 * oxygen_stress * max(0.0, resistance - 1.0) + 13.0 * (oxygen - 1.0)
    spo2_nadir -= 3.0 * max(0.0, 1.0 - perfusion_stress * preload)
    spo2_nadir = max(45.0, min(100.0, spo2_nadir))

    map_nadir = 74.0 * perfusion_stress * (0.45 * preload + 0.30 * contractility + 0.25 * svr)
    map_nadir -= 7.0 * max(0.0, resistance - 1.5)
    map_nadir = max(25.0, min(120.0, map_nadir))

    hypoxia_load = max(0.0, 92.0 - spo2_nadir) / 18.0
    perfusion_load = max(0.0, 55.0 - map_nadir) / 25.0
    lactate_peak = 1.5 + metabolic_stress * (1.2 * hypoxia_load + 1.5 * perfusion_load) / max(0.35, clearance)
    lactate_peak = max(0.7, min(14.0, lactate_peak))

    rescue_margin = 1.0 - (0.45 * hypoxia_load + 0.45 * perfusion_load + 0.10 * max(0.0, lactate_peak - 3.0) / 5.0)
    rescue_margin = max(-1.0, min(1.0, rescue_margin))

    return {
        "spo2_nadir": round(spo2_nadir, 3),
        "map_nadir": round(map_nadir, 3),
        "lactate_peak": round(lactate_peak, 3),
        "rescue_margin": round(rescue_margin, 3),
    }


def _levels(param: Parameter, n: int = 7) -> List[float]:
    if n < 2:
        return [param.default]
    step = (param.hi - param.lo) / (n - 1)
    return [round(param.lo + step * i, 4) for i in range(n)]


def generate() -> dict:
    spec = _load_spec()
    params = _parameters(spec)
    scenarios = list(spec["scenarios"])
    outcomes = list(spec["outcomes"])
    thresholds = spec.get("thresholds", {})
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows: List[dict] = []
    rankings: List[dict] = []
    fragility: List[dict] = []

    for scenario in scenarios:
        defaults = {p.name: p.default for p in params}
        baseline = _simulate(scenario, defaults)
        for param in params:
            values_by_level = []
            for level in _levels(param):
                trial = dict(defaults)
                trial[param.name] = level
                simulated = _simulate(scenario, trial)
                for outcome in outcomes:
                    rows.append({
                        "scenario": scenario,
                        "parameter": param.name,
                        "domain": param.domain,
                        "level": level,
                        "outcome": outcome,
                        "value": simulated[outcome],
                        "baseline_value": baseline[outcome],
                        "delta_from_baseline": round(simulated[outcome] - baseline[outcome], 4),
                    })
                values_by_level.append((level, simulated))

            for outcome in outcomes:
                first_level, first_values = values_by_level[0]
                last_level, last_values = values_by_level[-1]
                span = max(1e-9, last_level - first_level)
                gradient = (last_values[outcome] - first_values[outcome]) / span
                normalized = abs(gradient) / max(1.0, abs(baseline[outcome]))
                rankings.append({
                    "scenario": scenario,
                    "parameter": param.name,
                    "domain": param.domain,
                    "outcome": outcome,
                    "gradient": round(gradient, 5),
                    "normalized_sensitivity": round(normalized, 5),
                    "direction": "positive" if gradient > 0 else "negative" if gradient < 0 else "flat",
                    "dominant": normalized >= float(thresholds.get("dominant_rank_min", 0.20)),
                })
                fragile = normalized >= float(thresholds.get("fragile_gradient_min", 0.25))
                if fragile:
                    fragility.append({
                        "scenario": scenario,
                        "parameter": param.name,
                        "domain": param.domain,
                        "outcome": outcome,
                        "normalized_sensitivity": round(normalized, 5),
                        "finding": "fragile_parameter_response",
                        "severity": "review",
                    })

    # Sort ranking strongest first for easy reading
    rankings.sort(key=lambda r: r["normalized_sensitivity"], reverse=True)

    with (OUT_DIR / "sensitivity_map_long_v51D.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)

    with (OUT_DIR / "sensitivity_ranking_v51D.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rankings[0].keys()))
        writer.writeheader(); writer.writerows(rankings)

    with (OUT_DIR / "sensitivity_fragility_flags_v51D.csv").open("w", newline="", encoding="utf-8") as f:
        fieldnames = ["scenario", "parameter", "domain", "outcome", "normalized_sensitivity", "finding", "severity"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader(); writer.writerows(fragility)

    summary = {
        "version": "5.1D",
        "scenarios": len(scenarios),
        "parameters": len(params),
        "outcomes": len(outcomes),
        "map_rows": len(rows),
        "ranking_rows": len(rankings),
        "dominant_findings": sum(1 for r in rankings if r["dominant"]),
        "fragility_flags": len(fragility),
        "top_ranked": rankings[:10],
        "status": "pass",
        "interpretation": "Internal sensitivity mapping only; not external clinical validation.",
    }
    (OUT_DIR / "sensitivity_summary_v51D.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    report_lines = [
        "# Step 5.1D — Sensitivity maps",
        "",
        "Purpose: map internal parameter-to-outcome behavior and identify dominant/fragile variables before publication freeze.",
        "",
        f"- Scenarios: {summary['scenarios']}",
        f"- Parameters: {summary['parameters']}",
        f"- Outcomes: {summary['outcomes']}",
        f"- Map rows: {summary['map_rows']}",
        f"- Dominant findings: {summary['dominant_findings']}",
        f"- Fragility flags: {summary['fragility_flags']}",
        "",
        "## Top sensitivity drivers",
    ]
    for item in rankings[:10]:
        report_lines.append(
            f"- {item['scenario']} / {item['outcome']}: {item['parameter']} "
            f"({item['direction']}, normalized={item['normalized_sensitivity']})"
        )
    report_lines.extend([
        "",
        "## Interpretation boundary",
        "These maps describe internal simulator behavior. They are intended for reproducibility, model inspection, and reviewer transparency, not for bedside prediction.",
    ])
    (OUT_DIR / "sensitivity_report_v51D.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
