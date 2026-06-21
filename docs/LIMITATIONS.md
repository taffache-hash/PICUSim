# PICUSim limitations and safety boundary

Status: local v3.2.0 public release-candidate, RC2.

PICUSim is an educational and research-prototyping simulator. It is not a medical device, not clinically validated, not patient-specific and not for clinical use.

## Non-clinical use only

Do not use PICUSim outputs for:

- diagnosis;
- treatment decisions;
- drug prescribing or dose calculation;
- triage;
- bedside monitoring;
- prognostication;
- ventilator/device control;
- patient-specific prediction;
- any real patient-care decision.

## Model limitations

PICUSim uses simplified, semi-mechanistic and heuristic physiology. Many variables are proxy indices rather than directly validated biological measurements. Couplings between organ systems are qualitative and scenario-calibrated.

Major limitations include:

- simplified gas exchange and V/Q representation;
- simplified cardiovascular scaling and baroreflex behavior;
- qualitative sepsis, cytokine, vasoplegia and microcirculation dynamics;
- proxy pharmacology and drug-response modules, not dosing calculators;
- simplified renal, hepatic, coagulation, endocrine, thermoregulation and neurological modules;
- scenario-specific calibration for educational behavior;
- no external prospective validation;
- no guarantee of accuracy across ages, weights, pathologies, devices or drugs.

## v3.2.0 public-polish limitations

The v3.2.0 public-polish pass corrected several public-demo problems, including healthy-child instability, FiO2 persistence across oxygen interfaces, short-scenario norepinephrine visibility in sepsis, electrolyte-baseline robustness, release-package test hygiene and visible PaCO2/HR numerical walls.

These corrections improve educational plausibility. They do not convert the model into a clinically validated simulator.

## Scenario limitations

Some scenarios are intentionally extreme. For example, refractory septic shock, near-fatal asthma, bronchiolitis and combined septic acidosis scenarios may produce severe acidemia, hypercapnia, tachycardia, hypotension or oxygenation abnormalities. These scenarios are designed for teaching pattern recognition and debriefing, not for bedside reference ranges.

## Interpretation rule

Treat every output as a simulated educational signal. If a value appears physiologically implausible, use it as a model-inspection finding, not as a clinical assertion.
