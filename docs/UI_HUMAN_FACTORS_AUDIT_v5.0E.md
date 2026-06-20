# Step 5.0E — UI Human Factors Audit v2

Purpose: pre-validation audit of the local console from a human-use perspective.

This step checks whether the interface is still usable after the monitor layout compression introduced in Step 4.51. It is not a formal usability study and does not provide clinical validation.

## Audit gates

- Core DOM targets must be present and unique.
- Session controls must remain reachable.
- Apparatus panels must be reachable from dock and tabs.
- Numeric vital signs must be visually dominant.
- Waveforms must remain supportive and compressed.
- Click density must remain below predefined review thresholds.
- Core JavaScript targets must resolve.

## Outputs

Generated under `outputs/ui_human_factors_v5.0E/`:

- `ui_human_factors_audit_v50E.csv`
- `ui_human_factors_summary_v50E.json`
- `ui_human_factors_report_v50E.md`

## Interpretation

Passing this audit means the console is structurally suitable for continued validation. It does not mean that clinicians have observed and scored the UI in a formal human-factors study.
