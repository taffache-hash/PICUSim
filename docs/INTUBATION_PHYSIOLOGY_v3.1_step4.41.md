# Intubation physiology — v3.1 Step 4.41

Educational/non-clinical peri-intubation physiology layer.

## Scope

Step 4.41 adds a narrow physiologic scaffold around the existing airway action/event system:

- preoxygenation reservoir `[0-1]`
- apnea timer and safe-apnea reserve proxy
- bounded desaturation trajectory during apnea
- RSI drug-effect coupling from NMB/sedation signals
- qualitative warning/phase fields for instructor feedback

This module does not decide when to intubate and does not provide clinical dosing or clinical airway guidance.

## New module

`modules/airway/intubation_physiology.py`

Class: `IntubationPhysiologyModule`

Revision marker: `intubation_physiology_revision = 441`.

## Main Bus fields

- `preoxygenation_active`
- `preoxygenation_reservoir`
- `apnea_active`
- `apnea_timer_s`
- `safe_apnea_time_remaining_s`
- `rsi_effect_active`
- `rsi_resp_suppression_index`
- `peri_intubation_desaturation_risk`
- `peri_intubation_desaturation_slope`
- `peri_intubation_phase`
- `peri_intubation_warning`

## Coupling notes

The module reads existing airway flags such as `intubated`, `ventilator_connected`, `manual_ventilation_active`, `bag_mask_quality`, `airway_event_type`, `drug_NMB_frac`, and `sed_resp_mod`.

During apnea, it can apply a bounded downward SaO2/PaO2 trajectory. During effective oxygenation with high FiO2, it allows slow oxygenation recovery. Final gas-exchange modules may still own later equilibrium behavior depending on execution order.

## Contract tests

`tests/test_v441_intubation_physiology_contract.py`

The tests verify:

1. preoxygenation reservoir builds with high FiO2 and effective ventilation;
2. apnea timer/desaturation risk rise after failed RSI-like apnea;
3. bag-mask ventilation reduces apnea burden and recovers the phase.
