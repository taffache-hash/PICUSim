# v3.1 Step 3.6 — Respiratory drug response contract

Scope: salbutamol, ipratropium, magnesium, nebulized epinephrine and inhaled nitric oxide (iNO). This step does not modify opioids, GABA sedatives, ketamine, alpha-2 agonists, rocuronium, steroids, insulin, furosemide, antibiotics, Docker packaging or graphical monitor curves.

## Design decision

Respiratory drugs are kept in respiratory/pulmonary modules rather than being folded into systemic vasoactive or analgosedation pathways.

- Bronchodilators act in `AirwayObstructionModule` by reducing effective bronchospasm-driven obstruction, resistance, air-trapping, auto-PEEP, dead-space and mucus/small-airway penalties to a lesser extent.
- Salbutamol and nebulized epinephrine expose a small `bronchodilator_HR_mod` tachycardia signal, consumed separately by `BaroreflexModule`.
- Ipratropium and magnesium do not create a direct HR signal in this contract.
- Nebulized epinephrine exposes an upper-airway relief audit signal, without rewriting the underlying scenario obstruction target.
- iNO acts only through `ino_PVR_mod` and `ino_Qs_Qt_mod`; it does not directly write systemic SVR/MAP.

## Added audit variables

Bronchodilator/airway:

- `salbutamol_bronchodilation_signal`
- `salbutamol_tachycardia_signal`
- `ipratropium_bronchodilation_signal`
- `magnesium_bronchodilation_signal`
- `nebulized_epinephrine_bronchodilation_signal`
- `nebulized_epinephrine_upper_airway_relief_signal`
- `nebulized_epinephrine_tachycardia_signal`
- `upper_airway_relief_signal`
- `bronchodilator_HR_mod`

Inhaled nitric oxide:

- `ino_pulmonary_vasodilation_signal`
- `ino_oxygenation_signal`
- `ino_rebound_risk_signal`

## Modified files

- `core/bus.py`
- `modules/airway/obstruction.py`
- `modules/pharmacology/ino.py`
- `modules/cardiovascular/baroreflex.py`
- `tests/test_v311_respiratory_drug_response_contract.py`
- `VERSION`
- `CHANGELOG.md`
- `STEP3_6_RESPIRATORY_DRUG_RESPONSE_REPORT.md`

## Tests

Added `tests/test_v311_respiratory_drug_response_contract.py` with five contract tests:

1. Salbutamol dose-response reduces obstruction/resistance/air-trapping/auto-PEEP.
2. Salbutamol, ipratropium, magnesium and nebulized epinephrine expose separate directional signals.
3. Bronchodilators do not directly write `drug_MAP_mod` or `drug_SVR_mod`.
4. iNO reduces PVR and shunt modifiers with onset/offset and rebound-risk signal during washout.
5. iNO reduces pulmonary vascular tone without directly changing systemic vascular tone.

## Limitations

- No full upper-airway/croup dynamic model yet; nebulized epinephrine currently exposes a relief signal but does not overwrite event-driven obstruction state.
- No PK model for salbutamol/ipratropium/magnesium/nebulized epinephrine; effects are direct educational PD dose-response placeholders.
- No methemoglobinemia/NO2 toxicity module for iNO.
- No graphical monitor/curve update in this step.
