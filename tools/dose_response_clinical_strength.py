#!/usr/bin/env python3
"""PDT v0.37 clinical-strengthened dose-response matrix.

This tool addresses the v0.29 critique that monotonic checks could pass with
flat curves. A case passes only if:
  1. values move monotonically in the expected direction, and
  2. the total response exceeds an absolute or relative minimum effect size.

It is a qualitative sanity check, not pharmacological calibration.
"""
from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.simtools import load_yaml, scenario_path, run_config, set_nested, write_json  # noqa: E402

DEFAULT_SPECS = ROOT / "data" / "dose_response_specs_v0.37.yaml"


def _load_specs(path: Path = DEFAULT_SPECS) -> Dict[str, Dict[str, Any]]:
    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}
    cases = data.get("cases", {})
    if not isinstance(cases, dict) or not cases:
        raise ValueError(f"No cases found in {path}")
    return cases


def _metric_value(df: pd.DataFrame, metric: str, aggregate: str) -> float:
    if metric not in df.columns:
        raise KeyError(f"Metric '{metric}' not found in simulation output columns")
    series = pd.to_numeric(df[metric], errors="coerce").dropna()
    if series.empty:
        raise ValueError(f"Metric '{metric}' is empty/non-numeric")
    if aggregate == "final":
        return float(series.iloc[-1])
    if aggregate == "max":
        return float(series.max())
    if aggregate == "min":
        return float(series.min())
    if aggregate == "mean":
        return float(series.mean())
    raise ValueError(f"Unknown aggregate '{aggregate}' for metric '{metric}'")


def monotonic(values: List[float], direction: str, tol: float = 1e-9) -> bool:
    if len(values) < 2:
        return False
    pairs = zip(values, values[1:])
    if direction == "down":
        return all(b <= a + tol for a, b in pairs)
    if direction == "up":
        return all(b >= a - tol for a, b in pairs)
    raise ValueError(f"Unknown direction: {direction}")


def effect_size(values: List[float], direction: str) -> tuple[float, float]:
    """Return signed improvement and relative improvement vs baseline magnitude."""
    if len(values) < 2:
        return 0.0, 0.0
    if direction == "down":
        delta = values[0] - values[-1]
    else:
        delta = values[-1] - values[0]
    rel = delta / max(abs(values[0]), 1e-9)
    return float(delta), float(rel)


def is_nonflat(values: List[float], direction: str, min_abs: float, min_rel: float) -> tuple[bool, float, float]:
    delta, rel = effect_size(values, direction)
    return bool((delta >= min_abs) or (rel >= min_rel)), delta, rel


def _build_config(spec: Mapping[str, Any], dose: Any) -> Dict[str, Any]:
    cfg = load_yaml(scenario_path(spec["scenario"]))
    cfg = copy.deepcopy(cfg)
    if spec.get("clear_perturbations", True):
        cfg["perturbations"] = []
    if "simulation_time_s" in spec:
        cfg["simulation_time_s"] = float(spec["simulation_time_s"])

    for k, v in (spec.get("extra_set") or {}).items():
        set_nested(cfg, str(k), v)

    mode = str(spec.get("mode", "config"))
    if mode == "config":
        set_nested(cfg, str(spec["set_path"]), dose)
    elif mode == "action":
        action = str(spec["action"])
        cfg.setdefault("perturbations", []).append({"t": 1, "action": action, "value": dose, "label": "v0.32 systematic dose-response"})
    else:
        raise ValueError(f"Unknown case mode: {mode}")
    return cfg


def run_case(name: str, spec: Mapping[str, Any], default_dt: float | None = None) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    dt = float(default_dt if default_dt is not None else spec.get("dt", 5.0))
    metric = str(spec["metric"])
    aggregate = str(spec.get("aggregate", "final"))
    for dose in spec["doses"]:
        cfg = _build_config(spec, dose)
        try:
            df = run_config(cfg, dt=dt, quiet=True)
            value = _metric_value(df, metric, aggregate)
            status = "ok"
            error = ""
        except Exception as exc:
            value = float("nan")
            status = "error"
            error = f"{type(exc).__name__}: {exc}"
        rows.append({
            "case": name,
            "scenario": spec["scenario"],
            "mode": spec.get("mode", "config"),
            "dose": dose,
            "metric": metric,
            "aggregate": aggregate,
            "direction": spec["direction"],
            "value": value,
            "dt": dt,
            "simulation_time_s": float(spec.get("simulation_time_s", 0.0)),
            "row_status": status,
            "error": error,
        })
    return pd.DataFrame(rows)


