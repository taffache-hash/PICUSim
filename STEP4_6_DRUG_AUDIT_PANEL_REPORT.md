# Step 4.6 - Drug Audit Panel

Added a manual, snapshot-only drug audit panel inside the Drugs surface.

## Behavior

- No new route.
- No polling loop.
- The panel reads `/session/{id}/state?profile=full` only when `Aggiorna audit` is pressed.
- Each card shows dose, concentration when exposed by the Bus, PD/audit signals, and risk signals when available.
- Missing model outputs remain visible as `--` rather than being inferred.

## Files

- `ui/index.html`
- `ui/app.js`
- `ui/styles.css`
- `tests/test_v324_drug_audit_panel_contract.py`

## Verification

Targeted contract:

```bash
pytest tests/test_v324_drug_audit_panel_contract.py
```
