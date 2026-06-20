# v3.1 Step 4.43 — Advanced vasoactive engine

Educational, non-clinical extension of the vasoactive layer.

## Added
- Receptor-weighted qualitative signals: alpha-1, beta-1, beta-2, V1 and PDE3.
- First-order infusion hysteresis for norepinephrine, epinephrine, dopamine, milrinone and vasopressin.
- Exposure-dependent tachyphylaxis index for high-dose/prolonged pressor states.
- Interaction index for mixed pressor/inodilator combinations.
- Explicit audit fields for effective dose, SVR/CO/HR/inotropy modifiers.

## Deliberate limitations
This is not a bedside dosing model and must not be used for clinical titration. The module preserves monotonic educational behavior while exposing the assumptions that drive the simulated response.
