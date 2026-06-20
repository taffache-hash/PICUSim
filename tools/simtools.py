"""Shared utilities for PDT scenario analysis tools (v0.15).

These utilities are intentionally lightweight and depend only on the public
scenario/engine APIs. They are not clinical validation tools; they support
reproducible in-silico exploration, uncertainty analysis and reporting.
"""
from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import ScenarioLoader  # noqa: E402
from run_simulation import build_twin  # noqa: E402


SUMMARY_KEYS = [
    "SaO2", "PaO2", "PaCO2", "pH_a", "MAP", "HR", "CO", "Vt", "PEEP", "FiO2",
    "Paw", "Pplat", "Ppeak", "Pdriving", "MP", "recruited_frac", "VILI_risk",
    "overdistension_index", "atelectrauma_index", "lactate", "Hb", "fluid_balance",
    "urine_rate_mL_h", "GFR", "PAP_mean", "PVR", "RV_afterload_index", "ICP_mmHg",
    "CPP_mmHg", "pain_score", "stress_index", "sedation_score", "analgesia_score",
    "airway_obstruction_index", "auto_PEEP_obstructive", "R_rs", "sepsis_severity_score",
    "vasoplegia_index", "myocardial_depression_index", "endothelial_leak_index",
    "microcirculatory_failure_index", "fluid_responsiveness", "heart_lung_CO_mod",
    "cortisol_activity", "catecholamine_tone", "adrenal_insufficiency_index",
    "critical_illness_steroid_need_index", "insulin_resistance_index",
    "stress_hyperglycemia_index", "ADH_water_retention_index",
    "thyroid_suppression_index", "endocrine_severity_score", "glucose_mmol_L", "Na_mmol_L", "K_mmol_L", "Cl_mmol_L", "HCO3_mmol_L",
    "urea_mmol_L", "creatinine_mg_dL", "bilirubin_total_mg_dL", "GCS_proxy",
    "microbial_burden", "antibiotic_coverage", "infection_severity_score", "antibiotic_effect",
    "vq_adaptive_sigma", "vq_ards_weight", "vq_obstruction_weight", "vq_shock_weight", "vq_neonatal_weight",
    "C_vancomycin_mg_L", "vancomycin_target_attainment",
    "C_piperacillin_mg_L", "piperacillin_ft_above_MIC", "piperacillin_target_attainment",
    "C_insulin_mU_L", "insulin_glucose_clearance_signal", "insulin_hypoglycemia_risk",
    "C_morphine_ng_mL", "M6G_accumulation_proxy",
]

RISK_THRESHOLDS = {
    "hypoxemia_any": lambda df: (df.get("SaO2", pd.Series([1.0])) < 0.90).any(),
    "severe_hypoxemia_any": lambda df: (df.get("SaO2", pd.Series([1.0])) < 0.85).any(),
    "hypercapnia_any": lambda df: (df.get("PaCO2", pd.Series([0.0])) > 60.0).any(),
    "severe_acidemia_any": lambda df: (df.get("pH_a", pd.Series([7.4])) < 7.20).any(),
    "hypotension_any": lambda df: (df.get("MAP", pd.Series([65.0])) < 50.0).any(),
    "high_vili_any": lambda df: (df.get("VILI_risk", pd.Series([0.0])) > 0.50).any(),
    "high_lactate_final": lambda df: float(df.get("lactate", pd.Series([0.0])).iloc[-1]) > 4.0,
}


def load_yaml(path: str | Path) -> Dict[str, Any]:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def save_yaml(obj: Mapping[str, Any], path: str | Path) -> None:
    with open(path, "w") as f:
        yaml.safe_dump(dict(obj), f, sort_keys=False)


def scenario_path(name_or_path: str | Path) -> Path:
    p = Path(name_or_path)
    if p.exists():
        return p
    if p.suffix != ".yaml":
        p = p.with_suffix(".yaml")
    candidate = ROOT / "scenarios" / p.name
    if not candidate.exists():
        raise FileNotFoundError(f"Scenario not found: {name_or_path}")
    return candidate


def run_config(config: Dict[str, Any], dt: float = 0.1, quiet: bool = True) -> pd.DataFrame:
    loader = ScenarioLoader.from_dict(copy.deepcopy(config))
    bus = loader.build_bus()
    engine = build_twin(bus, loader.config, dt=dt)
    engine.verbose = not quiet
    engine.add_perturbations(loader.build_perturbations())
    return engine.run(float(loader.config.get("simulation_time_s", 300.0)))


def run_scenario(path_or_name: str | Path, dt: float = 0.1, quiet: bool = True) -> tuple[Dict[str, Any], pd.DataFrame]:
    path = scenario_path(path_or_name)
    config = load_yaml(path)
    return config, run_config(config, dt=dt, quiet=quiet)


def get_nested(config: Mapping[str, Any], dotted: str, default: Any = None) -> Any:
    cur: Any = config
    for part in dotted.split("."):
        if not isinstance(cur, Mapping) or part not in cur:
            return default
        cur = cur[part]
    return cur


def set_nested(config: Dict[str, Any], dotted: str, value: Any) -> None:
    cur: Dict[str, Any] = config
    parts = dotted.split(".")
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value


