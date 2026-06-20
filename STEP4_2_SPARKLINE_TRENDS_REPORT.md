# PCCSim v3.1 Step 4.2 — Bedside sparkline trends

## Scope

UI-only bedside monitor improvement. No physiological model, backend API, Docker or pharmacology changes.

## Implemented

- Added small trend canvases inside the primary vital cards.
- Trends shown for:
  - HR
  - SpO2
  - MAP
  - PaCO2 with EtCO2 as a secondary line
  - Paw
  - FiO2
- The trend buffer is populated from the existing bedside WebSocket stream.
- The buffer keeps approximately the last 10 simulated minutes and is capped at 2400 samples.
- Trends reset automatically if session time moves backwards, for example after reset or loading another scenario.

## Files changed

- `ui/index.html`
- `ui/app.js`
- `ui/styles.css`
- `tests/test_v318_bedside_sparkline_trends_contract.py`
- `VERSION`
- `CHANGELOG.md`
- `docs/PCCSIM_V3_1_PHARMACOLOGY_AND_UI_ROADMAP.md`

## Non-goals

- No threshold alarms.
- No labs strip.
- No scenario info card.
- No backend state-profile changes.
- No Docker rebuild-specific edits.
