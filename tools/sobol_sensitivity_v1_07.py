#!/usr/bin/env python3
"""Lightweight Sobol-style sensitivity indices for PDT scenarios (v1.07).

This tool estimates first-order (S1) and total-order (ST) sensitivity indices
using a Saltelli/Jansen Monte Carlo design:

    evaluations = N * (D + 2)

where N is the number of paired base samples and D is the number of uncertain
parameters. The implementation is dependency-light and deliberately small; it
is intended for internal uncertainty ranking, not for calibrated external
validation.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from simtools import load_yaml, run_config, scenario_path, set_nested, summarize_dataframe  # noqa: E402

DEFAULT_SPEC = ROOT / "data" / "sobol_specs_v1.07.yaml"
DEFAULT_OUTDIR = ROOT / "outputs" / "sobol_sensitivity_v1.07"


def _write_json(obj: Dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True))


def _lin_from_unit(low: float, high: float, x: float) -> float:
    return float(low + (high - low) * x)


def _finite_float(value: Any) -> float:
    try:
        v = float(value)
    except Exception:
        return float("nan")
    return v if math.isfinite(v) else float("nan")


def _summary_outcomes(summary: Dict[str, Any], outcomes: Iterable[str]) -> Dict[str, float]:
    return {key: _finite_float(summary.get(key, float("nan"))) for key in outcomes}


def _make_config(base_config: Dict[str, Any], param_names: List[str], param_specs: Dict[str, Any], unit_values: np.ndarray) -> Tuple[Dict[str, Any], Dict[str, float]]:
    cfg = copy.deepcopy(base_config)
    values: Dict[str, float] = {}
    for name, u in zip(param_names, unit_values):
        ps = param_specs[name]
        val = _lin_from_unit(float(ps["low"]), float(ps["high"]), float(u))
        set_nested(cfg, name, val)
        values[name] = val
    return cfg, values


def _run_point(base_config: Dict[str, Any], param_names: List[str], param_specs: Dict[str, Any], unit_values: np.ndarray, dt: float, outcomes: List[str]) -> Dict[str, float]:
    cfg, _ = _make_config(base_config, param_names, param_specs, unit_values)
    df = run_config(cfg, dt=dt, quiet=True)
    return _summary_outcomes(summarize_dataframe(df), outcomes)


def _variance(y_a: np.ndarray, y_b: np.ndarray) -> float:
    y = np.concatenate([y_a, y_b]).astype(float)
    y = y[np.isfinite(y)]
    if len(y) < 2:
        return 0.0
    return float(np.var(y, ddof=1))


def _safe_index(num: float, den: float) -> float:
    if not math.isfinite(num) or not math.isfinite(den) or den <= 1e-12:
        return float("nan")
    return float(num / den)


def sobol_for_scenario(spec: Dict[str, Any], scenario_key: str, base_samples: int, dt: float, seed: int, outcomes: List[str]) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    scen_spec = spec["scenarios"][scenario_key]
    scenario_name = scen_spec.get("scenario", scenario_key)
    base_config = load_yaml(scenario_path(scenario_name))
    params: Dict[str, Any] = scen_spec["parameters"]
    param_names = list(params.keys())
    d = len(param_names)
    if d < 2:
        raise ValueError(f"Sobol sensitivity requires at least 2 parameters for {scenario_key}")
    if base_samples < 2:
        raise ValueError("base_samples must be >=2")

    rng = np.random.default_rng(seed)
    A = rng.uniform(0.0, 1.0, size=(base_samples, d))
    B = rng.uniform(0.0, 1.0, size=(base_samples, d))

    rows: List[Dict[str, Any]] = []
    eval_rows: List[Dict[str, Any]] = []
    y_a_by_outcome: Dict[str, List[float]] = {o: [] for o in outcomes}
    y_b_by_outcome: Dict[str, List[float]] = {o: [] for o in outcomes}
    y_ab_by_param_outcome: Dict[str, Dict[str, List[float]]] = {p: {o: [] for o in outcomes} for p in param_names}

    start = time.time()
    for n in range(base_samples):
        for matrix_name, u in [("A", A[n]), ("B", B[n])]:
            y = _run_point(base_config, param_names, params, u, dt, outcomes)
            _, values = _make_config(base_config, param_names, params, u)
            eval_rows.append({
                "scenario": scenario_key,
                "sample": n,
                "matrix": matrix_name,
                "parameter_replaced": "",
                **{f"value__{k}": v for k, v in values.items()},
                **y,
            })
            target = y_a_by_outcome if matrix_name == "A" else y_b_by_outcome
            for outcome, val in y.items():
                target[outcome].append(val)

        for j, param_name in enumerate(param_names):
            AB = A[n].copy()
            AB[j] = B[n, j]
            y = _run_point(base_config, param_names, params, AB, dt, outcomes)
            _, values = _make_config(base_config, param_names, params, AB)
            eval_rows.append({
                "scenario": scenario_key,
                "sample": n,
                "matrix": "AB",
                "parameter_replaced": param_name,
                **{f"value__{k}": v for k, v in values.items()},
                **y,
            })
            for outcome, val in y.items():
                y_ab_by_param_outcome[param_name][outcome].append(val)

    for outcome in outcomes:
        y_a = np.asarray(y_a_by_outcome[outcome], dtype=float)
        y_b = np.asarray(y_b_by_outcome[outcome], dtype=float)
        var_y = _variance(y_a, y_b)
        mean_y = float(np.nanmean(np.concatenate([y_a, y_b]))) if len(y_a) and len(y_b) else float("nan")
        for param_name in param_names:
            y_ab = np.asarray(y_ab_by_param_outcome[param_name][outcome], dtype=float)
            # Saltelli first-order estimator: E[f(B) * (f(AB_i) - f(A))] / Var(Y)
            s1_raw = _safe_index(float(np.nanmean(y_b * (y_ab - y_a))), var_y)
            # Jansen total-order estimator: 0.5 * E[(f(A) - f(AB_i))^2] / Var(Y)
            st_raw = _safe_index(float(0.5 * np.nanmean((y_a - y_ab) ** 2)), var_y)
            s1_clipped = float(np.clip(s1_raw, 0.0, 1.0)) if math.isfinite(s1_raw) else float("nan")
            st_clipped = float(np.clip(st_raw, 0.0, 1.0)) if math.isfinite(st_raw) else float("nan")
            rows.append({
                "scenario": scenario_key,
                "parameter": param_name,
                "parameter_label": params[param_name].get("label", param_name),
                "outcome": outcome,
                "S1_raw": s1_raw,
                "ST_raw": st_raw,
                "S1": s1_clipped,
                "ST": st_clipped,
                "variance": var_y,
                "mean_output": mean_y,
                "base_samples": int(base_samples),
                "rank_ST": 0,
            })

    indices = pd.DataFrame(rows)
    evaluations = pd.DataFrame(eval_rows)
    if not indices.empty:
        # Rank finite clipped total-order estimates first. Outcomes with near-zero
        # variance can legitimately produce NaN indices; keep them in the CSV but
        # push them to the bottom of the ranking.
        rank_source = indices["ST"].where(np.isfinite(indices["ST"]), -1.0)
        indices["rank_ST"] = rank_source.groupby([indices["scenario"], indices["outcome"]]).rank(method="dense", ascending=False).astype(int)
        indices = indices.sort_values(["scenario", "outcome", "rank_ST", "parameter"])

    meta = {
        "scenario": scenario_key,
        "scenario_file": f"{scenario_name}.yaml",
        "parameters": param_names,
        "outcomes": outcomes,
        "base_samples": int(base_samples),
        "dt_s": float(dt),
        "seed": int(seed),
        "n_parameters": int(d),
        "n_evaluations": int(len(evaluations)),
        "expected_evaluations": int(base_samples * (d + 2)),
        "n_indices": int(len(indices)),
        "runtime_s": float(time.time() - start),
    }
    return indices, evaluations, meta


def build_report(indices: pd.DataFrame, metas: List[Dict[str, Any]]) -> str:
    lines = [
        "# PDT v1.07 Sobol sensitivity report",
        "",
        "This report estimates first-order (`S1`) and total-order (`ST`) sensitivity indices using a lightweight Saltelli/Jansen Monte Carlo design.",
        "The aim is variance-based parameter ranking for model development. It is not clinical validation and the default sample size is intentionally small for fast regression checks.",
        "",
        "## Run metadata",
        "",
    ]
    for m in metas:
        lines.append(f"- **{m['scenario']}**: {m['n_evaluations']} model evaluations, {m['n_parameters']} parameters, N={m['base_samples']}, dt={m['dt_s']} s, runtime={m['runtime_s']:.1f} s.")
    lines.extend(["", "## Top total-order drivers by scenario/outcome", ""])
    if indices.empty:
        lines.append("No indices were generated.")
        return "\n".join(lines) + "\n"
    for scenario in indices["scenario"].unique():
        lines.append(f"### {scenario}")
        sub_s = indices[indices["scenario"] == scenario]
        for outcome in sub_s["outcome"].unique():
            sub_o = sub_s[sub_s["outcome"] == outcome].sort_values(["rank_ST", "parameter"])
            top = sub_o.head(3)
            if top["ST"].fillna(0).max() <= 0:
                continue
            lines.append(f"- **{outcome}**")
            for _, row in top.iterrows():
                lines.append(
                    f"  - {row['parameter_label']} (`{row['parameter']}`): ST={row['ST']:.3f}, S1={row['S1']:.3f}, variance={row['variance']:.4g}"
                )
        lines.append("")
    lines.extend([
        "## Interpretation rules",
        "",
        "- `S1` estimates the direct variance contribution of a parameter when varied alone.",
        "- `ST` estimates the total contribution, including interactions and non-linear effects.",
        "- Negative raw estimates can occur with small Monte Carlo samples; clipped values are provided for ranking, while raw values are preserved in the CSV.",
        "- Parameter ranges are stress-test uncertainty ranges, not calibrated probability distributions.",
    ])
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", default=str(DEFAULT_SPEC))
    parser.add_argument("--scenarios", nargs="*", help="scenario keys from the spec; defaults to all")
    parser.add_argument("--base-samples", type=int, help="override base sample count N")
    parser.add_argument("--dt", type=float, help="override dt")
    parser.add_argument("--seed", type=int, help="override random seed")
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR))
    parser.add_argument("--fail-on-error", action="store_true")
    args = parser.parse_args(argv)

    spec_path = Path(args.spec)
    spec = yaml.safe_load(spec_path.read_text())
    defaults = spec.get("defaults", {})
    base_samples = int(args.base_samples or defaults.get("base_samples", 4))
    dt = float(args.dt or defaults.get("dt_s", 10.0))
    seed = int(args.seed or defaults.get("random_seed", 107))
    outcomes = list(defaults.get("outcomes", []))
    scenarios = args.scenarios or list(spec.get("scenarios", {}).keys())

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    all_indices: List[pd.DataFrame] = []
    all_evals: List[pd.DataFrame] = []
    metas: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []

    for i, scenario_key in enumerate(scenarios):
        try:
            idx, ev, meta = sobol_for_scenario(spec, scenario_key, base_samples, dt, seed + i * 1000, outcomes)
            all_indices.append(idx)
            all_evals.append(ev)
            metas.append(meta)
            print(f"{scenario_key}: {meta['n_evaluations']} evaluations, {meta['n_indices']} indices")
        except Exception as exc:
            errors.append({"scenario": scenario_key, "error": str(exc)})
            print(f"ERROR {scenario_key}: {exc}", file=sys.stderr)
            if args.fail_on_error:
                raise

    indices_df = pd.concat(all_indices, ignore_index=True) if all_indices else pd.DataFrame()
    evals_df = pd.concat(all_evals, ignore_index=True) if all_evals else pd.DataFrame()
    indices_path = outdir / "sobol_sensitivity_v107_indices.csv"
    evals_path = outdir / "sobol_sensitivity_v107_evaluations.csv"
    report_path = outdir / "sobol_sensitivity_v107_report.md"
    json_path = outdir / "sobol_sensitivity_v107_summary.json"
    indices_df.to_csv(indices_path, index=False)
    evals_df.to_csv(evals_path, index=False)
    report_path.write_text(build_report(indices_df, metas))
    _write_json({
        "version": "v1.07",
        "method": "saltelli_jansen_monte_carlo",
        "spec": str(spec_path.relative_to(ROOT) if spec_path.is_relative_to(ROOT) else spec_path),
        "scenarios_requested": scenarios,
        "scenarios_completed": [m["scenario"] for m in metas],
        "errors": errors,
        "base_samples": base_samples,
        "dt_s": dt,
        "total_evaluations": int(sum(m["n_evaluations"] for m in metas)),
        "total_indices": int(sum(m["n_indices"] for m in metas)),
        "outcomes": outcomes,
        "status": "PASS" if not errors else "REVIEW",
    }, json_path)
    print(f"Output: {outdir}")
    return 1 if errors and args.fail_on_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
