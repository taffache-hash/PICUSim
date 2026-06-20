#!/usr/bin/env python3
"""Generate an automatic HTML/CSV/PNG report for one PDT scenario (v0.15)."""
from __future__ import annotations

import argparse
import html
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from simtools import run_scenario, scenario_path, summarize_dataframe, write_json  # noqa: E402

PLOT_GROUPS = [
    ("gas_exchange", ["SaO2", "PaO2", "PaCO2", "pH_a"]),
    ("hemodynamics", ["MAP", "HR", "CO", "SVR", "PVR"]),
    ("ventilator_lung", ["Vt", "PEEP", "Paw", "Pdriving", "recruited_frac", "VILI_risk"]),
    ("metabolism_fluids", ["lactate", "DO2", "VO2", "Hb", "fluid_balance", "urine_rate_mL_h"]),
    ("clinical_axes", ["pain_score", "stress_index", "sedation_score", "airway_obstruction_index", "sepsis_severity_score", "ICP_mmHg"]),
    ("endocrine_axis", ["glucose_mmol_L", "cortisol_activity", "catecholamine_tone", "adrenal_insufficiency_index", "insulin_resistance_index", "stress_hyperglycemia_index", "ADH_water_retention_index"]),
]


def _plot_group(df: pd.DataFrame, group_name: str, cols: list[str], out: Path) -> str | None:
    cols = [c for c in cols if c in df.columns]
    if not cols:
        return None
    fig = plt.figure(figsize=(10, 5.8))
    ax = fig.add_subplot(1, 1, 1)
    x = df.index.values
    for c in cols:
        y = df[c].values
        if c == "SaO2":
            y = y * 100.0
            label = "SaO2_%"
        else:
            label = c
        ax.plot(x, y, label=label)
    ax.set_xlabel("time [s]")
    ax.set_title(group_name.replace("_", " ").title())
    ax.legend(loc="best", fontsize=8)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fn = f"{group_name}.png"
    fig.savefig(out / fn, dpi=160)
    plt.close(fig)
    return fn


def _warnings(summary: dict) -> list[str]:
    w = []
    if summary.get("SaO2_min", 1.0) < 0.90:
        w.append("Hypoxemia occurred: SaO2 < 90% at least once.")
    if summary.get("PaCO2_max", 0.0) > 60:
        w.append("Hypercapnia occurred: PaCO2 > 60 mmHg at least once.")
    if summary.get("pH_a_min", 7.4) < 7.20:
        w.append("Severe acidemia occurred: pH < 7.20 at least once.")
    if summary.get("MAP_min", 100.0) < 50:
        w.append("Hypotension occurred: MAP < 50 mmHg at least once.")
    if summary.get("VILI_risk_max", 0.0) > 0.50:
        w.append("High qualitative VILI risk detected: VILI_risk > 0.50.")
    if summary.get("lactate_max", 0.0) > 4.0:
        w.append("High lactate burden detected: lactate > 4 mmol/L.")
    return w


def _html_table(data: dict, max_rows: int = 80) -> str:
    items = [(k, v) for k, v in sorted(data.items()) if isinstance(v, (int, float))]
    rows = []
    for k, v in items[:max_rows]:
        rows.append(f"<tr><td>{html.escape(k)}</td><td>{float(v):.4g}</td></tr>")
    return "<table><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>" + "\n".join(rows) + "</tbody></table>"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--dt", type=float, default=0.1)
    parser.add_argument("--outdir")
    args = parser.parse_args(argv)

    scen = scenario_path(args.scenario)
    ts = time.strftime("%Y%m%d_%H%M%S")
    out = Path(args.outdir) if args.outdir else ROOT / "outputs" / "reports" / f"{scen.stem}_{ts}"
    out.mkdir(parents=True, exist_ok=True)

    cfg, df = run_scenario(scen, dt=args.dt, quiet=True)
    df.to_csv(out / "timeseries.csv")
    summary = summarize_dataframe(df)
    write_json(summary, out / "summary.json")

    images = []
    for name, cols in PLOT_GROUPS:
        img = _plot_group(df, name, cols, out)
        if img:
            images.append((name, img))

    warnings = _warnings(summary)
    warning_html = "<p>No automatic physiologic warnings.</p>" if not warnings else "<ul>" + "".join(f"<li>{html.escape(x)}</li>" for x in warnings) + "</ul>"
    imgs_html = "\n".join(f"<h2>{html.escape(name.replace('_',' ').title())}</h2><img src='{html.escape(img)}' />" for name, img in images)
    report = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>PDT Scenario Report - {html.escape(scen.stem)}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 28px; line-height: 1.35; }}
table {{ border-collapse: collapse; width: 100%; max-width: 980px; }}
th, td {{ border: 1px solid #ddd; padding: 6px 8px; }}
th {{ background: #f1f1f1; }}
img {{ max-width: 100%; border: 1px solid #ddd; margin-bottom: 24px; }}
.note {{ color: #555; }}
</style></head><body>
<h1>Pediatric Digital Twin — Scenario Report</h1>
<p><b>Scenario:</b> {html.escape(scen.name)}<br>
<b>Generated:</b> {html.escape(ts)}<br>
<b>dt:</b> {args.dt} s<br>
<b>Simulation time:</b> {float(cfg.get('simulation_time_s', 0)):.1f} s</p>
<p class='note'>This report supports in-silico exploration. It is not clinical validation and must not be used for patient-specific decision-making.</p>
<h2>Automatic warnings</h2>
{warning_html}
<h2>Summary metrics</h2>
{_html_table(summary)}
{imgs_html}
</body></html>"""
    (out / "report.html").write_text(report)

    print(f"Report generated: {out / 'report.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
