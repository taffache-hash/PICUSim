#!/usr/bin/env python3
"""PDT v5.0B Monte Carlo stress runner.

Runs randomized scenario perturbations and records stability/plausibility
signals. This is an in-silico robustness gate, not clinical validation.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.simtools import (  # noqa: E402
    aggregate_runs,
    infer_default_parameters,
    load_yaml,
    run_config,
    sample_config,
    scenario_path,
    summarize_dataframe,
    write_json,
)


def load_spec(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _bounded_duration_config(config: Dict[str, Any], max_runtime_s: float | None) -> Dict[str, Any]:
    cfg = dict(config)
    if max_runtime_s is not None:
        cfg["simulation_time_s"] = min(float(cfg.get("simulation_time_s", max_runtime_s)), float(max_runtime_s))
    return cfg


def _finite_values(row: Mapping[str, Any]) -> bool:
    for value in row.values():
        if isinstance(value, (float, int)) and not math.isfinite(float(value)):
            return False
    return True


def plausibility_flags(row: Mapping[str, Any], bounds: Mapping[str, Iterable[float]]) -> List[str]:
    flags: List[str] = []
    if not _finite_values(row):
        flags.append("non_finite_numeric")
    for key, interval in bounds.items():
        if key not in row:
            continue
        try:
            value = float(row[key])
            low, high = [float(x) for x in interval]
        except Exception:
            continue
        if not math.isfinite(value):
            flags.append(f"{key}:non_finite")
        elif value < low or value > high:
            flags.append(f"{key}:outside_{low:g}_{high:g}")
    return flags


def run_one_scenario(
    scenario: str,
    n: int,
    dt: float,
    seed: int,
    bounds: Mapping[str, Iterable[float]],
    max_runtime_s: float | None,
) -> tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    base_path = scenario_path(scenario)
    base_cfg = load_yaml(base_path)
    base_cfg = _bounded_duration_config(base_cfg, max_runtime_s)
    specs = infer_default_parameters(base_cfg)
    rng = np.random.default_rng(seed)
    rows: List[Dict[str, Any]] = []
    draw_rows: List[Dict[str, Any]] = []
    for run_idx in range(int(n)):
        sampled, draws = sample_config(base_cfg, specs, rng)
        row: Dict[str, Any] = {"scenario": scenario, "run": run_idx, "seed": seed + run_idx, "run_error": ""}
        try:
            df = run_config(sampled, dt=dt, quiet=True)
            row.update(summarize_dataframe(df))
        except Exception as exc:  # recorded for robustness audit
            row["run_error"] = repr(exc)
        flags = plausibility_flags(row, bounds)
        if row.get("run_error"):
            flags.append("run_error")
        row["plausibility_flags"] = ";".join(flags)
        row["pass_stability"] = int(not flags)
        rows.append(row)
        drow = {"scenario": scenario, "run": run_idx}
        drow.update(draws)
        draw_rows.append(drow)
    summary = aggregate_runs(rows)
    summary.update({
        "scenario": scenario,
        "runs": int(n),
        "stable_runs": int(sum(int(r.get("pass_stability", 0)) for r in rows)),
        "flagged_runs": int(sum(1 for r in rows if r.get("plausibility_flags"))),
        "parameter_count": len(specs),
        "parameters": sorted(specs.keys()),
    })
    return pd.DataFrame(rows), pd.DataFrame(draw_rows), summary


def write_markdown(path: Path, summaries: List[Dict[str, Any]], spec: Mapping[str, Any]) -> None:
    total_runs = sum(int(s.get("runs", 0)) for s in summaries)
    flagged = sum(int(s.get("flagged_runs", 0)) for s in summaries)
    lines = [
        "# Step 5.0B — Massive Monte Carlo Stress Report",
        "",
        "Scope: randomized in-silico robustness audit across benchmark scenarios.",
        "",
        "This is **not** external validation and **not** medical decision support.",
        "It checks numerical stability, bounded physiology and outlier behavior before the larger validation pack.",
        "",
        f"Spec version: **{spec.get('version', '')}**",
        f"Total runs: **{total_runs}**",
        f"Flagged runs: **{flagged}**",
        "",
        "| Scenario | Runs | Stable | Flagged | Parameters varied |",
        "|---|---:|---:|---:|---:|",
    ]
    for s in summaries:
        lines.append(
            f"| {s.get('scenario')} | {s.get('runs')} | {s.get('stable_runs')} | "
            f"{s.get('flagged_runs')} | {s.get('parameter_count')} |"
        )
    lines += ["", "## Interpretation", ""]
    if flagged:
        lines.append("Flagged runs should be reviewed as edge cases before promotion to publication-grade validation.")
    else:
        lines.append("No numerical or biological-boundary flags were detected in this targeted run set.")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default=str(ROOT / "data" / "monte_carlo_specs_v5.0B.yaml"))
    ap.add_argument("--outdir", default=str(ROOT / "outputs" / "monte_carlo_v5.0B"))
    ap.add_argument("--n", type=int, default=None)
    ap.add_argument("--dt", type=float, default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--scenarios", nargs="*", default=None)
    ap.add_argument("--fail-on-flags", action="store_true")
    args = ap.parse_args()

    spec = load_spec(Path(args.spec))
    n = int(args.n if args.n is not None else spec.get("default_n", 200))
    dt = float(args.dt if args.dt is not None else spec.get("dt_s", 20.0))
    seed = int(args.seed if args.seed is not None else spec.get("seed", 5031))
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    bounds = spec.get("plausibility_bounds", {}) or {}
    selected = set(args.scenarios or spec.get("scenarios", {}).keys())

    all_rows: List[pd.DataFrame] = []
    all_draws: List[pd.DataFrame] = []
    summaries: List[Dict[str, Any]] = []
    for idx, (scenario, cfg) in enumerate(spec.get("scenarios", {}).items()):
        if scenario not in selected:
            continue
        rows, draws, summary = run_one_scenario(
            scenario=scenario,
            n=n,
            dt=dt,
            seed=seed + idx * 100000,
            bounds=bounds,
            max_runtime_s=cfg.get("max_runtime_s"),
        )
        all_rows.append(rows)
        all_draws.append(draws)
        summaries.append(summary)

    results = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame()
    draws = pd.concat(all_draws, ignore_index=True) if all_draws else pd.DataFrame()
    results.to_csv(outdir / "monte_carlo_results_v50B.csv", index=False)
    draws.to_csv(outdir / "monte_carlo_draws_v50B.csv", index=False)
    write_json({"release_step": "5.0B", "summaries": summaries}, outdir / "monte_carlo_summary_by_scenario_v50B.json")
    total = int(len(results))
    flagged = int((results.get("plausibility_flags", pd.Series(dtype=str)).fillna("") != "").sum()) if total else 0
    summary = {
        "release_step": "5.0B",
        "scenarios": len(summaries),
        "runs_per_scenario": n,
        "total_runs": total,
        "flagged_runs": flagged,
        "stable_runs": total - flagged,
        "dt_s": dt,
        "seed": seed,
    }
    write_json(summary, outdir / "monte_carlo_summary_v50B.json")
    write_markdown(outdir / "monte_carlo_report_v50B.md", summaries, spec)
    print(json.dumps(summary, indent=2))
    if args.fail_on_flags and flagged:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
