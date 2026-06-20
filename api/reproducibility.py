"""Export and reproducibility helpers for PDT v5.1A.

This module deliberately keeps the export format plain-text and deterministic:
JSON for complete replay metadata, CSV for physiological timelines and actions,
Markdown for a PDF-like structured report, and SHA-256 hashes for scenario/session
state verification. It is educational/research alpha only; it is not a clinical
record format.
"""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .session_io import build_session_bundle, bundle_to_markdown, _json_safe, _safe_name

ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = ROOT / "outputs" / "reproducibility_pack_v5.1A"
PACK_SCHEMA = "pdt-reproducibility-pack-v5.1A"

TIMELINE_COLUMNS = [
    "time_s", "SpO2_percent", "SaO2", "HR", "MAP", "SBP", "DBP", "RR", "EtCO2", "PaCO2",
    "pH", "PaO2", "lactate", "urine_ml_kg_h", "renal_perfusion_index", "hepatic_perfusion_index",
    "airway_event_type", "airway_rescue_state", "shock_type", "failure_to_rescue_phase",
]
ACTION_COLUMNS = ["t", "action", "label", "payload_json", "result_json"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical_json(obj: Any) -> str:
    """Return a stable JSON representation suitable for hashing."""
    return json.dumps(_json_safe(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def scenario_file_hash(sess: Any) -> str:
    p = Path(sess.scenario_path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""


def build_timeline_rows(history: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for h in history:
        row: Dict[str, Any] = {}
        for col in TIMELINE_COLUMNS:
            val = h.get(col)
            if val is None and col == "time_s":
                val = h.get("t")
            if isinstance(val, float):
                val = round(val, 5)
            row[col] = val if val is not None else ""
        rows.append(row)
    return rows


def build_action_rows(event_log: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for ev in event_log:
        if not isinstance(ev, dict):
            continue
        if not ev.get("action") and not str(ev.get("label", "")).startswith("action:"):
            continue
        rows.append({
            "t": round(float(ev.get("t", 0.0) or 0.0), 5),
            "action": ev.get("action", ""),
            "label": ev.get("label", ""),
            "payload_json": canonical_json(ev.get("payload", {})),
            "result_json": canonical_json(ev.get("result", {})),
        })
    return rows


def rows_to_csv(rows: List[Dict[str, Any]], columns: List[str]) -> str:
    from io import StringIO
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def build_reproducibility_bundle(sess: Any, *, seed: int | None = None, history_limit: int = 20000) -> Dict[str, Any]:
    session_bundle = build_session_bundle(sess, history_limit=history_limit)
    timeline_rows = build_timeline_rows(session_bundle.get("history", []))
    action_rows = build_action_rows(session_bundle.get("event_log", []))
    manifest = {
        "schema": PACK_SCHEMA,
        "created_utc": _utc_now(),
        "engine_version": session_bundle.get("engine_version", "unknown"),
        "seed": int(seed) if seed is not None else None,
        "scenario": session_bundle.get("session", {}).get("scenario", ""),
        "scenario_path": session_bundle.get("session", {}).get("scenario_path", ""),
        "scenario_file_sha256": scenario_file_hash(sess),
        "session_state_sha256": sha256_obj(session_bundle.get("final_state", {})),
        "session_bundle_sha256": sha256_obj(session_bundle),
        "timeline_rows": len(timeline_rows),
        "action_rows": len(action_rows),
        "exports": {
            "session_json": "complete portable session bundle",
            "timeline_csv": "physiology timeline, bedside columns",
            "intervention_log_csv": "action/intervention replay log",
            "structured_report_md": "PDF-like markdown report",
            "manifest_json": "hashes and reproducibility metadata",
        },
        "safety_note": "Educational/research alpha only. Not for clinical use. Not a medical device.",
    }
    return _json_safe({
        "manifest": manifest,
        "session_bundle": session_bundle,
        "timeline_rows": timeline_rows,
        "action_rows": action_rows,
        "structured_report_md": build_structured_report(session_bundle, manifest),
    })


def build_structured_report(session_bundle: Dict[str, Any], manifest: Dict[str, Any]) -> str:
    base = bundle_to_markdown(session_bundle)
    lines = [
        f"# Reproducibility Pack — {manifest.get('scenario', 'unknown')}",
        "",
        "Educational/research alpha only. Not for clinical use. Not a medical device.",
        "",
        "## Reproducibility manifest",
        f"- Schema: `{manifest.get('schema')}`",
        f"- Engine version: `{manifest.get('engine_version')}`",
        f"- Seed: `{manifest.get('seed')}`",
        f"- Scenario SHA-256: `{manifest.get('scenario_file_sha256')}`",
        f"- Session state SHA-256: `{manifest.get('session_state_sha256')}`",
        f"- Session bundle SHA-256: `{manifest.get('session_bundle_sha256')}`",
        f"- Timeline rows: {manifest.get('timeline_rows')}",
        f"- Intervention/action rows: {manifest.get('action_rows')}",
        "",
        "## Session report",
        "",
        base,
    ]
    return "\n".join(lines)


def save_reproducibility_pack(sess: Any, *, basename: str | None = None, seed: int | None = None, history_limit: int = 20000, output_dir: Path | None = None) -> Dict[str, Any]:
    outdir = output_dir or EXPORT_DIR
    outdir.mkdir(parents=True, exist_ok=True)
    pack = build_reproducibility_bundle(sess, seed=seed, history_limit=history_limit)
    manifest = pack["manifest"]
    stem = _safe_name(basename or f"{manifest.get('scenario','session')}_{str(getattr(sess,'id',''))[:8]}_v51A")

    session_json = outdir / f"{stem}_session.json"
    timeline_csv = outdir / f"{stem}_timeline.csv"
    actions_csv = outdir / f"{stem}_interventions.csv"
    report_md = outdir / f"{stem}_report.md"
    manifest_json = outdir / f"{stem}_manifest.json"

    session_json.write_text(json.dumps(pack["session_bundle"], indent=2, ensure_ascii=False), encoding="utf-8")
    timeline_csv.write_text(rows_to_csv(pack["timeline_rows"], TIMELINE_COLUMNS), encoding="utf-8")
    actions_csv.write_text(rows_to_csv(pack["action_rows"], ACTION_COLUMNS), encoding="utf-8")
    report_md.write_text(pack["structured_report_md"], encoding="utf-8")
    manifest_json.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "status": "saved",
        "schema": PACK_SCHEMA,
        "manifest": manifest,
        "files": {
            "session_json": str(session_json.relative_to(ROOT)),
            "timeline_csv": str(timeline_csv.relative_to(ROOT)),
            "intervention_log_csv": str(actions_csv.relative_to(ROOT)),
            "structured_report_md": str(report_md.relative_to(ROOT)),
            "manifest_json": str(manifest_json.relative_to(ROOT)),
        },
    }
