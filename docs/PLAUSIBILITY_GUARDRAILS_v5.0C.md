# Step 5.0C — Plausibility guardrails

Purpose: add an explicit audit gate for biologically impossible, numerically unstable, or semantically inconsistent simulator outputs before scenario solvability and larger validation campaigns.

This is an engineering validation layer for an educational simulator. It is not external clinical validation and is not medical decision support.

## Implemented artifacts

- `data/plausibility_guardrails_v5.0C.yaml`
- `tools/plausibility_guardrails_v5_0C.py`
- `tests/test_v500c_plausibility_guardrails.py`
- `outputs/plausibility_guardrails_v5.0C/`

## Guardrail families

1. **Critical biological bounds**
   - saturation fractions must remain 0–1;
   - FiO2 must remain 0.21–1.0;
   - pH, PaCO2, MAP, HR, lactate, electrolytes and ventilator pressures must remain inside broad pediatric plausibility limits.

2. **Scenario-specific soft bounds**
   - healthy child, bronchiolitis, septic shock, anaphylaxis and hyperkalemia scenarios have softer review corridors.
   - These produce REVIEW findings only, not automatic failure.

3. **Logical consistency rules**
   - FiO2/SaO2 percent-vs-fraction mistakes;
   - severe hypoxemia with implausibly high PaO2;
   - profound hypotension with absent lactate signal;
   - finite electrolyte values.

4. **Clamp policy**
   - Current mode: `audit_only`.
   - The validation tool reports impossible states but does not silently clamp outputs.
   - Runtime clamping must remain explicit and module-owned.

## Current handoff result

Input: `outputs/monte_carlo_v5.0B/monte_carlo_results_v50B.csv`

- rows audited: 15
- findings: 0
- critical findings: 0
- review findings: 0
- pass guardrails: true

## Next step

Step 5.0D — Scenario solvability audit.

Every scenario should be checked for:

- solvable trajectory;
- fail-able trajectory;
- recovery path after correct action;
- deterioration path after delayed/wrong action;
- absence of deterministic single-outcome behavior.
