#!/usr/bin/env python3
"""Performance smoke audit for PDT Clinical Training Console v2.4."""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from api.server import app
from api.performance import json_size_bytes


def timed(fn):
    t0 = time.perf_counter()
    result = fn()
    return result, (time.perf_counter() - t0) * 1000.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="airway_rsi_hypoxic_child_v1_24")
    parser.add_argument("--dt", type=float, default=0.5)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--outdir", default="outputs/gui_performance_v2.4")
    parser.add_argument("--fail-on-review", action="store_true")
    args = parser.parse_args()

    outdir = ROOT / args.outdir
    outdir.mkdir(parents=True, exist_ok=True)
    client = TestClient(app)

    load_body = {
        "scenario": args.scenario,
        "dt": args.dt,
        "snapshot_interval_s": 1.0,
        "max_history_points": 600,
        "history_window_s": 900.0,
        "history_decimation_s": 1.0,
    }
    load_resp, load_ms = timed(lambda: client.post("/session/load", json=load_body))
    if load_resp.status_code != 200:
        raise RuntimeError(load_resp.text)
    sid = load_resp.json()["session_id"]

    step_ms = []
    bedside_ms = []
    waveform_ms = []
    payloads = []
    for _ in range(args.steps):
        _, ms = timed(lambda: client.post(f"/session/{sid}/step", json={"seconds": 1.0}))
        step_ms.append(ms)
        r, ms = timed(lambda: client.get(f"/session/{sid}/state?profile=bedside_fast"))
        bedside_ms.append(ms)
        payloads.append({"profile": "bedside_fast", "bytes": json_size_bytes(r.json())})
        r, ms = timed(lambda: client.get(f"/session/{sid}/state?profile=waveform_fast"))
        waveform_ms.append(ms)
        payloads.append({"profile": "waveform_fast", "bytes": json_size_bytes(r.json())})

    perf = client.get(f"/session/{sid}/performance").json()["performance"]
    hist = client.get(f"/session/{sid}/history?limit=100&profile=training").json()["history"]
    debrief = client.get(f"/session/{sid}/debrief").json()["debrief"]
    client.delete(f"/session/{sid}")

    max_payload = max(p["bytes"] for p in payloads)
    summary = {
        "release": "v2.4-alpha",
        "scenario": args.scenario,
        "steps": args.steps,
        "load_ms": round(load_ms, 2),
        "step_ms_mean": round(statistics.mean(step_ms), 2),
        "bedside_ms_mean": round(statistics.mean(bedside_ms), 2),
        "waveform_ms_mean": round(statistics.mean(waveform_ms), 2),
        "max_payload_bytes": max_payload,
        "history_points": len(hist),
        "performance": perf,
        "debrief_flags": len([f for f in debrief.get("flags", []) if f.get("triggered")]),
        "status": "PASS" if max_payload < 6000 and statistics.mean(bedside_ms) < 250 else "REVIEW",
    }
    (outdir / "performance_summary_v24.json").write_text(json.dumps(summary, indent=2))
    (outdir / "payload_samples_v24.json").write_text(json.dumps(payloads[:20], indent=2))
    report = [
        "# PDT GUI performance audit v2.4",
        "",
        f"Scenario: `{args.scenario}`",
        f"Load time: {summary['load_ms']} ms",
        f"Mean step call: {summary['step_ms_mean']} ms",
        f"Mean bedside state call: {summary['bedside_ms_mean']} ms",
        f"Mean waveform state call: {summary['waveform_ms_mean']} ms",
        f"Max payload: {summary['max_payload_bytes']} bytes",
        f"History points returned: {summary['history_points']}",
        f"Status: **{summary['status']}**",
    ]
    (outdir / "performance_report_v24.md").write_text("\n".join(report) + "\n")
    print(json.dumps(summary, indent=2))
    if args.fail_on_review and summary["status"] != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
