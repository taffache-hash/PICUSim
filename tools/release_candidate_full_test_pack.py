#!/usr/bin/env python3
"""
v0.49 release-candidate full test pack.

Runs a pragmatic pre-release battery: static checks, selected functional reports,
and smoke simulation of core scenarios. This is an engineering/reproducibility
pack, not clinical validation.
"""
from __future__ import annotations

import argparse
import compileall
import csv
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.simtools import run_scenario, summarize_dataframe  # noqa: E402

OUT = ROOT / "outputs" / "validation_pack"
DEFAULT_MANIFEST = ROOT / "data" / "release_candidate_full_test_manifest_v0.49.yaml"


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def run_command(label: str, cmd: List[str], timeout: int = 120, hard: bool = False) -> Dict[str, Any]:
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        status = "PASS" if proc.returncode == 0 else ("FAIL" if hard else "REVIEW")
        return {
            "kind": "command",
            "label": label,
            "status": status,
            "returncode": proc.returncode,
            "elapsed_s": round(time.time() - t0, 2),
            "command": " ".join(cmd),
            "stdout_tail": proc.stdout[-1200:],
            "stderr_tail": proc.stderr[-1200:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "kind": "command",
            "label": label,
            "status": "FAIL" if hard else "REVIEW",
            "returncode": 124,
            "elapsed_s": round(time.time() - t0, 2),
            "command": " ".join(cmd),
            "stdout_tail": (exc.stdout or "")[-1200:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": "timeout",
        }


def compile_check() -> Dict[str, Any]:
    t0 = time.time()
    ok = compileall.compile_dir(str(ROOT), quiet=1, force=False)
    return {
        "kind": "static",
        "label": "compileall",
        "status": "PASS" if ok else "FAIL",
        "elapsed_s": round(time.time() - t0, 2),
        "detail": "python files compile" if ok else "compile failure",
    }


def smoke_scenarios(scenarios: List[str], dt: float) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for name in scenarios:
        t0 = time.time()
        try:
            cfg, df = run_scenario(name, dt=dt, quiet=True)
            summary = summarize_dataframe(df)
            rows.append({
                "kind": "scenario_smoke",
                "scenario": name,
                "status": "PASS",
                "elapsed_s": round(time.time() - t0, 2),
                "n_rows": int(len(df)),
                "simulation_time_s": float(cfg.get("simulation_time_s", 0.0)),
                "dt_s": float(dt),
                **summary,
            })
        except Exception as exc:
            rows.append({
                "kind": "scenario_smoke",
                "scenario": name,
                "status": "FAIL",
                "elapsed_s": round(time.time() - t0, 2),
                "error": repr(exc),
                "dt_s": float(dt),
            })
    return rows


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: List[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    ap.add_argument("--dt", type=float, default=None)
    ap.add_argument("--outdir", default=str(OUT))
    ap.add_argument("--fail-on-error", action="store_true")
    ap.add_argument("--skip-functional", action="store_true", help="Skip slower auxiliary functional reports.")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    manifest = load_yaml(Path(args.manifest))
    dt = float(args.dt if args.dt is not None else manifest.get("recommended_dt_s", 2.0))

    command_rows: List[Dict[str, Any]] = []
    command_rows.append(compile_check())
    command_rows.append(run_command("release_candidate_check", [sys.executable, "tools/release_candidate_check.py", "--fail-on-error"], hard=True))
    command_rows.append(run_command("dependency_deep_audit", [sys.executable, "tools/dependency_deep_audit.py", "--fail-on-error"], hard=True))
    command_rows.append(run_command("score_registry_audit", [sys.executable, "tools/audit_score_registry.py", "--fail-on-error"], hard=True))
    command_rows.append(run_command("profile_usage_audit", [sys.executable, "tools/profile_usage_audit.py"], hard=False))
    command_rows.append(run_command("literature_source_matrix", [sys.executable, "tools/literature_source_matrix.py"], hard=False))

    if not args.skip_functional:
        command_rows.append(run_command(
            "literature_benchmark_report_core",
            [sys.executable, "tools/literature_benchmark_report.py", "--dt", str(dt), "--scenarios", "healthy_child_20kg", "ards_mild", "septic_shock", "status_asthmaticus", "near_fatal_status_asthmaticus", "tbi_icp", "hematology_anemia_transfusion"],
            timeout=180,
            hard=False,
        ))
        command_rows.append(run_command("counterfactual_report", [sys.executable, "tools/counterfactual_report.py", "--dt", str(dt), "--fail-on-error"], timeout=180, hard=False))
        command_rows.append(run_command("event_demo_report", [sys.executable, "tools/event_demo_report.py", "--dt", str(dt), "--fail-on-error"], timeout=180, hard=False))
        command_rows.append(run_command(
            "output_profile_export",
            [sys.executable, "tools/export_output_profile.py", "--profiles", "instructor_minimal", "clinical_educational", "validation_core", "--scenarios", "healthy_child_20kg", "septic_shock", "status_asthmaticus", "--dt", str(dt)],
            timeout=180,
            hard=False,
        ))

    scenario_rows = smoke_scenarios(manifest.get("scenario_smoke_core", []), dt=dt)

    all_statuses = [r.get("status") for r in command_rows] + [r.get("status") for r in scenario_rows]
    fail_count = sum(1 for s in all_statuses if s == "FAIL")
    review_count = sum(1 for s in all_statuses if s == "REVIEW")
    pass_count = sum(1 for s in all_statuses if s == "PASS")
    final_status = "FAIL" if fail_count else ("REVIEW" if review_count else "PASS")

    summary = {
        "version": "v0.49",
        "status": final_status,
        "dt_s": dt,
        "commands": len(command_rows),
        "scenarios_smoked": len(scenario_rows),
        "pass": pass_count,
        "review": review_count,
        "fail": fail_count,
        "not_clinical_validation": True,
    }

    write_csv(outdir / "release_candidate_full_test_pack_v049_commands.csv", command_rows)
    write_csv(outdir / "release_candidate_full_test_pack_v049_scenarios.csv", scenario_rows)
    (outdir / "release_candidate_full_test_pack_v049_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# v0.49 Release Candidate Full Test Pack",
        "",
        "This is an engineering/reproducibility test pack, not clinical validation.",
        "",
        f"Overall status: **{final_status}**",
        "",
        f"- dt: {dt} s",
        f"- command checks: {len(command_rows)}",
        f"- scenario smoke runs: {len(scenario_rows)}",
        f"- PASS: {pass_count}",
        f"- REVIEW: {review_count}",
        f"- FAIL: {fail_count}",
        "",
        "## Command checks",
        "",
        "| check | status | elapsed_s | returncode/detail |",
        "|---|---:|---:|---|",
    ]
    for r in command_rows:
        detail = r.get("returncode", r.get("detail", ""))
        lines.append(f"| {r.get('label')} | {r.get('status')} | {r.get('elapsed_s', '')} | {detail} |")
    lines += ["", "## Scenario smoke runs", "", "| scenario | status | rows | elapsed_s | key final values |", "|---|---:|---:|---:|---|"]
    for r in scenario_rows:
        keyvals = []
        for k in ["SaO2_final", "PaCO2_final", "pH_a_final", "MAP_final", "lactate_final", "Hb_final"]:
            if k in r:
                try:
                    keyvals.append(f"{k}={float(r[k]):.3g}")
                except Exception:
                    keyvals.append(f"{k}={r[k]}")
        lines.append(f"| {r.get('scenario')} | {r.get('status')} | {r.get('n_rows', '')} | {r.get('elapsed_s', '')} | {'; '.join(keyvals)} |")
    lines += [
        "",
        "## Residual limitations before v1.0-alpha",
        "",
    ]
    for item in manifest.get("residual_issues_before_v1_alpha", []):
        lines.append(f"- {item}")
    (outdir / "release_candidate_full_test_pack_v049_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 1 if (args.fail_on_error and fail_count) else 0


if __name__ == "__main__":
    raise SystemExit(main())
