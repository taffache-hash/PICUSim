# STEP 3.5 — Rocuronium / neuromuscular blockade response contract

## Scope

This step is intentionally narrow. It reviews rocuronium/paralysis behavior only.
It does not change bronchodilators, steroids, insulin, antibiotics, ventilator
PEEP synchronization, graphical arterial waveforms or Docker packaging logic.

## Problem identified

Rocuronium already produced a `drug_NMB_frac` signal in the PK/PD module, and
ChemoreflexModule used this signal to reduce `Pmus`. However, the
PainStressSedationModule also included neuromuscular blockade inside the
`sed_resp_mod` pathway and inside the non-GABA respiratory-sedation signal.

That created two conceptual problems:

1. rocuronium could be counted as respiratory sedation in addition to true
   neuromuscular blockade;
2. rocuronium could look like analgosedation, although paralysis is not
   analgesia or sedation.

## Changes made

### PharmacologyModule

- Keeps rocuronium as a neuromuscular-blockade drug only.
- Publishes explicit audit variables:
  - `rocuronium_nmb_signal`
  - `neuromuscular_blockade_active`
  - `spontaneous_effort_available`
  - `nmb_trigger_block_active`
- Does not assign rocuronium any direct oxygenation or ventilation benefit.

### PainStressSedationModule

- Removed rocuronium/NMB from `sed_resp_mod`.
- Removed rocuronium/NMB from `sedation_non_gaba_resp_signal`.
- Removed rocuronium/NMB from `sedation_score`.
- Rocuronium therefore does not create analgesia or sedation.

### ChemoreflexModule

- Uses `drug_NMB_frac` as the single pathway by which rocuronium reduces motor
  respiratory output.
- Spontaneous/assisted RR now follows the post-pharmacologic motor target, not
  the unblocked chemical stimulus alone.
- Full NMB therefore suppresses effective spontaneous effort and triggering.
- Controlled modes still keep the set ventilator RR.

### VentilatorModule

- Patient-trigger logic now explicitly treats NMB >= 0.90 as trigger-blocking.
- Added `nmb_trigger_block_active` audit output in the main ventilator state.

## Expected behavior

Rocuronium dose increase should produce:

```text
C_rocuronium_ng_mL ↑
drug_NMB_frac ↑
rocuronium_nmb_signal ↑
spontaneous_effort_available ↓
Pmus ↓
patient_triggered = false when NMB is high
```

Rocuronium should not produce:

```text
analgesia_score ↑
sedation_score ↑
sed_resp_mod ↓ through a separate sedation pathway
immediate improvement in PaO2, PaCO2, Vt, MAP or CO by itself
```

## Files changed

```text
core/bus.py
modules/pharmacology/pk_pd.py
modules/analgosedation/pain_stress_sedation.py
modules/respiratory/chemoreflex.py
modules/ventilator/ventilator.py
tests/test_v310_rocuronium_nmb_response_contract.py
VERSION
CHANGELOG.md
STEP3_5_ROCURONIUM_NMB_RESPONSE_REPORT.md
```

## Tests

Targeted validation:

```text
python -m py_compile core/bus.py modules/pharmacology/pk_pd.py modules/analgosedation/pain_stress_sedation.py modules/respiratory/chemoreflex.py modules/ventilator/ventilator.py
pytest tests/test_v310_rocuronium_nmb_response_contract.py
pytest tests/test_v309_alpha2_agonist_response_contract.py
pytest tests/test_v308_ketamine_response_contract.py
pytest tests/test_v307_gaba_sedative_response_contract.py
pytest tests/test_v306_opioid_response_contract.py
pytest tests/test_v305_vasoactive_response_contract.py
pytest tests/test_v304_drug_map_mod_direction.py
pytest tests/test_v303_drug_control_surface.py
pytest tests/test_v302_ui_backend_bidirectional.py
pytest tests/test_v301_ui_live_controls.py
pytest tests/test_v210_web_monitor.py
pytest tests/test_v260_ui_polish_tablet.py
pytest tests/test_v200_api_server.py
pytest tests/test_v220_emergency_training_mode.py
pytest tests/test_v230_instructor_mode.py
```

Result:

```text
53 passed
```

Additional legacy/smoke validation:

```text
pytest tests/test_v114_morphine_pkpd.py tests/test_public_smoke.py
```

Result:

```text
6 passed
```

## Remaining limitations

- This is still an educational qualitative model, not a validated PK/PD or NMBA
  monitor.
- It does not model TOF count, post-tetanic count, sugammadex/neostigmine,
  hepatic/renal detailed rocuronium clearance, or ICU-acquired weakness.
- Graphical monitor behavior and arterial waveform realism remain separate
  future steps.
