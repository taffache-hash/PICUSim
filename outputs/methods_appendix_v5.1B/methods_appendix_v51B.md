# Methods Appendix — Pediatric Critical Care Simulator v3.1

Generated: `2026-06-20T11:28:00Z`

## Scope and intended use
Educational and research-alpha simulator only; not a medical device, not a bedside decision tool and not validated for clinical diagnosis or treatment.

## Active model components
- pediatric profile scaling
- respiratory mechanics and gas-exchange surrogate
- shock engine
- advanced vasoactive engine
- intubation physiology
- organ perfusion model
- failure-to-rescue clock
- adaptive deterioration / recovery logic
- EPALS-like decision support layer
- scenario engine v2
- export and reproducibility pack

## Major modelling assumptions
- The model uses surrogate physiology rather than patient-specific mechanistic equations.
- Age/weight phenotype scaling is approximate and intended for training plausibility.
- Drug and vasoactive responses are directional and receptor-weighted, not individual PK/PD predictions.
- Critical-event timing is scenario-authored and designed for educational tempo.
- Recovery and deterioration are rule-based and constrained by plausibility guardrails.
- Displayed laboratory values are simulated trend surrogates, not diagnostic calculations.
- Biological extrema are clamped by an explicit v5.0C plausibility guardrail registry.
- Active model components are traceable to the repository model registry where present.

## Validation and audit artifacts
- `literature_benchmark_v5.0A`: pass=12, review=6
- `monte_carlo_v5.0B`: stable_runs=15, flagged_runs=0, scenarios=3
- `plausibility_guardrails_v5.0C`: missing in current checkout
- `scenario_solvability_v5.0D`: critical_findings=0, review_findings=0, playable=8, recoverable=8
- `ui_human_factors_v5.0E`: checks=23, pass=23, review=0, critical=0

## Scenario coverage
- Scenario manifest present: True
- Scenario count detected: 8

## Reproducibility controls
- Deterministic export bundle available from v5.1A.
- Session JSON, timeline CSV, intervention CSV, manifest hashes and structured Markdown are exportable.
- Seed metadata are recorded when supplied by the caller.

## Known limitations
- Not calibrated against individual patient data.
- Not externally validated as a clinical predictor.
- Not intended for dosing, diagnosis, triage or therapeutic decision-making.
- Literature benchmarks define broad corridors, not high-fidelity validation targets.
- User-interface audits are static/human-factors checks, not formal usability trials.
- Monte Carlo runs are robustness tests of simulated behavior, not evidence of clinical accuracy.

## Traceability files
### Tests
- `tests/test_v439_shock_engine_contract.py`
- `tests/test_v440_epals_decision_engine_contract.py`
- `tests/test_v441_intubation_physiology_contract.py`
- `tests/test_v442_organ_perfusion_contract.py`
- `tests/test_v443_advanced_vasoactive_engine_contract.py`
- `tests/test_v444_scenario_engine_v2_contract.py`
- `tests/test_v445_scenario_timing_trigger_contract.py`
- `tests/test_v446_failure_to_rescue_clock_contract.py`
- `tests/test_v448_recovery_engine_contract.py`
- `tests/test_v450_prevalidation_audit_contract.py`
- `tests/test_v451_monitor_layout_compression_contract.py`
- `tests/test_v500a_literature_benchmark_engine.py`
- `tests/test_v500b_monte_carlo_runner.py`
- `tests/test_v500c_plausibility_guardrails.py`
- `tests/test_v500d_scenario_solvability_audit.py`
- `tests/test_v500e_ui_human_factors_audit.py`
- `tests/test_v510a_export_reproducibility_pack.py`
- `tests/test_v51b_methods_appendix_generator.py`

### Documentation
- `docs/ADVANCED_VASOACTIVE_ENGINE_v3.1_step4.43.md`
- `docs/CODEX_HANDOFF_v3.1_step4.38_to_step4.39.md`
- `docs/CODEX_HANDOFF_v3.1_step4.39_to_step4.40.md`
- `docs/CODEX_HANDOFF_v3.1_step4.40_to_step4.41.md`
- `docs/CODEX_HANDOFF_v3.1_step4.41_to_step4.42.md`
- `docs/CODEX_HANDOFF_v3.1_step4.42_to_step4.43.md`
- `docs/CODEX_HANDOFF_v3.1_step4.43_to_step4.44.md`
- `docs/CODEX_HANDOFF_v3.1_step4.44_to_step5.0.md`
- `docs/CODEX_HANDOFF_v3.1_step4.46_to_step4.47.md`
- `docs/EPALS_DECISION_ENGINE_v3.1_step4.40.md`
- `docs/EXPORT_REPRODUCIBILITY_PACK_v5.1A.md`
- `docs/FAILURE_TO_RESCUE_CLOCK_v3.1_step4.46.md`
- `docs/FULL_PREVALIDATION_AUDIT_v3.1_step4.50.md`
- `docs/INTUBATION_PHYSIOLOGY_v3.1_step4.41.md`
- `docs/LITERATURE_BENCHMARK_ENGINE_v5.0A.md`
- `docs/MASSIVE_MONTE_CARLO_v5.0B.md`
- `docs/METHODS_APPENDIX_GENERATOR_v5.1B.md`
- `docs/MONITOR_LAYOUT_COMPRESSION_v3.1_step4.51.md`
- `docs/ORGAN_PERFUSION_MODEL_v3.1_step4.42.md`
- `docs/PLAUSIBILITY_GUARDRAILS_v5.0C.md`
- `docs/RECOVERY_ENGINE_v3.1_step4.48.md`
- `docs/SCENARIO_ENGINE_V2_v3.1_step4.44.md`
- `docs/SCENARIO_SOLVABILITY_AUDIT_v5.0D.md`
- `docs/SCENARIO_TIMING_TRIGGER_v3.1_step4.45.md`
- `docs/SHOCK_ENGINE_v3.1_step4.39.md`
- `docs/UI_HUMAN_FACTORS_AUDIT_v5.0E.md`

## Safety statement
This appendix supports transparent reporting of a research-alpha educational simulator. This is not clinical validation and must not be interpreted as clinical validation.