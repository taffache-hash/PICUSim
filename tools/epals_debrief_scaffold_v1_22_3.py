#!/usr/bin/env python3
"""Generate EPALS reversible-cause debrief reports (v1.22.3).

This tool converts EPALS scenario metadata and optional simulation time-series into
instructor-facing debrief artifacts. It is educational scaffolding only: it does
not grade clinicians and it is not a clinical decision-support tool.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]

PACK_FILES = [
    ROOT / "data" / "epals_5h_scenario_pack_v1.22.1.yaml",
    ROOT / "data" / "epals_5t_scenario_pack_v1.22.2.yaml",
]
TAXONOMY_FILE = ROOT / "data" / "epals_reversible_causes_v1.22.yaml"

METRIC_PLAN: dict[str, list[dict[str, Any]]] = {
    "epals_hypoxia_airway_obstruction": [
        {"var": "SaO2", "role": "oxygenation", "direction": "nadir", "thresholds": [0.90, 0.80]},
        {"var": "PaCO2", "role": "ventilation", "direction": "peak"},
        {"var": "R_rs", "role": "airway resistance", "direction": "peak"},
    ],
    "epals_hypovolemia_hemorrhagic_shock": [
        {"var": "MAP", "role": "perfusion pressure", "direction": "nadir", "thresholds": [55.0, 45.0]},
        {"var": "lactate", "role": "oxygen debt", "direction": "peak"},
        {"var": "Hb", "role": "oxygen carrying capacity", "direction": "nadir"},
    ],
    "epals_acidosis_septic_shock": [
        {"var": "pH_a", "role": "acidaemia", "direction": "nadir", "thresholds": [7.25, 7.10]},
        {"var": "lactate", "role": "shock metabolism", "direction": "peak"},
        {"var": "MAP", "role": "perfusion pressure", "direction": "nadir"},
    ],
    "epals_hyperkalemia_aki": [
        {"var": "K_mmol_L", "role": "potassium toxicity", "direction": "peak", "thresholds": [6.0, 7.0]},
        {"var": "RRT_indication_score", "role": "renal replacement trigger", "direction": "peak"},
        {"var": "pH_a", "role": "acidaemia modifier", "direction": "nadir"},
    ],
    "epals_hypothermia_rewarming": [
        {"var": "T_core", "role": "core temperature", "direction": "nadir", "thresholds": [35.0, 32.0]},
        {"var": "hypothermia_index", "role": "temperature severity", "direction": "peak"},
        {"var": "HR", "role": "temperature-related heart-rate effect", "direction": "nadir"},
    ],
    "epals_tension_pneumothorax": [
        {"var": "MAP", "role": "obstructive shock", "direction": "nadir", "thresholds": [55.0, 45.0]},
        {"var": "RV_afterload_index", "role": "right-heart load", "direction": "peak"},
        {"var": "Ppeak", "role": "airway pressure", "direction": "peak"},
    ],
    "epals_cardiac_tamponade": [
        {"var": "CVP", "role": "venous congestion", "direction": "peak"},
        {"var": "MAP", "role": "perfusion pressure", "direction": "nadir", "thresholds": [55.0, 45.0]},
        {"var": "CO", "role": "cardiac output", "direction": "nadir"},
    ],
    "epals_toxicologic_opioid_benzodiazepine": [
        {"var": "PaCO2", "role": "hypoventilation", "direction": "peak", "thresholds": [55.0, 70.0]},
        {"var": "sedation_score", "role": "sedative burden", "direction": "peak"},
        {"var": "drive_level", "role": "respiratory drive", "direction": "nadir"},
    ],
    "epals_pulmonary_thrombosis_pe": [
        {"var": "PVR", "role": "pulmonary vascular load", "direction": "peak"},
        {"var": "RV_afterload_index", "role": "RV afterload", "direction": "peak"},
        {"var": "SaO2", "role": "oxygenation", "direction": "nadir", "thresholds": [0.90, 0.80]},
    ],
    "epals_cardiac_thrombosis_myocarditis_low_output": [
        {"var": "CO", "role": "pump failure", "direction": "nadir"},
        {"var": "MAP", "role": "perfusion pressure", "direction": "nadir", "thresholds": [55.0, 45.0]},
        {"var": "drug_inotropy_mod", "role": "inotrope response proxy", "direction": "peak"},
    ],
}

CORE_COLUMNS = ["SaO2", "PaO2", "PaCO2", "pH_a", "MAP", "HR", "CO", "lactate"]


@dataclass
class ScenarioMeta:
    scenario_id: str
    path: Path
    group: str
    cause: str
    reversible_cause: str
    narrative: str
    expected_response: list[str]
    debrief_questions: list[str]
    interventions: list[str]


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text()) or {}


def _collect_scenarios() -> list[ScenarioMeta]:
    rows: list[ScenarioMeta] = []
    seen: set[str] = set()
    for pack_path in PACK_FILES:
        pack = _load_yaml(pack_path)
        for item in pack.get("scenarios", []):
            sid = item["id"]
            if sid in seen:
                continue
            seen.add(sid)
            scenario_path = ROOT / item["file"]
            data = _load_yaml(scenario_path)
            epals = data.get("epals", {}) or {}
            perturbations = data.get("perturbations", []) or []
            interventions = []
            for p in perturbations:
                label = p.get("label") or p.get("action") or "intervention"
                interventions.append(f"t={p.get('t', '?')}s: {label}")
            rows.append(
                ScenarioMeta(
                    scenario_id=sid,
                    path=scenario_path,
                    group=str(epals.get("group", item.get("group", ""))),
                    cause=str(epals.get("cause", item.get("H_cause", item.get("T_cause", "")))),
                    reversible_cause=str(epals.get("reversible_cause", epals.get("cause", ""))),
                    narrative=str(data.get("clinical_narrative", "")),
                    expected_response=[str(x) for x in (data.get("expected_response", []) or [])],
                    debrief_questions=[str(x) for x in (data.get("debrief_questions", []) or [])],
                    interventions=interventions,
                )
            )
    return rows


def _run_scenario(meta: ScenarioMeta, outdir: Path, dt: float) -> tuple[int, Path, str]:
    ts_dir = outdir / "timeseries"
    ts_dir.mkdir(parents=True, exist_ok=True)
    csv_path = ts_dir / f"{meta.scenario_id}_timeseries.csv"
    cmd = [
        sys.executable,
        str(ROOT / "run_simulation.py"),
        "--scenario",
        str(meta.path),
        "--dt",
        str(dt),
        "--no-plot",
        "--save-csv",
        str(csv_path),
    ]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
    return res.returncode, csv_path, (res.stderr + res.stdout)[-800:]


def _time_col(df: pd.DataFrame) -> pd.Series:
    if "t" in df.columns:
        return pd.to_numeric(df["t"], errors="coerce")
    return pd.Series(range(len(df)), dtype=float)


def _metric_row(sid: str, df: pd.DataFrame, spec: dict[str, Any]) -> dict[str, Any]:
    var = spec["var"]
    base = {"scenario": sid, "variable": var, "role": spec.get("role", ""), "direction": spec.get("direction", ""), "status": "PASS"}
    if var not in df.columns:
        base.update({"status": "REVIEW", "detail": "missing variable"})
        return base
    values = pd.to_numeric(df[var], errors="coerce")
    valid = values.dropna()
    if valid.empty:
        base.update({"status": "REVIEW", "detail": "no numeric data"})
        return base
    t = _time_col(df)
    idx_min = int(values.idxmin())
    idx_max = int(values.idxmax())
    first = float(valid.iloc[0])
    final = float(valid.iloc[-1])
    mn = float(values.min())
    mx = float(values.max())
    t_min = float(t.iloc[idx_min]) if idx_min < len(t) else None
    t_max = float(t.iloc[idx_max]) if idx_max < len(t) else None
    direction = spec.get("direction")
    if direction == "nadir":
        worst = mn
        t_worst = t_min
        recovery = final - mn
    elif direction == "peak":
        worst = mx
        t_worst = t_max
        recovery = mx - final
    else:
        worst = final
        t_worst = float(t.iloc[-1]) if len(t) else None
        recovery = final - first
    base.update(
        {
            "first": first,
            "min": mn,
            "t_min_s": t_min,
            "max": mx,
            "t_max_s": t_max,
            "final": final,
            "worst": worst,
            "t_worst_s": t_worst,
            "recovery_from_worst": recovery,
            "detail": f"{var}: first={first:.4g}, worst={worst:.4g}, final={final:.4g}",
        }
    )
    return base


def _threshold_rows(sid: str, df: pd.DataFrame, spec: dict[str, Any]) -> list[dict[str, Any]]:
    var = spec["var"]
    thresholds = spec.get("thresholds", []) or []
    if var not in df.columns or not thresholds:
        return []
    values = pd.to_numeric(df[var], errors="coerce")
    t = _time_col(df)
    rows = []
    direction = spec.get("direction")
    for th in thresholds:
        if direction == "nadir":
            mask = values < float(th)
            label = f"below_{th}"
        else:
            mask = values > float(th)
            label = f"above_{th}"
        if mask.any():
            times = t[mask]
            rows.append(
                {
                    "scenario": sid,
                    "variable": var,
                    "threshold": th,
                    "condition": label,
                    "crossed": True,
                    "first_crossing_s": float(times.iloc[0]),
                    "last_crossing_s": float(times.iloc[-1]),
                    "samples": int(mask.sum()),
                }
            )
        else:
            rows.append(
                {
                    "scenario": sid,
                    "variable": var,
                    "threshold": th,
                    "condition": label,
                    "crossed": False,
                    "first_crossing_s": None,
                    "last_crossing_s": None,
                    "samples": 0,
                }
            )
    return rows


def _scenario_markdown(meta: ScenarioMeta, metric_rows: list[dict[str, Any]], threshold_rows: list[dict[str, Any]], status: str, run_detail: str) -> str:
    lines = [
        f"# EPALS debrief — {meta.scenario_id}",
        "",
        f"**Group:** {meta.group}",
        f"**Reversible cause:** {meta.reversible_cause}",
        f"**Scenario file:** `{meta.path.relative_to(ROOT)}`",
        f"**Run status:** {status}",
        "",
        "## Clinical frame",
        "",
        meta.narrative or "No narrative recorded.",
        "",
        "## Key physiologic markers",
        "",
        "| Variable | Role | Direction | First | Worst | Final | Recovery from worst |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for r in metric_rows:
        def fmt(x: Any) -> str:
            return "" if x is None or pd.isna(x) else f"{float(x):.3g}"
        lines.append(f"| {r.get('variable','')} | {r.get('role','')} | {r.get('direction','')} | {fmt(r.get('first'))} | {fmt(r.get('worst'))} | {fmt(r.get('final'))} | {fmt(r.get('recovery_from_worst'))} |")
    if threshold_rows:
        lines += ["", "## Threshold events", "", "| Variable | Threshold | Condition | Crossed | First crossing (s) | Samples |", "|---|---:|---|---:|---:|---:|"]
        for r in threshold_rows:
            first = "" if r.get("first_crossing_s") is None else f"{float(r['first_crossing_s']):.0f}"
            lines.append(f"| {r['variable']} | {r['threshold']} | {r['condition']} | {r['crossed']} | {first} | {r['samples']} |")
    lines += ["", "## Intervention proxies", ""]
    lines += [f"- {x}" for x in (meta.interventions or ["No perturbation/intervention metadata recorded."])]
    lines += ["", "## Expected physiologic response", ""]
    lines += [f"- {x}" for x in (meta.expected_response or ["No expected-response metadata recorded."])]
    lines += ["", "## Debrief questions", ""]
    lines += [f"- {x}" for x in (meta.debrief_questions or ["No debrief questions recorded."])]
    lines += ["", "## Safety note", "", "This report is for education and model review only. It is not a clinical protocol and must not be used for patient care."]
    if status != "PASS":
        lines += ["", "## Run detail", "", "```", run_detail[-800:], "```"]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="outputs/epals_debrief_v1.22.3")
    ap.add_argument("--dt", type=float, default=10.0)
    ap.add_argument("--scenarios", nargs="*", help="Optional scenario ids to run.")
    ap.add_argument("--no-run", action="store_true", help="Generate metadata-only debrief scaffold without simulation.")
    ap.add_argument("--fail-on-review", action="store_true")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    if not outdir.is_absolute():
        outdir = ROOT / outdir
    outdir.mkdir(parents=True, exist_ok=True)
    report_dir = outdir / "scenario_reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    scenarios = _collect_scenarios()
    if args.scenarios:
        wanted = set(args.scenarios)
        scenarios = [s for s in scenarios if s.scenario_id in wanted]

    scenario_rows = []
    metric_rows_all: list[dict[str, Any]] = []
    threshold_rows_all: list[dict[str, Any]] = []
    question_rows = []

    for meta in scenarios:
        run_status = "SKIPPED" if args.no_run else "PASS"
        run_detail = "metadata-only mode"
        metric_rows: list[dict[str, Any]] = []
        threshold_rows: list[dict[str, Any]] = []
        if not args.no_run:
            rc, csv_path, detail = _run_scenario(meta, outdir, args.dt)
            run_detail = detail
            if rc != 0 or not csv_path.exists():
                run_status = "FAIL"
            else:
                try:
                    df = pd.read_csv(csv_path)
                    if "Unnamed: 0" in df.columns and "t" not in df.columns:
                        df = df.rename(columns={"Unnamed: 0": "t"})
                    for spec in METRIC_PLAN.get(meta.scenario_id, []):
                        row = _metric_row(meta.scenario_id, df, spec)
                        metric_rows.append(row)
                        threshold_rows.extend(_threshold_rows(meta.scenario_id, df, spec))
                    missing_core = [c for c in CORE_COLUMNS if c not in df.columns]
                    if missing_core:
                        run_status = "REVIEW"
                        run_detail += "\nMissing core columns: " + ", ".join(missing_core)
                    elif any(r.get("status") == "REVIEW" for r in metric_rows):
                        run_status = "REVIEW"
                except Exception as e:  # pragma: no cover - defensive reporting
                    run_status = "FAIL"
                    run_detail = str(e)
        else:
            for spec in METRIC_PLAN.get(meta.scenario_id, []):
                metric_rows.append({"scenario": meta.scenario_id, "variable": spec["var"], "role": spec.get("role", ""), "direction": spec.get("direction", ""), "status": "SKIPPED", "detail": "metadata-only mode"})

        metric_rows_all.extend(metric_rows)
        threshold_rows_all.extend(threshold_rows)
        for i, q in enumerate(meta.debrief_questions, start=1):
            question_rows.append({"scenario": meta.scenario_id, "question_number": i, "question": q})
        scenario_rows.append(
            {
                "scenario": meta.scenario_id,
                "group": meta.group,
                "cause": meta.cause,
                "reversible_cause": meta.reversible_cause,
                "file": str(meta.path.relative_to(ROOT)),
                "run_status": run_status,
                "metric_count": len(metric_rows),
                "threshold_event_count": len([r for r in threshold_rows if r.get("crossed")]),
                "intervention_count": len(meta.interventions),
                "debrief_question_count": len(meta.debrief_questions),
            }
        )
        (report_dir / f"{meta.scenario_id}_debrief.md").write_text(_scenario_markdown(meta, metric_rows, threshold_rows, run_status, run_detail))

    pd.DataFrame(scenario_rows).to_csv(outdir / "epals_debrief_scenario_summary_v1223.csv", index=False)
    pd.DataFrame(metric_rows_all).to_csv(outdir / "epals_debrief_metric_markers_v1223.csv", index=False)
    pd.DataFrame(threshold_rows_all).to_csv(outdir / "epals_debrief_threshold_events_v1223.csv", index=False)
    pd.DataFrame(question_rows).to_csv(outdir / "epals_debrief_questions_v1223.csv", index=False)

    fail = sum(r["run_status"] == "FAIL" for r in scenario_rows)
    review = sum(r["run_status"] == "REVIEW" for r in scenario_rows)
    summary = {
        "release": "v1.22.3-alpha",
        "scenario_count": len(scenario_rows),
        "metric_rows": len(metric_rows_all),
        "threshold_rows": len(threshold_rows_all),
        "question_rows": len(question_rows),
        "fail": fail,
        "review": review,
        "status": "FAIL" if fail else ("REVIEW" if review else "PASS"),
        "mode": "metadata_only" if args.no_run else "simulation",
    }
    (outdir / "epals_debrief_summary_v1223.json").write_text(json.dumps(summary, indent=2))
    index_lines = [
        "# EPALS debrief index v1.22.3",
        "",
        f"Status: **{summary['status']}**",
        f"Mode: `{summary['mode']}`",
        f"Scenarios: {summary['scenario_count']}",
        f"Metric rows: {summary['metric_rows']}",
        f"Threshold rows: {summary['threshold_rows']}",
        f"Debrief questions: {summary['question_rows']}",
        "",
        "| Scenario | Group | Cause | Run status | Report |",
        "|---|---|---|---|---|",
    ]
    for row in scenario_rows:
        rep = f"scenario_reports/{row['scenario']}_debrief.md"
        index_lines.append(f"| {row['scenario']} | {row['group']} | {row['reversible_cause']} | {row['run_status']} | `{rep}` |")
    (outdir / "epals_debrief_index_v1223.md").write_text("\n".join(index_lines) + "\n")
    print(json.dumps(summary, indent=2))
    if fail or (args.fail_on_review and review):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
