# PICUSim v3.2.0 public-polish validation notes

Status: local v3.2.0 public release-candidate, RC2.

This document is a validation-support note, not a claim of clinical validation. PICUSim remains an educational and research-prototyping simulator. It is not a medical device and is not for clinical use.

## Purpose of this validation layer

The v3.2.0 public-polish pass focuses on public-demo plausibility and regression safety. It does not attempt patient-specific prediction. The main goals are:

- keep a healthy child physiologically stable during room-air/PEEP demonstration;
- preserve visible therapeutic response to FiO2 and vasoactive interventions;
- prevent public scenarios from converging to repeated numeric ceilings such as PaCO2 = 105 mmHg or HR = 180/210/220 bpm;
- preserve severe physiology in shock, bronchiolitis, asthma, RDS, pneumothorax and excessive-PEEP scenarios;
- make public-package tests skip intentionally absent generated/release artifacts instead of failing.

## Golden scenario snapshot

The following values were generated locally with `dt=5.0` from the Step 5 v3.2.0 public-polish candidate.

| Scenario | Final SaO2 | Final PaCO2 | Final pH | Final HCO3 | Final HR | Final MAP | Final CO | Max PaCO2 | Max HR | Interpretation |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `healthy_child_20kg` | 94.0% | 43.6 | 7.35 | 24.0 | 109.7 | 70.4 | 4.58 | 58.7 | 128.5 | Pass: healthy-child demo no longer collapses after FiO2 0.21. |
| `neonatal_rds_3kg` | 96.5% | 62.3 | 7.20 | 24.0 | 215.6 | 43.8 | 0.75 | 81.9 | 215.6 | Pass with caution: severe neonatal tachycardia/hypercapnia preserved, no exact 220 ceiling. |
| `septic_shock` | 86.9% | 90.3 | 7.00 | 21.8 | 176.4 | 40.8 | 6.25 | 92.5 | 176.4 | Pass: distributive shock remains severe; old PaCO2/HR walls reduced. |
| `septic_shock_refractory` | 82.9% | 91.7 | 6.96 | 20.3 | 176.4 | 35.6 | 5.00 | 95.8 | 176.4 | Pass with caution: refractory physiology remains extreme. |
| `counterfactual_excessive_PEEP_ARDS` | 91.1% | 61.3 | 7.21 | 24.0 | 176.4 | 25.0 | 2.82 | 68.1 | 176.4 | Pass: excessive PEEP still depresses CO/MAP. |
| `epals_hyperkalemia_aki` | 99.4% | 36.0 | 7.33 | 18.9 | 175.8 | 49.7 | 7.50 | 38.7 | 176.3 | Pass: K baseline is preserved and improves after timeline interventions. |
| `epals_tension_pneumothorax` | 99.7% | 41.1 | 7.38 | 24.0 | 176.4 | 46.8 | 4.00 | 48.0 | 176.4 | Pass: obstructive-shock label and decompression response retained. |
| `near_fatal_status_asthmaticus` | 97.0% | 93.8 | 7.02 | 24.0 | 166.6 | 67.5 | 7.50 | 96.5 | 166.6 | Pass: severe hypercapnia retained without old 105 wall. |
| `infant_bronchiolitis` | 92.7% | 99.5 | 7.00 | 24.0 | 205.8 | 65.0 | 2.00 | 99.5 | 205.8 | Pass with caution: severe bronchiolitis remains extreme but no longer prints 105/210. |
| `epals_acidosis_septic_shock` | 85.1% | 86.3 | 6.91 | 17.0 | 176.4 | 37.8 | 5.50 | 89.5 | 176.4 | Pass with caution: combined respiratory/metabolic acidosis remains very severe. |

## RC2 external-review regression snapshot

The RC2 pass specifically rechecked independent-review findings from RC1.

| Scenario | RC1 concern | RC2 observed behavior | Status |
|---|---|---|---|
| `epals_v2_dka_dehydration_shock` | SaO2 collapsed to an implausible oxygen/Fick death spiral | SaO2 remains >=95%, PaCO2 remains compensatory/low, pH remains acidemic, K starts pathologic | Fixed for educational release use |
| `epals_tension_pneumothorax` | insufficient visible pre-decompression deterioration | SaO2/MAP/CO deteriorate before decompression and recover afterward | Fixed for teaching pattern |
| `epals_hyperkalemia_aki` | suspected K baseline overwrite | integrated scenario starts K >=6.5 and improves | Not reproduced as integrated bug; regression locked |
| `epals_acidosis_septic_shock` | suspected absent norepinephrine/MAP response | norepinephrine exposure is visible and MAP rises in the short simulation horizon | Not reproduced as absent response; regression locked |

## Regression tests added during v3.2.0 public-polish

Key public-polish regression files:

- `tests/test_v320_public_polish_contracts.py`
- `tests/test_v320_public_polish_deviation_contracts.py`
- `tests/test_v320_fio2_control_persistence.py`
- `tests/test_v320_public_package_regression_cleanup.py`
- `tests/test_v320_public_polish_soft_caps_contract.py`
- `tests/test_v320_public_polish_metadata_docs.py`
- `tests/test_v320_public_rc2_external_review_regressions.py`

## Current local targeted results

Targeted checks completed during Step 5:

- public smoke: 2 passed;
- v3.2 public-polish physiology contracts: 4 passed;
- v3.2 deviation contracts: 5 passed;
- FiO2 persistence contracts: 5 passed;
- public package regression cleanup: 5 passed;
- soft cap contracts: 4 passed;
- metadata/docs contracts: 4 passed;
- historical v3.1 metadata tests under v3.2 local candidate: 21 skipped;
- ETCO2/RR/shock/ScvO2/plausibility block: 17 passed, 1 skipped;
- API/UI/emogas/monitor block: 11 passed.

## Validation boundary

These checks are plausibility and regression safeguards. They do not establish diagnostic accuracy, dosing accuracy, patient-level prediction, device equivalence, or clinical efficacy.
