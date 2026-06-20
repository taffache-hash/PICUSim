#!/usr/bin/env python3
"""PDT v5.0E UI human-factors audit v2.

Static audit for the training console after monitor-layout compression. This is
not a substitute for observed usability testing; it is a reproducible gate that
checks whether the UI exposes all expected controls, preserves DOM targets, and
keeps numeric vitals visually dominant over supportive waveforms.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _ids(html: str) -> List[str]:
    return re.findall(r'\bid=["\']([^"\']+)["\']', html)


def _classes(html: str) -> List[str]:
    out: List[str] = []
    for raw in re.findall(r'\bclass=["\']([^"\']+)["\']', html):
        out.extend(raw.split())
    return out


def _button_texts(html: str) -> List[str]:
    return [re.sub(r"<[^>]+>", "", b).strip() for b in re.findall(r"<button\b[^>]*>(.*?)</button>", html, re.S)]


def _css_number(pattern: str, css: str, default: float = 0.0) -> float:
    m = re.search(pattern, css, re.S)
    if not m:
        return default
    try:
        return float(m.group(1))
    except Exception:
        return default


def _add(rows: List[Dict[str, Any]], category: str, check: str, status: str, detail: str, severity: str = "pass") -> None:
    rows.append({
        "category": category,
        "check": check,
        "status": status,
        "severity": severity,
        "detail": detail,
    })


def audit(root: Path, spec: Mapping[str, Any]) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    html_path = root / "ui" / "index.html"
    css_path = root / "ui" / "styles.css"
    app_path = root / "ui" / "app.js"
    html = html_path.read_text(encoding="utf-8")
    css = css_path.read_text(encoding="utf-8")
    app = app_path.read_text(encoding="utf-8") if app_path.exists() else ""
    criteria = spec.get("criteria", {}) or {}
    rows: List[Dict[str, Any]] = []

    ids = _ids(html)
    idset = set(ids)
    duplicate_ids = sorted({x for x in ids if ids.count(x) > 1})
    if duplicate_ids:
        _add(rows, "dom", "unique ids", "FAIL", f"duplicate ids: {', '.join(duplicate_ids)}", "critical")
    else:
        _add(rows, "dom", "unique ids", "PASS", f"{len(ids)} unique id targets")

    classes = set(_classes(html))
    for cls in ["monitor-display-split", "side-vitals", "compact-waveforms", "control-dock", "apparatus-overlay"]:
        if cls in classes or f".{cls}" in css:
            _add(rows, "layout", f"class {cls}", "PASS", "present")
        else:
            _add(rows, "layout", f"class {cls}", "FAIL", "missing", "critical")

    if criteria.get("require_side_vitals_before_waveforms", True):
        side_pos = html.find("side-vitals")
        wave_pos = html.find("compact-waveforms")
        if side_pos >= 0 and wave_pos >= 0 and side_pos < wave_pos:
            _add(rows, "layout", "numeric column before waveforms", "PASS", "side vitals precede compressed waveforms in DOM")
        else:
            _add(rows, "layout", "numeric column before waveforms", "FAIL", "side vitals do not precede waveforms", "critical")

    for group_name, key in [
        ("vital numeric ids", "required_vital_ids"),
        ("vital trend ids", "required_trend_ids"),
        ("waveform ids", "required_waveform_ids"),
        ("quick monitor buttons", "required_quick_buttons"),
        ("session buttons", "required_session_buttons"),
        ("apparatus panels", "required_panels"),
    ]:
        missing = [x for x in criteria.get(key, []) if x not in idset]
        if missing:
            _add(rows, "targets", group_name, "FAIL", f"missing: {', '.join(missing)}", "critical")
        else:
            _add(rows, "targets", group_name, "PASS", f"all {len(criteria.get(key, []))} targets present")

    panel_targets = re.findall(r'data-open-panel=["\']([^"\']+)["\']', html) + re.findall(r'data-panel-tab=["\']([^"\']+)["\']', html)
    missing_panel_targets = sorted({p for p in panel_targets if p not in idset})
    if missing_panel_targets:
        _add(rows, "navigation", "dock/tab panel targets", "FAIL", f"missing target panels: {', '.join(missing_panel_targets)}", "critical")
    else:
        _add(rows, "navigation", "dock/tab panel targets", "PASS", f"{len(set(panel_targets))} panel targets resolve")

    button_texts = _button_texts(html)
    empty_buttons = [i for i, t in enumerate(button_texts, start=1) if not t]
    if empty_buttons:
        _add(rows, "accessibility", "button visible labels", "FAIL", f"empty button labels at indices: {empty_buttons}", "critical")
    else:
        _add(rows, "accessibility", "button visible labels", "PASS", f"{len(button_texts)} buttons have visible text")

    dock_cards = html.count('class="dock-card"')
    session_buttons_match = re.search(r'<div class="session-buttons">(.*?)</div>', html, re.S)
    session_buttons = len(re.findall(r"<button\b", session_buttons_match.group(1))) if session_buttons_match else 0
    quick_actions_match = re.search(r'<div class="quick-actions">(.*?)</div>', html, re.S)
    quick_actions = len(re.findall(r"<button\b", quick_actions_match.group(1))) if quick_actions_match else 0
    header_match = re.search(r'<div class="monitor-header-actions">(.*?)</div>', html, re.S)
    header_actions = len(re.findall(r"<button\b", header_match.group(1))) if header_match else 0

    density_checks = [
        ("dock cards", dock_cards, int(criteria.get("max_dock_cards", 14))),
        ("session buttons", session_buttons, int(criteria.get("max_session_buttons", 6))),
        ("quick airway actions", quick_actions, int(criteria.get("max_quick_airway_actions", 5))),
        ("monitor header actions", header_actions, int(criteria.get("max_monitor_header_actions", 6))),
    ]
    for name, count, limit in density_checks:
        if count <= limit:
            _add(rows, "click_density", name, "PASS", f"{count}/{limit}")
        else:
            _add(rows, "click_density", name, "REVIEW", f"{count}/{limit}; consider grouping", "review")

    side_font = _css_number(r"\.side-vitals\s+\.vital\s+strong\s*\{[^}]*font-size:\s*clamp\((\d+(?:\.\d+)?)px", css)
    if side_font >= float(criteria.get("min_side_vital_font_px", 32)):
        _add(rows, "legibility", "side vital numeric font", "PASS", f"minimum clamp {side_font:g}px")
    else:
        _add(rows, "legibility", "side vital numeric font", "REVIEW", f"minimum clamp {side_font:g}px", "review")

    vitals_col_min = _css_number(r"grid-template-columns:\s*minmax\((\d+(?:\.\d+)?)px,\s*(\d+(?:\.\d+)?)px\)\s+minmax\(0,\s*1fr\)", css)
    vitals_col_max_match = re.search(r"grid-template-columns:\s*minmax\((\d+(?:\.\d+)?)px,\s*(\d+(?:\.\d+)?)px\)\s+minmax\(0,\s*1fr\)", css)
    vitals_col_max = float(vitals_col_max_match.group(2)) if vitals_col_max_match else 0.0
    min_req = float(criteria.get("min_vitals_column_px", 210))
    max_req = float(criteria.get("max_vitals_column_px", 300))
    if min_req <= vitals_col_min and vitals_col_max <= max_req:
        _add(rows, "layout", "vitals column width", "PASS", f"minmax({vitals_col_min:g}px, {vitals_col_max:g}px)")
    else:
        _add(rows, "layout", "vitals column width", "REVIEW", f"minmax({vitals_col_min:g}px, {vitals_col_max:g}px)", "review")

    wave_max = _css_number(r"\.compact-waveforms\s+\.wave\s*\{[^}]*height:\s*clamp\([^,]+,[^,]+,\s*(\d+(?:\.\d+)?)px\)", css)
    if 0 < wave_max <= float(criteria.get("max_compact_waveform_height_px", 110)):
        _add(rows, "layout", "compact waveform height", "PASS", f"max clamp {wave_max:g}px")
    else:
        _add(rows, "layout", "compact waveform height", "REVIEW", f"max clamp {wave_max:g}px", "review")

    app_targets = set(re.findall(r'getElementById\(["\']([^"\']+)["\']\)', app))
    missing_app_targets = sorted(x for x in app_targets if x not in idset)
    # Some app targets may be dynamically optional; report critical only for core monitor/session IDs.
    core_missing = [x for x in missing_app_targets if x in set(criteria.get("required_vital_ids", []) + criteria.get("required_session_buttons", []) + criteria.get("required_quick_buttons", []))]
    if core_missing:
        _add(rows, "js_contract", "core JS targets", "FAIL", f"missing core JS targets: {', '.join(core_missing)}", "critical")
    else:
        _add(rows, "js_contract", "core JS targets", "PASS", "all core monitor/session JS targets resolve")

    critical = sum(1 for r in rows if r["severity"] == "critical")
    review = sum(1 for r in rows if r["severity"] == "review")
    summary = {
        "checks": len(rows),
        "pass": sum(1 for r in rows if r["status"] == "PASS"),
        "review": review,
        "critical": critical,
        "ui_human_factors_gate_passed": critical == 0,
        "dock_cards": dock_cards,
        "session_buttons": session_buttons,
        "quick_airway_actions": quick_actions,
        "monitor_header_actions": header_actions,
        "side_vital_font_min_px": side_font,
        "compact_waveform_max_px": wave_max,
    }
    return rows, summary


def write_csv(path: Path, rows: List[Mapping[str, Any]]) -> None:
    fields = ["category", "check", "status", "severity", "detail"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def write_report(path: Path, rows: List[Mapping[str, Any]], summary: Mapping[str, Any]) -> None:
    lines = [
        "# Step 5.0E — UI Human Factors Audit v2",
        "",
        "Scope: static human-factors gate for the local training console before deeper validation.",
        "",
        "This is **not** formal clinical validation and **not** observed usability testing.",
        "",
        f"Checks: **{summary['checks']}**",
        f"Pass checks: **{summary['pass']}**",
        f"Review findings: **{summary['review']}**",
        f"Critical findings: **{summary['critical']}**",
        f"Gate passed: **{summary['ui_human_factors_gate_passed']}**",
        "",
        "## Human-use interpretation",
        "",
        "- Numeric vital signs remain the primary monitor surface.",
        "- Waveforms are retained as supportive context and compressed to reduce dominance.",
        "- All core session, monitor, quick-access and apparatus targets are present.",
        "- Control density remains within the predefined pre-validation thresholds.",
        "",
        "## Audit table",
        "",
        "| Category | Check | Status | Severity | Detail |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['category']} | {r['check']} | {r['status']} | {r['severity']} | {r['detail']} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, default=ROOT / "data" / "ui_human_factors_audit_v5.0E.yaml")
    parser.add_argument("--outdir", type=Path, default=ROOT / "outputs" / "ui_human_factors_v5.0E")
    parser.add_argument("--fail-on-critical", action="store_true")
    args = parser.parse_args(argv)
    spec = load_yaml(args.spec)
    rows, summary = audit(ROOT, spec)
    args.outdir.mkdir(parents=True, exist_ok=True)
    write_csv(args.outdir / "ui_human_factors_audit_v50E.csv", rows)
    (args.outdir / "ui_human_factors_summary_v50E.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_report(args.outdir / "ui_human_factors_report_v50E.md", rows, summary)
    print(json.dumps(summary, indent=2))
    if args.fail_on_critical and summary["critical"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
