#!/usr/bin/env python3
"""Full configurable Sobol runner for public alpha v1.21.

This script wraps the lightweight v1.07 Saltelli/Jansen implementation and adds:

- named run presets (smoke, exploratory, report, paper);
- dry-run planning with evaluation counts before expensive execution;
- guardrails for large runs;
- v1.21 output filenames and manifest/report metadata;
- a public, non-clinical validation disclaimer.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from sobol_sensitivity_v1_07 import sobol_for_scenario  # noqa: E402

DEFAULT_SPEC = ROOT / "data" / "sobol_full_specs_v1.21.yaml"
DEFAULT_OUTDIR = ROOT / "outputs" / "sobol_full_v1.21"


def _write_json(obj: Dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True))


def _load_spec(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text())


def _resolve_preset(spec: Dict[str, Any], preset_name: str | None) -> Dict[str, Any]:
    presets = spec.get("presets", {})
    default_name = spec.get("defaults", {}).get("preset", "smoke")
    name = preset_name or default_name
    if name not in presets:
        raise KeyError(f"Unknown preset '{name}'. Available: {', '.join(sorted(presets))}")
    out = dict(presets[name])
    out["name"] = name
    return out


def _resolve_scenarios(spec: Dict[str, Any], requested: Iterable[str] | None) -> List[str]:
    available = spec.get("scenarios", {})
    defaults = spec.get("defaults", {}).get("default_scenarios", list(available.keys()))
    scenarios = list(requested) if requested else list(defaults)
    missing = [s for s in scenarios if s not in available]
    if missing:
        raise KeyError(f"Unknown Sobol scenario key(s): {missing}. Available: {', '.join(sorted(available))}")
    return scenarios


def build_plan(spec: Dict[str, Any], scenarios: List[str], preset: Dict[str, Any], base_samples: int | None, dt: float | None, seed: int | None) -> Dict[str, Any]:
    n = int(base_samples or preset.get("base_samples", 2))
    dt_s = float(dt if dt is not None else preset.get("dt_s", 10.0))
    random_seed = int(seed if seed is not None else spec.get("defaults", {}).get("random_seed", 121))
    outcomes = list(spec.get("defaults", {}).get("outcomes", []))
    rows: List[Dict[str, Any]] = []
    total_evaluations = 0
    total_indices = 0
    for key in scenarios:
        params = spec["scenarios"][key]["parameters"]
        d = len(params)
        evals = int(n * (d + 2))
        indices = int(d * len(outcomes))
        total_evaluations += evals
        total_indices += indices
        rows.append({
            "scenario": key,
            "scenario_file": f"{spec['scenarios'][key].get('scenario', key)}.yaml",
            "focus": spec["scenarios"][key].get("focus", ""),
            "n_parameters": int(d),
            "base_samples": int(n),
            "expected_evaluations": evals,
            "expected_indices": indices,
            "recommended_preset": spec["scenarios"][key].get("recommended_preset", ""),
        })
    return {
        "release": "v1.21-alpha",
        "method": "saltelli_jansen_monte_carlo",
        "preset": preset.get("name", "custom"),
        "preset_description": preset.get("description", ""),
        "base_samples": int(n),
        "dt_s": float(dt_s),
        "random_seed": int(random_seed),
        "outcomes": outcomes,
        "scenario_rows": rows,
        "scenario_count": len(rows),
        "total_expected_evaluations": int(total_evaluations),
        "total_expected_indices": int(total_indices),
        "max_evaluations_guard": int(preset.get("max_evaluations", 1000)),
        "nonclinical_disclaimer": "Exploratory model-development uncertainty analysis only; not clinical validation and not for patient care.",
    }


def _plan_dataframe(plan: Dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(plan["scenario_rows"])


def build_report(indices: pd.DataFrame, plan: Dict[str, Any], metas: List[Dict[str, Any]], errors: List[Dict[str, str]], dry_run: bool) -> str:
    lines: List[str] = [
        "# v1.21 Sobol full-run report",
        "",
        "This is a configurable Sobol/Saltelli-Jansen sensitivity analysis runner for model development.",
        "It is not clinical validation, not a medical device assessment and not suitable for patient-care decisions.",
        "",
        "## Run plan",
        "",
        f"- Preset: `{plan['preset']}`",
        f"- Base samples N: {plan['base_samples']}",
        f"- dt: {plan['dt_s']} s",
        f"- Scenarios: {plan['scenario_count']}",
        f"- Expected evaluations: {plan['total_expected_evaluations']}",
        f"- Expected indices: {plan['total_expected_indices']}",
        f"- Dry run: {dry_run}",
        "",
    ]
    lines.append("## Scenario evaluation plan")
    lines.append("")
    for row in plan["scenario_rows"]:
        lines.append(f"- **{row['scenario']}**: D={row['n_parameters']}, evaluations={row['expected_evaluations']}, focus={row.get('focus', '')}")
    lines.append("")
    if dry_run:
        lines.append("No simulations were executed because `--dry-run` was used.")
        return "\n".join(lines) + "\n"
    lines.append("## Completed scenarios")
    lines.append("")
    for m in metas:
        lines.append(f"- **{m['scenario']}**: {m['n_evaluations']} evaluations, runtime={m['runtime_s']:.1f} s.")
    if errors:
        lines.append("")
        lines.append("## Errors")
        lines.append("")
        for e in errors:
            lines.append(f"- **{e['scenario']}**: {e['error']}")
    if indices.empty:
        lines.append("")
        lines.append("No indices generated.")
        return "\n".join(lines) + "\n"
    lines.append("")
    lines.append("## Top total-order drivers")
    lines.append("")
    for scenario in indices["scenario"].unique():
        sub_s = indices[indices["scenario"] == scenario]
        lines.append(f"### {scenario}")
        for outcome in sub_s["outcome"].unique():
            sub_o = sub_s[sub_s["outcome"] == outcome].sort_values(["rank_ST", "parameter"])
            finite = sub_o[sub_o["ST"].apply(lambda x: isinstance(x, (int, float)) and math.isfinite(float(x)))]
            if finite.empty or float(finite["ST"].max()) <= 0.0:
                continue
            top = finite.head(3)
            lines.append(f"- **{outcome}**")
            for _, row in top.iterrows():
                lines.append(f"  - {row['parameter_label']} (`{row['parameter']}`): ST={row['ST']:.3f}, S1={row['S1']:.3f}")
        lines.append("")
    return "\n".join(lines) + "\n"


def run_full(spec: Dict[str, Any], scenarios: List[str], plan: Dict[str, Any], outdir: Path, fail_on_error: bool) -> Dict[str, Any]:
    all_indices: List[pd.DataFrame] = []
    all_evaluations: List[pd.DataFrame] = []
    metas: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []
    t0 = time.time()
    for i, scenario_key in enumerate(scenarios):
        try:
            idx, ev, meta = sobol_for_scenario(
                spec,
                scenario_key,
                base_samples=int(plan["base_samples"]),
                dt=float(plan["dt_s"]),
                seed=int(plan["random_seed"]) + i * 1000,
                outcomes=list(plan["outcomes"]),
            )
            all_indices.append(idx)
            all_evaluations.append(ev)
            metas.append(meta)
            print(f"{scenario_key}: {meta['n_evaluations']} evaluations, {meta['n_indices']} indices")
        except Exception as exc:  # pragma: no cover - exercised by CLI guards
            errors.append({"scenario": scenario_key, "error": str(exc)})
            print(f"ERROR {scenario_key}: {exc}", file=sys.stderr)
            if fail_on_error:
                raise
    indices_df = pd.concat(all_indices, ignore_index=True) if all_indices else pd.DataFrame()
    evals_df = pd.concat(all_evaluations, ignore_index=True) if all_evaluations else pd.DataFrame()
    indices_df.to_csv(outdir / "sobol_full_indices_v121.csv", index=False)
    evals_df.to_csv(outdir / "sobol_full_evaluations_v121.csv", index=False)
    return {
        "metas": metas,
        "errors": errors,
        "indices_df": indices_df,
        "evaluations_df": evals_df,
        "runtime_s": float(time.time() - t0),
    }


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="v1.21 configurable Sobol full runner")
    parser.add_argument("--spec", default=str(DEFAULT_SPEC))
    parser.add_argument("--preset", choices=["smoke", "exploratory", "report", "paper"], help="named run preset")
    parser.add_argument("--scenarios", nargs="*", help="scenario keys from the v1.21 spec; defaults to the spec default core set")
    parser.add_argument("--base-samples", type=int, help="override N; total evaluations = N*(D+2) per scenario")
    parser.add_argument("--dt", type=float, help="override simulation time step")
    parser.add_argument("--seed", type=int, help="override random seed")
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR))
    parser.add_argument("--dry-run", action="store_true", help="write plan/manifest only; do not execute simulations")
    parser.add_argument("--allow-large-run", action="store_true", help="bypass preset max_evaluations guard")
    parser.add_argument("--fail-on-error", action="store_true")
    args = parser.parse_args(argv)

    spec_path = Path(args.spec)
    spec = _load_spec(spec_path)
    preset = _resolve_preset(spec, args.preset)
    scenarios = _resolve_scenarios(spec, args.scenarios)
    plan = build_plan(spec, scenarios, preset, args.base_samples, args.dt, args.seed)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    _plan_dataframe(plan).to_csv(outdir / "sobol_full_plan_v121.csv", index=False)

    if plan["total_expected_evaluations"] > plan["max_evaluations_guard"] and not args.allow_large_run:
        plan["status"] = "REVIEW"
        plan["guard_triggered"] = True
        plan["guard_message"] = "Run exceeds preset max_evaluations. Re-run with --allow-large-run if intentional."
        _write_json(plan, outdir / "sobol_full_summary_v121.json")
        (outdir / "sobol_full_report_v121.md").write_text(build_report(pd.DataFrame(), plan, [], [{"scenario": "run_guard", "error": plan["guard_message"]}], dry_run=True))
        print(json.dumps({"status": "REVIEW", "expected_evaluations": plan["total_expected_evaluations"], "guard": plan["max_evaluations_guard"]}, indent=2))
        return 1 if args.fail_on_error else 0

    if args.dry_run:
        plan["status"] = "PASS"
        plan["dry_run"] = True
        _write_json(plan, outdir / "sobol_full_summary_v121.json")
        (outdir / "sobol_full_report_v121.md").write_text(build_report(pd.DataFrame(), plan, [], [], dry_run=True))
        print(json.dumps({"status": "PASS", "dry_run": True, "expected_evaluations": plan["total_expected_evaluations"]}, indent=2))
        return 0

    result = run_full(spec, scenarios, plan, outdir, fail_on_error=args.fail_on_error)
    summary = dict(plan)
    summary.update({
        "dry_run": False,
        "guard_triggered": False,
        "scenarios_completed": [m["scenario"] for m in result["metas"]],
        "errors": result["errors"],
        "total_actual_evaluations": int(sum(m["n_evaluations"] for m in result["metas"])),
        "total_actual_indices": int(sum(m["n_indices"] for m in result["metas"])),
        "runtime_s": float(result["runtime_s"]),
        "status": "PASS" if not result["errors"] else "REVIEW",
    })
    _write_json(summary, outdir / "sobol_full_summary_v121.json")
    (outdir / "sobol_full_report_v121.md").write_text(build_report(result["indices_df"], plan, result["metas"], result["errors"], dry_run=False))
    print(json.dumps({k: summary[k] for k in ["status", "total_actual_evaluations", "total_actual_indices", "runtime_s"]}, indent=2))
    return 1 if result["errors"] and args.fail_on_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
