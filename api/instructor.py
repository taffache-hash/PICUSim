"""Instructor-mode helpers for the PDT v2.3 web console.

This module is deliberately lightweight: it defines action presets, note/report
helpers, and a narrow instructor-facing data model.  It does not execute code or
alter the physiology engine directly; actions still pass through the validated
API action router.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parents[1]


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists() or yaml is None:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


INSTRUCTOR_PRESETS: List[Dict[str, Any]] = [
    {
        "id": "failed_attempt_moderate",
        "label": "Failed intubation",
        "category": "airway",
        "action": "airway_event",
        "payload": {"name": "failed_intubation_attempt", "severity": "moderate"},
        "teaching_use": "Escalation trigger after an unsuccessful airway attempt.",
    },
    {
        "id": "bag_mask_adequate",
        "label": "Bag-mask rescue",
        "category": "airway",
        "action": "airway_event",
        "payload": {"name": "start_bag_mask_ventilation", "severity": "adequate"},
        "teaching_use": "Rescue oxygenation before a repeat intubation attempt.",
    },
    {
        "id": "intubate_emergency",
        "label": "Intubation success",
        "category": "airway",
        "action": "airway_event",
        "payload": {"name": "perform_intubation", "severity": "emergency"},
        "teaching_use": "Secured airway with invasive ventilation.",
    },
    {
        "id": "laryngospasm_severe",
        "label": "Severe laryngospasm",
        "category": "airway",
        "action": "airway_event",
        "payload": {"name": "laryngospasm", "severity": "severe"},
        "teaching_use": "Post-extubation upper-airway obstruction scenario.",
    },
    {
        "id": "aspiration_moderate",
        "label": "Aspiration event",
        "category": "airway",
        "action": "airway_event",
        "payload": {"name": "aspiration_event", "severity": "moderate"},
        "teaching_use": "RSI complication or airway protection failure.",
    },
    {
        "id": "accidental_extubation_severe",
        "label": "Accidental extubation",
        "category": "airway",
        "action": "airway_event",
        "payload": {"name": "accidental_extubation", "severity": "severe"},
        "teaching_use": "PICU tube-loss emergency.",
    },
    {
        "id": "hypoxia_challenge",
        "label": "Reduce FiO2",
        "category": "ventilation",
        "action": "set_fio2",
        "payload": {"value": 0.30},
        "teaching_use": "Creates a reversible oxygenation challenge.",
    },
    {
        "id": "full_oxygen",
        "label": "FiO2 1.0",
        "category": "ventilation",
        "action": "set_fio2",
        "payload": {"value": 1.0},
        "teaching_use": "Emergency oxygenation intervention.",
    },
    {
        "id": "peep_up",
        "label": "PEEP 8",
        "category": "ventilation",
        "action": "set_peep",
        "payload": {"value": 8.0},
        "teaching_use": "Ventilatory escalation after hypoxemia.",
    },
    {
        "id": "adrenaline_start",
        "label": "Adrenaline 0.05",
        "category": "circulation",
        "action": "set_adrenaline",
        "payload": {"value": 0.05},
        "teaching_use": "Hemodynamic escalation in shock/low output.",
    },
    {
        "id": "noradrenaline_start",
        "label": "Noradrenaline 0.05",
        "category": "circulation",
        "action": "set_norad",
        "payload": {"value": 0.05},
        "teaching_use": "Vasopressor escalation in vasodilatory shock.",
    },
]


def instructor_presets() -> List[Dict[str, Any]]:
    """Return safe instructor action presets for the web UI."""
    event_spec = _load_yaml(ROOT / "data" / "airway_events_v1.24.yaml").get("events", {})
    out: List[Dict[str, Any]] = []
    for item in INSTRUCTOR_PRESETS:
        row = dict(item)
        if row.get("action") == "airway_event":
            name = row.get("payload", {}).get("name")
            severity = row.get("payload", {}).get("severity")
            row["available"] = bool(name in event_spec and severity in (event_spec.get(name, {}).get("severities", {}) or {}))
        else:
            row["available"] = True
        out.append(row)
    return out


def new_note(t: float, text: str, kind: str = "note", pinned: bool = False) -> Dict[str, Any]:
    return {
        "t": round(float(t), 3),
        "kind": str(kind or "note"),
        "text": str(text or "").strip(),
        "pinned": bool(pinned),
    }


def export_instructor_report(session, debrief: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Build a compact instructor report from a running session."""
    notes = list(getattr(session, "instructor_notes", []))
    events = list(getattr(session, "event_log", []))
    state = session.state(profile="bedside")
    metrics = (debrief or {}).get("metrics", {}) if isinstance(debrief, dict) else {}
    flags = (debrief or {}).get("flags", []) if isinstance(debrief, dict) else []
    triggered_flags = [f for f in flags if f.get("triggered")]
    return {
        "session_id": session.id,
        "scenario": session.scenario_name,
        "time_s": round(session.time_s, 3),
        "status": session.status,
        "learner_diagnosis_hidden": bool(getattr(session, "learner_diagnosis_hidden", False)),
        "instructor_notes": notes,
        "event_count": len(events),
        "events": events[-100:],
        "final_state": state,
        "debrief_metrics": metrics,
        "triggered_flags": triggered_flags,
        "summary": {
            "notes": len(notes),
            "pinned_notes": sum(1 for n in notes if n.get("pinned")),
            "triggered_flags": len(triggered_flags),
            "SpO2_nadir": metrics.get("SpO2_nadir"),
            "time_below_SpO2_90_s": metrics.get("time_below_SpO2_90_s"),
            "PaCO2_peak": metrics.get("PaCO2_peak"),
            "MAP_min": metrics.get("MAP_min"),
        },
        "safety_note": "Educational/research alpha only. Not for clinical use. Not a medical device.",
    }


def report_to_markdown(report: Dict[str, Any]) -> str:
    """Render an instructor report to a plain Markdown document."""
    lines: List[str] = []
    lines.append("# PDT instructor report")
    lines.append("")
    lines.append(f"- Scenario: `{report.get('scenario')}`")
    lines.append(f"- Session: `{report.get('session_id')}`")
    lines.append(f"- Time: {report.get('time_s')} s")
    lines.append(f"- Status: {report.get('status')}")
    lines.append(f"- Learner diagnosis hidden: {report.get('learner_diagnosis_hidden')}")
    lines.append("")
    lines.append("## Summary metrics")
    for k, v in (report.get("summary") or {}).items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Triggered flags")
    flags = report.get("triggered_flags") or []
    if flags:
        for f in flags:
            lines.append(f"- {f.get('flag')}: {f.get('value')}")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## Instructor notes")
    notes = report.get("instructor_notes") or []
    if notes:
        for n in notes:
            pin = " pinned" if n.get("pinned") else ""
            lines.append(f"- t={n.get('t')} s [{n.get('kind')}{pin}]: {n.get('text')}")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## Recent events")
    events = report.get("events") or []
    if events:
        for e in events[-25:]:
            lines.append(f"- t={e.get('t')} s: {e.get('label', e.get('event', 'event'))}")
    else:
        lines.append("- None")
    lines.append("")
    lines.append(report.get("safety_note", ""))
    return "\n".join(lines).strip() + "\n"