def evaluate(results: pd.DataFrame, specs: Mapping[str, Mapping[str, Any]]) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    for name, spec in specs.items():
        sub = results[results["case"] == name].sort_values("dose")
        values = [float(v) for v in sub["value"].tolist()]
        errors = [e for e in sub["error"].tolist() if isinstance(e, str) and e]
        direction = str(spec["direction"])
        min_abs = float(spec.get("min_abs_delta", 0.0))
        min_rel = float(spec.get("min_rel_delta", 0.0))
        mono = False if errors else monotonic(values, direction)
        nonflat, delta, rel = (False, 0.0, 0.0) if errors else is_nonflat(values, direction, min_abs, min_rel)
        passed = bool(mono and nonflat)
        checks.append({
            "case": name,
            "scenario": spec["scenario"],
            "metric": spec["metric"],
            "aggregate": spec.get("aggregate", "final"),
            "direction": direction,
            "doses": list(spec["doses"]),
            "values": values,
            "monotonic": mono,
            "nonflat": nonflat,
            "delta": delta,
            "relative_delta": rel,
            "min_abs_delta": min_abs,
            "min_rel_delta": min_rel,
            "passed": passed,
            "status": "PASS" if passed else ("ERROR" if errors else "REVIEW"),
            "errors": errors,
            "interpretation": spec.get("interpretation", ""),
        })
    return checks


def write_markdown(checks: List[Dict[str, Any]], path: Path) -> None:
    passed = sum(1 for c in checks if c["passed"])
    lines = [
        "# PDT v0.37 Clinical-Strengthened Dose-Response Matrix",
        "",
        "A case passes only if it is monotonic in the expected direction and exceeds a clinically meaningful minimum effect size.",
        "This is a qualitative internal sanity check, not pharmacological validation.",
        "",
        f"Passed **{passed}/{len(checks)}** cases.",
        "",
        "| Case | Metric | Direction | Values | Δ | Rel Δ | Status |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for c in checks:
        vals = ", ".join(f"{v:.4g}" for v in c["values"])
        lines.append(
            f"| {c['case']} | {c['metric']} ({c['aggregate']}) | {c['direction']} | {vals} | "
            f"{c['delta']:.4g} | {c['relative_delta']:.3g} | {c['status']} |"
        )
    review = [c for c in checks if not c["passed"]]
    if review:
        lines += ["", "## Cases requiring review", ""]
        for c in review:
            reason = []
            if not c["monotonic"]:
                reason.append("non-monotonic")
            if not c["nonflat"]:
                reason.append("flat/too-small effect")
            if c.get("errors"):
                reason.append("errors: " + "; ".join(c["errors"]))
            lines.append(f"- **{c['case']}**: {', '.join(reason)}. {c.get('interpretation','')}")
    path.write_text("\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default=str(DEFAULT_SPECS))
    ap.add_argument("--cases", nargs="+", default=None)
    ap.add_argument("--dt", type=float, default=None, help="Override per-case dt")
    ap.add_argument("--outdir", default=str(ROOT / "outputs" / "validation_pack"))
    ap.add_argument("--fail-on-review", action="store_true", help="Exit nonzero if any case is REVIEW/ERROR")
    args = ap.parse_args()

    all_specs = _load_specs(Path(args.spec))
    selected = args.cases or list(all_specs.keys())
    specs = {k: all_specs[k] for k in selected}

    frames = [run_case(name, spec, default_dt=args.dt) for name, spec in specs.items()]
    results = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    checks = evaluate(results, specs)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    results.to_csv(outdir / "dose_response_systematic_results.csv", index=False)
    write_json({"checks": checks, "n_passed": sum(1 for c in checks if c["passed"]), "n_total": len(checks)}, outdir / "dose_response_systematic_summary.json")
    write_markdown(checks, outdir / "dose_response_systematic_report.md")
    print(f"systematic dose-response report written to {outdir}")
    print(f"passed {sum(1 for c in checks if c['passed'])}/{len(checks)} cases")
    if args.fail_on_review and not all(c["passed"] for c in checks):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
