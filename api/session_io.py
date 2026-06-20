"""Session save/load and report export helpers for PDT v2.5.

The save format is intentionally JSON, deterministic, and educational/replay
oriented.  It stores session metadata, instructor notes, action events, compact
history, debrief metrics, and a final bedside snapshot.  Restored sessions are
rebuilt from the scenario YAML and action log where possible; this avoids unsafe
pickle/state serialization and keeps files portable across machines.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .debrief import emergency_metrics
from .instructor import export_instructor_report, report_to_markdown

ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = ROOT / "outputs" / "session_exports_v2.5"
SAVE_SCHEMA = "pdt-session-save-v2.5"


def _safe_name(text: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(text).strip()).strip("_")
    return name[:96] or "session"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _json_safe(obj: Any) -> Any:
    try:
        json.dumps(obj, default=str)
        return obj
    except Exception:
        if isinstance(obj, dict):
            return {str(k): _json_safe(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_json_safe(v) for v in obj]
        return str(obj)


def build_session_bundle(sess: Any, *, history_limit: int = 5000) -> Dict[str, Any]:
    """Return a portable JSON-serializable session save bundle."""
    history = sess.compact_history(limit=history_limit, profile="bedside")
    training_history = sess.compact_history(limit=history_limit, profile="training")
    debrief = emergency_metrics(training_history or history, sess.event_log)
    report = export_instructor_report(sess, debrief=debrief)
    actions = []
    for ev in list(sess.event_log):
        if isinstance(ev, dict) and ev.get("action"):
            actions.append({
                "t": float(ev.get("t", 0.0) or 0.0),
                "action": ev.get("action"),
                "payload": ev.get("payload") or {},
                "label": ev.get("label", ""),
            })
    return _json_safe({
        "schema": SAVE_SCHEMA,
        "created_utc": _utc_now(),
        "engine_version": (ROOT / "VERSION").read_text().strip() if (ROOT / "VERSION").exists() else "unknown",
        "session": {
            "session_id": sess.id,
            "scenario": sess.scenario_name,
            "scenario_path": str(sess.scenario_path.relative_to(ROOT)),
            "status": sess.status,
            "time_s": round(sess.time_s, 3),
            "duration_s": sess.T_sim,
            "dt": sess.dt,
            "speed": sess.speed,
            "snapshot_interval_s": sess.snapshot_interval_s,
            "max_history_points": sess.max_history_points,
            "history_window_s": sess.history_window_s,
            "history_decimation_s": sess.history_decimation_s,
        },
        "final_state": sess.state(profile="bedside"),
        "history": history,
        "training_history": training_history,
        "event_log": list(sess.event_log),
        "action_replay_log": actions,
        "instructor": sess.instructor_state(),
        "debrief": debrief,
        "instructor_report": report,
        "safety_note": "Educational/research alpha only. Not for clinical use. Not a medical device.",
    })


def bundle_to_markdown(bundle: Dict[str, Any]) -> str:
    session = bundle.get("session", {})
    debrief = bundle.get("debrief", {}) or {}
    metrics = debrief.get("metrics", {}) or {}
    flags = [f for f in debrief.get("flags", []) if f.get("triggered")]
    instructor = bundle.get("instructor", {}) or {}
    lines: List[str] = []
    lines.append(f"# PDT Session Report — {session.get('scenario', 'unknown')}")
    lines.append("")
    lines.append("Educational/research alpha only. Not for clinical use. Not a medical device.")
    lines.append("")
    lines.append("## Session")
    lines.append(f"- Schema: `{bundle.get('schema', '')}`")
    lines.append(f"- Version: `{bundle.get('engine_version', '')}`")
    lines.append(f"- Session ID: `{session.get('session_id', '')}`")
    lines.append(f"- Scenario path: `{session.get('scenario_path', '')}`")
    lines.append(f"- Time: {session.get('time_s', 0)} / {session.get('duration_s', 0)} s")
    lines.append(f"- dt: {session.get('dt', '')} s")
    lines.append("")
    lines.append("## Debrief metrics")
    for key in [
        "SpO2_nadir", "time_below_SpO2_90_s", "time_below_SpO2_80_s", "PaCO2_peak",
        "MAP_min", "failed_intubation_count", "intubation_attempt_count", "first_rescue_ventilation_time_s",
        "intubation_success_time_s", "time_to_reoxygenation_after_intubation_s",
    ]:
        if key in metrics:
            lines.append(f"- {key}: {metrics.get(key)}")
    lines.append("")
    lines.append("## Triggered decision flags")
    if flags:
        for flag in flags:
            lines.append(f"- {flag.get('flag')}: {flag.get('value')}")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## Instructor notes")
    notes = instructor.get("notes", []) or []
    if notes:
        for note in notes:
            pin = " pinned" if note.get("pinned") else ""
            lines.append(f"- t={note.get('t')} s [{note.get('kind')}{pin}]: {note.get('text')}")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## Event log")
    events = bundle.get("event_log", []) or []
    if events:
        for ev in events[-50:]:
            lines.append(f"- t={ev.get('t', '')} s: {ev.get('label', ev.get('action', 'event'))}")
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def save_bundle_files(bundle: Dict[str, Any], *, basename: str | None = None, output_dir: Path | None = None) -> Dict[str, Any]:
    outdir = output_dir or EXPORT_DIR
    outdir.mkdir(parents=True, exist_ok=True)
    session = bundle.get("session", {})
    stem = _safe_name(basename or f"{session.get('scenario','session')}_{session.get('session_id','')[:8]}_{int(float(session.get('time_s', 0) or 0))}s")
    json_path = outdir / f"{stem}.json"
    md_path = outdir / f"{stem}.md"
    json_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(bundle_to_markdown(bundle), encoding="utf-8")
    return {
        "status": "saved",
        "json_path": str(json_path.relative_to(ROOT)),
        "markdown_path": str(md_path.relative_to(ROOT)),
        "bytes_json": json_path.stat().st_size,
        "bytes_markdown": md_path.stat().st_size,
    }


def read_bundle_from_path(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    if not p.exists():
        raise FileNotFoundError(f"Saved session file not found: {path}")
    if p.suffix.lower() != ".json":
        raise ValueError("Saved session import expects a .json file")
    data = json.loads(p.read_text(encoding="utf-8"))
    validate_bundle(data)
    return data


def validate_bundle(data: Dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise ValueError("Saved session bundle must be a JSON object")
    if data.get("schema") != SAVE_SCHEMA:
        raise ValueError(f"Unsupported saved session schema: {data.get('schema')}")
    session = data.get("session") or {}
    if not session.get("scenario_path") and not session.get("scenario"):
        raise ValueError("Saved session is missing scenario metadata")
