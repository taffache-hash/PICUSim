#!/usr/bin/env python3
"""Lightweight Morris elementary-effect screening for PDT scenarios (v0.46).

This implements a small, dependency-light Morris-style screening. It is meant
for methodological hardening and prioritisation, not for clinical validation or
formal variance decomposition.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from simtools import load_yaml, run_config, scenario_path, set_nested, summarize_dataframe  # noqa: E402

DEFAULT_SPEC = ROOT / "data" / "morris_specs_v0.46.yaml"
DEFAULT_OUTDIR = ROOT / "outputs" / "validation_pack"


def _write_json(obj: Dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True))


def _lin_from_unit(low: float, high: float, x: float) -> float:
    return float(low + (high - low) * x)


def _sample_start(k: int, rng: np.random.Generator, delta: float) -> np.ndarray:
    # Keep room for a positive elementary step. Directional signs are handled by
    # flipping the order of the pair rather than leaving the unit cube.
    upper = max(0.0, 1.0 - delta)
    return rng.uniform(0.0, upper, size=k)


def _summary_outcomes(summary: Dict[str, Any], outcomes: Iterable[str]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for key in outcomes:
        val = summary.get(key, float("nan"))
        try:
            out[key] = float(val)
        except Exception:
            out[key] = float("nan")
    return out


def _run_point(base_config: Dict[str, Any], param_names: List[str], param_specs: Dict[str, Any], unit_values: np.ndarray, dt: float, outcomes: List[str]) -> Dict[str, float]:
    cfg = copy.deepcopy(base_config)
    for name, u in zip(param_names, unit_values):
        ps = param_specs[name]
        val = _lin_from_unit(float(ps["low"]), float(ps["high"]), float(u))
        set_nested(cfg, name, val)
    df = run_config(cfg, dt=dt, quiet=True)
    return _summary_outcomes(summarize_dataframe(df), outcomes)


def morris_for_scenario(spec: Dict[str, Any], scenario_key: str, trajectories: int, levels: int, dt: float, seed: int, outcomes: List[str]) -> tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    scen_spec = spec["scenarios"][scenario_key]
    scenario_name = scen_spec.get("scenario", scenario_key)
    base_config = load_yaml(scenario_path(scenario_name))
    params: Dict[str, Any] = scen_spec["parameters"]
    param_names = list(params.keys())
    k = len(param_names)
    if k < 2:
        raise ValueError(f"Morris screening requires at least 2 parameters for {scenario_key}")
    if levels < 3:
        raise ValueError("levels must be >=3")
    # Classic Morris delta often p/[2(p-1)]. For p=4, delta=2/3.
    delta = float(spec.get("defaults", {}).get("delta_fraction", levels / (2 * (levels - 1))))
    rng = np.random.default_rng(seed)
    rows: List[Dict[str, Any]] = []
    eval_rows: List[Dict[str, Any]] = []

    for r in range(trajectories):
        order = rng.permutation(k)
        signs = rng.choice([-1.0, 1.0], size=k)
        x = _sample_start(k, rng, delta)
        # If sign is negative, start at x+delta and step down to x.
        x_current = np.where(signs < 0, x + delta, x).astype(float)
        y_current = _run_point(base_config, param_names, params, x_current, dt, outcomes)
        eval_rows.append({"scenario": scenario_key, "trajectory": r, "step": 0, **{f"u_{p}": float(v) for p, v in zip(param_names, x_current)}, **y_current})
        for step_index, param_idx in enumerate(order, start=1):
            p_name = param_names[param_idx]
            x_next = x_current.copy()
            x_next[param_idx] = float(np.clip(x_next[param_idx] + signs[param_idx] * delta, 0.0, 1.0))
            actual_delta_unit = x_next[param_idx] - x_current[param_idx]
            if abs(actual_delta_unit) < 1e-12:
                continue
            y_next = _run_point(base_config, param_names, params, x_next, dt, outcomes)
            eval_rows.append({"scenario": scenario_key, "trajectory": r, "step": step_index, **{f"u_{p}": float(v) for p, v in zip(param_names, x_next)}, **y_next})
            low = float(params[p_name]["low"])
            high = float(params[p_name]["high"])
            actual_delta_param = actual_delta_unit * (high - low)
            for outcome in outcomes:
                y0 = y_current.get(outcome, float("nan"))
                y1 = y_next.get(outcome, float("nan"))
                if math.isfinite(y0) and math.isfinite(y1) and abs(actual_delta_param) > 0:
                    ee = (y1 - y0) / actual_delta_param
                    rows.append({
                        "scenario": scenario_key,
                        "trajectory": r,
                        "step": step_index,
                        "parameter": p_name,
                        "parameter_label": params[p_name].get("label", p_name),
                        "outcome": outcome,
                        "elementary_effect": float(ee),
                        "abs_elementary_effect": float(abs(ee)),
                        "delta_param": float(actual_delta_param),
                        "y_before": float(y0),
                        "y_after": float(y1),
                    })
            x_current = x_next
            y_current = y_next

    effects = pd.DataFrame(rows)
    evals = pd.DataFrame(eval_rows)
    if effects.empty:
        summary = pd.DataFrame(columns=["scenario", "parameter", "parameter_label", "outcome", "mu", "mu_star", "sigma", "n", "rank_mu_star"])
    else:
        summary = (
            effects.groupby(["scenario", "parameter", "parameter_label", "outcome"])
            .agg(
                mu=("elementary_effect", "mean"),
                mu_star=("abs_elementary_effect", "mean"),
                sigma=("elementary_effect", "std"),
                n=("elementary_effect", "count"),
            )
            .reset_index()
        )
        summary["sigma"] = summary["sigma"].fillna(0.0)
        summary["rank_mu_star"] = summary.groupby(["scenario", "outcome"])["mu_star"].rank(method="dense", ascending=False).astype(int)
        summary = summary.sort_values(["scenario", "outcome", "rank_mu_star", "parameter"])
    meta = {
        "scenario": scenario_key,
        "scenario_file": f"{scenario_name}.yaml",
        "parameters": param_names,
        "outcomes": outcomes,
        "trajectories": trajectories,
        "levels": levels,
        "delta_fraction": delta,
        "dt_s": dt,
        "seed": seed,
        "n_effects": int(len(effects)),
        "n_evaluations": int(len(evals)),
    }
    return effects, summary, meta


def build_report(summary: pd.DataFrame, metas: List[Dict[str, Any]]) -> str:
    lines = [
        "# PDT v0.46 Morris screening report",
        "",
        "This is a lightweight Morris elementary-effect screening. It identifies influential parameters and possible non-linear/interaction signals; it is not clinical validation and not full Sobol variance decomposition.",
        "",
        "## Run metadata",
        "",
    ]
    for m in metas:
        lines.append(f"- **{m['scenario']}**: {m['n_evaluations']} model evaluations, {m['n_effects']} elementary effects, dt={m['dt_s']} s, trajectories={m['trajectories']}, parameters={len(m['parameters'])}.")
    lines.extend(["", "## Top findings by scenario/outcome", ""])
    if summary.empty:
        lines.append("No elementary effects were generated.")
        return "\n".join(lines) + "\n"
    for scenario in summary["scenario"].unique():
        lines.append(f"### {scenario}")
        sub_s = summary[summary["scenario"] == scenario]
        for outcome in sub_s["outcome"].unique():
            top = sub_s[sub_s["outcome"] == outcome].nsmallest(3, "rank_mu_star")
            if top["mu_star"].max() <= 0:
                continue
            lines.append(f"- **{outcome}**")
            for _, row in top.iterrows():
                lines.append(
                    f"  - {row['parameter_label']} (`{row['parameter']}`): mu*={row['mu_star']:.4g}, sigma={row['sigma']:.4g}, mu={row['mu']:.4g}"
                )
        lines.append("")
    lines.extend([
        "## Interpretation rules",
        "",
        "- Higher `mu*` = stronger average influence on the selected outcome.",
        "- Higher `sigma` = possible non-linearity, threshold behaviour or interaction with other varied parameters.",
        "- Parameter ranges are deliberate stress/screening ranges, not calibrated uncertainty distributions.",
    ])
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", default=str(DEFAULT_SPEC))
    parser.add_argument("--scenarios", nargs="*", help="scenario keys from the spec; defaults to all")
    parser.add_argument("--trajectories", type=int, help="override trajectories")
    parser.add_argument("--levels", type=int, help="override grid levels")
    parser.add_argument("--dt", type=float, help="override dt")
    parser.add_argument("--seed", type=int, help="override random seed")
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR))
    parser.add_argument("--fail-on-error", action="store_true")
    args = parser.parse_args(argv)

    spec_path = Path(args.spec)
    spec = yaml.safe_load(spec_path.read_text())
    defaults = spec.get("defaults", {})
    trajectories = int(args.trajectories or defaults.get("trajectories", 4))
    levels = int(args.levels or defaults.get("levels", 4))
    dt = float(args.dt or defaults.get("dt_s", 4.0))
    seed = int(args.seed or defaults.get("random_seed", 46))
    outcomes = list(defaults.get("outcomes", []))
    scenarios = args.scenarios or list(spec.get("scenarios", {}).keys())

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    all_effects: List[pd.DataFrame] = []
    all_summary: List[pd.DataFrame] = []
    metas: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []
    for i, scenario_key in enumerate(scenarios):
        try:
            effects, summary, meta = morris_for_scenario(spec, scenario_key, trajectories, levels, dt, seed + i * 1000, outcomes)
            all_effects.append(effects)
            all_summary.append(summary)
            metas.append(meta)
            print(f"{scenario_key}: {meta['n_evaluations']} evaluations, {meta['n_effects']} effects")
        except Exception as exc:
            errors.append({"scenario": scenario_key, "error": str(exc)})
            print(f"ERROR {scenario_key}: {exc}", file=sys.stderr)
            if args.fail_on_error:
                raise

    effects_df = pd.concat(all_effects, ignore_index=True) if all_effects else pd.DataFrame()
    summary_df = pd.concat(all_summary, ignore_index=True) if all_summary else pd.DataFrame()
    effects_path = outdir / "morris_screening_v046_effects.csv"
    summary_path = outdir / "morris_screening_v046_summary.csv"
    report_path = outdir / "morris_screening_v046_report.md"
    json_path = outdir / "morris_screening_v046_summary.json"
    effects_df.to_csv(effects_path, index=False)
    summary_df.to_csv(summary_path, index=False)
    report_path.write_text(build_report(summary_df, metas))
    _write_json({
        "version": "v0.46",
        "spec": str(spec_path.relative_to(ROOT) if spec_path.is_relative_to(ROOT) else spec_path),
        "scenarios_requested": scenarios,
        "scenarios_completed": [m["scenario"] for m in metas],
        "errors": errors,
        "total_evaluations": int(sum(m["n_evaluations"] for m in metas)),
        "total_effects": int(sum(m["n_effects"] for m in metas)),
        "outcomes": outcomes,
        "status": "PASS" if not errors else "REVIEW",
    }, json_path)
    print(f"Output: {outdir}")
    return 1 if errors and args.fail_on_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