def infer_default_parameters(config: Mapping[str, Any]) -> Dict[str, Dict[str, float]]:
    """Return default Monte Carlo parameter specs for scenario family.

    Each spec is {'base': value, 'rel_sd': ..., 'min': ..., 'max': ...}. The
    defaults intentionally cover major uncertain axes without changing timeline
    events. Tools can override via external YAML.
    """
    candidates = {
        "respiratory.C_rs":      {"rel_sd": 0.20, "min_factor": 0.50, "max_factor": 1.60},
        "respiratory.R_rs":      {"rel_sd": 0.20, "min_factor": 0.50, "max_factor": 2.00},
        "respiratory.non_recruitable_frac": {"abs_sd": 0.06, "min": 0.0, "max": 0.60},
        "respiratory.FiO2":      {"abs_sd": 0.03, "min": 0.21, "max": 1.0},
        "cardiovascular.SVR":    {"rel_sd": 0.15, "min_factor": 0.50, "max_factor": 1.80},
        "cardiovascular.PVR":    {"rel_sd": 0.20, "min_factor": 0.50, "max_factor": 2.20},
        "cardiovascular.Hb":     {"abs_sd": 0.8, "min": 6.0, "max": 16.0},
        "metabolism.VO2":        {"rel_sd": 0.15, "min_factor": 0.60, "max_factor": 1.60},
        "metabolism.lactate":    {"rel_sd": 0.20, "min_factor": 0.50, "max_factor": 2.00},
        "sepsis.infection_load": {"abs_sd": 0.08, "min": 0.0, "max": 1.0},
        "airway.bronchospasm_index": {"abs_sd": 0.08, "min": 0.0, "max": 1.0},
        "airway.mucus_load": {"abs_sd": 0.08, "min": 0.0, "max": 1.0},
        "airway.small_airway_obstruction": {"abs_sd": 0.08, "min": 0.0, "max": 1.0},
    }
    specs: Dict[str, Dict[str, float]] = {}
    for key, spec in candidates.items():
        base = get_nested(config, key, None)
        if base is None:
            continue
        try:
            base_f = float(base)
        except Exception:
            continue
        s = dict(spec)
        s["base"] = base_f
        if "min_factor" in s:
            s["min"] = base_f * float(s.pop("min_factor"))
        if "max_factor" in s:
            s["max"] = base_f * float(s.pop("max_factor"))
        if "rel_sd" in s:
            s["sd"] = abs(base_f) * float(s.pop("rel_sd"))
        elif "abs_sd" in s:
            s["sd"] = float(s.pop("abs_sd"))
        specs[key] = s
    return specs


def sample_config(config: Dict[str, Any], specs: Mapping[str, Mapping[str, float]], rng: np.random.Generator) -> tuple[Dict[str, Any], Dict[str, float]]:
    cfg = copy.deepcopy(config)
    draws: Dict[str, float] = {}
    for key, spec in specs.items():
        base = float(spec.get("base", get_nested(config, key, 0.0)))
        sd = float(spec.get("sd", 0.0))
        lo = float(spec.get("min", -math.inf))
        hi = float(spec.get("max", math.inf))
        distribution = str(spec.get("distribution", "normal"))
        if distribution == "uniform":
            val = rng.uniform(lo if math.isfinite(lo) else base - sd, hi if math.isfinite(hi) else base + sd)
        else:
            val = rng.normal(base, sd)
        val = float(np.clip(val, lo, hi))
        set_nested(cfg, key, val)
        draws[key] = val
    return cfg, draws


def summarize_dataframe(df: pd.DataFrame, prefix: str = "") -> Dict[str, float | int]:
    out: Dict[str, float | int] = {}
    last = df.iloc[-1]
    for key in SUMMARY_KEYS:
        if key in df.columns:
            name = f"{prefix}{key}_final" if prefix else f"{key}_final"
            try:
                out[name] = float(last[key])
            except Exception:
                pass
    # clinically useful extrema
    for key, fn in [("SaO2", "min"), ("PaCO2", "max"), ("pH_a", "min"), ("MAP", "min"), ("VILI_risk", "max"), ("lactate", "max")]:
        if key in df.columns:
            val = getattr(df[key], fn)()
            out[f"{key}_{fn}"] = float(val)
    for label, func in RISK_THRESHOLDS.items():
        try:
            out[label] = int(bool(func(df)))
        except Exception:
            out[label] = 0
    return out


def aggregate_runs(rows: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    frame = pd.DataFrame(rows)
    metrics = {}
    numeric = frame.select_dtypes(include=[np.number])
    for col in numeric.columns:
        if col == "run":
            continue
        s = numeric[col].dropna()
        if len(s) == 0:
            continue
        metrics[col] = {
            "mean": float(s.mean()),
            "sd": float(s.std(ddof=1)) if len(s) > 1 else 0.0,
            "p05": float(s.quantile(0.05)),
            "p50": float(s.quantile(0.50)),
            "p95": float(s.quantile(0.95)),
            "min": float(s.min()),
            "max": float(s.max()),
        }
    return {"n": int(len(frame)), "metrics": metrics}


def write_json(obj: Mapping[str, Any], path: str | Path) -> None:
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False))
