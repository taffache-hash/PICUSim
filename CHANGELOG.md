## v3.1 Step 6.0 - Public archive release metadata

- Recorded Zenodo DOI `10.5281/zenodo.20777589` after successful GitHub-Zenodo archival release.
- Added `docs/PUBLIC_ARCHIVE_RELEASE_v6.0.md`.
- Updated README, first-start notes, CFF/BibTeX citation metadata and Zenodo metadata with the DOI.
- OSF assembly and manuscript data/code availability updates remain deferred.
## v3.1 Step 5.9 - Final public release candidate rebuild

- Rebuilt the clean final public-release candidate archive locally after Step 5.8 preflight.
- Added `data/release_candidate_manifest_v5.9.yaml` and `docs/FINAL_RELEASE_NOTES_v5.9.md`.
- Updated package-facing version and citation/deposition metadata to `3.1-step5.9-final-public-release-candidate`.
- Added `tests/test_v590_final_release_archive.py` to verify archive existence, checksum, required entrypoints and exclusion of caches/logs/nested zip files.
- No GitHub, Zenodo or OSF upload was performed.
## v3.1 Step 5.8 - Archive preflight and manifest rebuild

- Regenerated package facts from the filesystem/tests instead of manuscript or paper text.
- Added `metadata/package_facts_v5.8.json` and `data/release_candidate_manifest_v5.8.yaml`.
- Added `docs/ARCHIVE_PREFLIGHT_v5.8.md` with deposit-first/paper-last checks and archive exclusion rules.
- Marked the Step 5.6 Zenodo candidate archive as superseded after Step 5.6A and Step 5.7A changes; it must not be uploaded.
- Updated README, citation metadata, OSF local artifact index and tests to the archive-preflight release-candidate label.
- No GitHub, Zenodo or OSF upload was performed.
## v3.1 Step 5.7A - Paper deferred / archive-preflight correction

- Corrected roadmap ordering so manuscripts/papers are deferred until after public deposit identifiers exist.
- Updated OSF and Zenodo planning documents to state that paper drafts are not authoritative for scenario/module/drug/test/validation counts.
- Replaced the old Step 5.8 manuscript pass with archive preflight and manifest rebuild.
- Added `docs/PAPER_DEFERRED_ARCHIVE_FIRST_v5.7A.md`.
- Updated README and first-start notes with the rule: deposit first, paper last.

## v3.1 Step 5.7 - OSF project preparation

- Added `docs/OSF_PROJECT_PLAN_v5.7.md` with OSF component layout, upload order, boundary decisions and open public-deposition decisions.
- Added `metadata/osf_project_structure_v5.7.md`.
- Added `metadata/osf_artifact_index_v5.7.json` and `metadata/osf_artifact_index_v5.7.csv`.
- Updated version/readme metadata to `3.1-step5.7-osf-project-prepared`.
- No OSF project was created and no upload was performed.
- Final archive/manifest regeneration remains required after the Step 5.6A deviation and before public upload.

## v3.1 Step 5.6A - Crystalloid infusion controls

- Added user-controlled crystalloid/fluid infusion support: saline, Ringer lactate, Sterofundin and 5% dextrose.
- Added `set_crystalloid_type` and `set_crystalloid_rate` API actions with control-state round-trip.
- Routed crystalloid rate through `FluidBalanceModule` in mL/h with bounded responsiveness, MAP/CO support markers, renal perfusion/urine markers, chloride/balanced-fluid audit markers and glucosata-to-GIR support.
- Added a compact main-page `Flebo` panel and a `Fluids / crystalloids` section in the infusions panel.
- Added `docs/CRYSTALLOID_INFUSION_CONTROLS_v5.6A.md` and `tests/test_v56a_crystalloid_fluids_contract.py`.
- The previously generated Step 5.6 Zenodo candidate archive is now stale and must be regenerated before any final public upload.

## v3.1 Step 5.6 - Zenodo deposition preparation

- Added `docs/ZENODO_DEPOSITION_PLAN_v5.6.md` with deposit scope, exclusions, open upload decisions and archive details.
- Added `metadata/zenodo_metadata_v5.6.yaml` and `.zenodo.json` draft metadata.
- Updated `VERSION`, `pyproject.toml`, `CITATION.cff`, `CITATION.bib`, `README.md`, and `README_FIRST_START_HERE.txt` to the Zenodo-ready release-candidate label.
- Built candidate archive `outputs/release_archives/pediatric_critical_care_sim_v3.1_step5.6_zenodo_candidate.zip` and SHA256 checksum file.
- Added `tests/test_v560_zenodo_deposition_preparation.py`.
- Actual Zenodo upload, DOI assignment, OSF links and manuscript related identifiers remain pending.

## v3.1 Step 5.5 - Apache-2.0 licensing conversion

- Added `LICENSE` with Apache License 2.0 text and project copyright boilerplate.
- Added `NOTICE` with project attribution and explicit non-clinical safety notice.
- Updated `VERSION`, `pyproject.toml`, `CITATION.cff`, `CITATION.bib`, `README.md`, and `README_FIRST_START_HERE.txt` for Apache-2.0 release-candidate status.
- Superseded `LICENSE_PENDING.md` while retaining it as provenance.
- Added `docs/APACHE_LICENSE_CONVERSION_v5.5.md` and `tests/test_v550_apache_license_conversion.py`.
- Zenodo, OSF, manuscript DOCX cleanup and final manifest regeneration remain reserved for Steps 5.6-5.9.

## v3.1 Step 5.4 - Documentation and version coherence cleanup

- Updated package-facing version and metadata after the Step 5.3 regression sweep.
- Refreshed `README_FIRST_START_HERE.txt`, `README.md`, `CITATION.cff`, `CITATION.bib`, `LICENSE_PENDING.md`, and `pyproject.toml` for the current release-candidate state.
- Added `docs/DOCUMENTATION_COHERENCE_AUDIT_v5.4.md` documenting completed cleanup and deferred publication tasks.
- Added `tests/test_v540_documentation_coherence.py` to lock entrypoint metadata, pending-license wording, and deferred Zenodo/OSF/manuscript/manifest work.
- Apache-2.0 licensing, Zenodo, OSF, manuscript DOCX cleanup and manifest regeneration remain reserved for Steps 5.5-5.9.

## v3.1 Step 5.3 - Release candidate regression sweep

- Added `docs/REGRESSION_SWEEP_v5.3.md` with the first targeted release-candidate regression sweep results.
- Added `outputs/regression_sweep_v5.3/regression_summary_v53.json` for machine-readable sweep summary.
- Executed targeted public/API/UI/RC, Step 4.39-4.51 advanced engine, UI/RCP/arrhythmia and Step 5.0A-5.1D validation-pack contract sweeps.
- Fixed Windows CLI smoke portability by replacing Unicode terminal progress markers in `core/engine.py` with ASCII-safe output.
- Current targeted sweep result after hotfix: 126 passed, 0 failed.
- Remaining Step 5.4 cleanup findings: `VERSION`, `README_FIRST_START_HERE.txt`, `pyproject.toml` and manuscript metadata/version alignment.

## v3.1 Step 5.0E — UI human factors audit v2

- Added `data/ui_human_factors_audit_v5.0E.yaml` defining static human-use audit gates for the console.
- Added `tools/ui_human_factors_audit_v5_0E.py` to verify DOM target completeness, monitor layout compression, click density, numeric prominence and core JS target resolution.
- Added `tests/test_v500e_ui_human_factors_audit.py`.
- Added `docs/UI_HUMAN_FACTORS_AUDIT_v5.0E.md`.
- Generated `outputs/ui_human_factors_v5.0E/` with CSV, summary JSON and Markdown report.
- Current handoff audit: 23 checks, 23 pass, 0 review findings, 0 critical findings.


## v3.1 Step 5.0D — Scenario solvability audit

- Added `data/scenario_solvability_audit_v5.0D.yaml` defining playability, recoverability, fail-ability, non-determinism and debriefability gates.
- Added `tools/scenario_solvability_audit_v5_0D.py` over the curated Step 4.44 EPALS scenario-engine v2 manifest.
- Added `tests/test_v500d_scenario_solvability_audit.py`.
- Added `docs/SCENARIO_SOLVABILITY_AUDIT_v5.0D.md`.
- Generated `outputs/scenario_solvability_v5.0D/` with CSV, summary JSON and Markdown report.
- Current handoff audit: 8 scenarios audited, 8 playable, 8 recoverable, 8 fail-able, 8 non-deterministic, 0 critical findings, 0 review findings.


## v3.1 Step 5.0C — Plausibility guardrails

- Added `data/plausibility_guardrails_v5.0C.yaml` with critical biological bounds, scenario-specific soft bounds and logical consistency rules.
- Added `tools/plausibility_guardrails_v5_0C.py` audit runner over Monte Carlo/benchmark-style output tables.
- Added `tests/test_v500c_plausibility_guardrails.py`.
- Added `docs/PLAUSIBILITY_GUARDRAILS_v5.0C.md`.
- Generated `outputs/plausibility_guardrails_v5.0C/` with findings CSV, summary JSON and Markdown report.
- Current handoff audit: 15 rows audited, 0 critical findings, 0 review findings, guardrails passed.


## v3.1 Step 5.0B — Massive Monte Carlo stress runner

- Added `data/monte_carlo_specs_v5.0B.yaml` for randomized in-silico robustness testing across core benchmark scenarios.
- Added `tools/monte_carlo_runner_v5_0B.py` with deterministic seed, per-scenario random draws, plausibility flags and aggregate summaries.
- Added `tests/test_v500b_monte_carlo_runner.py`.
- Added `docs/MASSIVE_MONTE_CARLO_v5.0B.md`.
- Generated `outputs/monte_carlo_v5.0B/` with results CSV, draw trace CSV, scenario summaries, JSON summary and Markdown report.
- Current compact handoff run: 15 runs, 15 stable, 0 flagged.


## v3.1 Step 5.0A — Literature benchmark engine

- Added `data/literature_benchmark_targets_v5.0A.yaml` with source-traceable broad physiological corridors.
- Added `tools/literature_benchmark_engine_v5_0A.py` for reproducible PASS/REVIEW/NO_DATA benchmark evaluation.
- Added `tests/test_v500a_literature_benchmark_engine.py`.
- Added `docs/LITERATURE_BENCHMARK_ENGINE_v5.0A.md`.
- Generated `outputs/literature_benchmark_v5.0A/` with source matrix, results CSV, summary JSON and Markdown report.
- Current full 5.0A benchmark result: 18 checks, 12 PASS, 6 REVIEW, 0 NO_DATA, 0 missing source rows.


## v3.1 Step 4.51 — Monitor layout compression

- Reworked bedside monitor layout to prioritise large numeric vital values over decorative waveforms.
- Moved HR, SpO2, MAP/ABP, PaCO2/EtCO2, Paw and FiO2 into a vertical side column adjacent to the waveform stack.
- Compressed ECG, pleth, ABP and Paw/Capno waveform rows to reduce screen dominance.
- Preserved all existing vital ids and trend canvas ids for UI compatibility.
- Added regression contract: `tests/test_v451_monitor_layout_compression_contract.py`.


## 3.1-step4.50-full-prevalidation-audit

- Added full pre-5.0 validation/audit report for engine/API/UI/scenario readiness.
- Added static human-style UI audit checks for missing DOM targets and core visible controls.
- Added scenario smoke audit coverage for Step 4.44 EPALS v2 scenarios.
- Fixed hyperkalemia/AKI v2 scenario blocker by adding `calcium_given` marker support to BusState and scenario action mapping.
- Added `tests/test_v450_prevalidation_audit_contract.py`.
- Targeted audit suite result: 59 passed.


## v3.1 step4.48 — Recovery engine

- Added `core/recovery_engine.py` with phenotype-specific recovery presets.
- Added delayed recovery perturbations anchored to the first corrective action after the critical trigger.
- Added recovery metadata for first response, partial response and near-baseline time.
- Added multiplier perturbation support in `core/engine.py` for audited recovery effects.
- Added recovery fields to `BusState`.
- Added `docs/RECOVERY_ENGINE_v3.1_step4.48.md`.
- Added contract tests for recovery timing, loader integration and multiplier application.

## v3.1 Step 4.46 — Failure-to-rescue clock

- Added `core/failure_to_rescue.py` with explicit golden-window, reversibility-threshold and point-of-no-return metadata.
- Added phenotype-based default windows for septic shock, anaphylaxis, tamponade, tension pneumothorax, bronchiolitis failure, hyperkalemia, status epilepticus, TBI/ICP crisis and DKA shock.
- Added optional deterministic late-deterioration perturbations after the critical window closes.
- Exposed `ScenarioLoader.failure_to_rescue_info` and integrated the late-deterioration perturbation hook.
- Updated Streamlit preview to show failure-to-rescue timing separately from real/virtual scenario duration.
- Added documentation and targeted Step 4.46 contract tests.

Validation: `tests/test_v445_scenario_timing_trigger_contract.py` + `tests/test_v446_failure_to_rescue_clock_contract.py` — 6 passed.

## v3.1 Step 4.44 — Scenario engine v2

- Added `ScenarioEngineV2Catalog` and lightweight scenario manifest validation.
- Added eight EPALS-oriented v2 scenario files: septic shock, anaphylaxis, tamponade, hyperkalemia/AKI, status epilepticus, TBI/ICP crisis, DKA-like dehydration shock and bronchiolitis respiratory failure.
- Added scenario-level `shock:` and `neuro:` initialization hooks to `ScenarioLoader`.
- Added Step 4.44 documentation, Codex handoff to Step 5.0 and targeted contract tests.

Validation: `tests/test_v444_scenario_engine_v2_contract.py` — 3 passed.


## v3.1 Step 4.43 — Advanced vasoactive engine

- Added receptor-weighted vasoactive audit signals for alpha-1, beta-1, beta-2, V1 and PDE3 activity.
- Added first-order infusion hysteresis for norepinephrine, epinephrine, dopamine, milrinone and vasopressin.
- Added exposure-dependent tachyphylaxis and mixed pressor/inodilator interaction indices.
- Preserved previous Step 3.3 monotonic vasoactive response contracts while exposing effective-dose audit fields.

Validation: targeted Step 4.43 contract tests added.

## 3.1-step4.38-codex-roadmap-handoff

## 3.1-step4.41-intubation-physiology

- Added `IntubationPhysiologyModule`, a bounded educational peri-intubation physiology layer.
- Added Bus fields for preoxygenation reservoir, apnea timer, safe-apnea reserve proxy, RSI suppression, desaturation risk/slope, phase and warning.
- Couples existing airway actions/flags with FiO2, ventilation quality, NMB/sedation signals, obstruction and aspiration risk.
- Applies a bounded SaO2/PaO2 downward trajectory during apnea and slow recovery during effective high-FiO2 ventilation.
- Added `docs/INTUBATION_PHYSIOLOGY_v3.1_step4.41.md`, Codex handoff to Step 4.42 and `tests/test_v441_intubation_physiology_contract.py`.

## 3.1-step4.40-epals-decision-engine

- Added `EPALSDecisionModule`, a bounded educational ABCDE/pattern-recognition layer.
- Added Bus decision fields for priority, pattern, confidence, contextual prompts, warnings and escalation marker.
- Detects cardiac arrest, severe hypoxemia/unsecured airway, shock, hyperkalemia, hypoglycemia and hypercarbic failure branches.
- Adds incoherence warnings for arrest without CPR marker, hypoxemia with disconnected ventilator, septic/distributive shock without antibiotic flag, and selected shock-action mismatches.
- Added `docs/EPALS_DECISION_ENGINE_v3.1_step4.40.md`, Codex handoff to Step 4.41 and `tests/test_v440_epals_decision_engine_contract.py`.

## 3.1-step4.39-shock-engine

- Added `ShockModule` with bounded distributive, hypovolemic, cardiogenic, obstructive and mixed shock phenotype modifiers.
- Added Bus shock fields for severity, stage, SVR/preload/contractility/HR/lactate coupling and phenotype indices.
- Coupled shock modifiers into Circulation, Baroreflex, Heart and Metabolism ownership paths without changing final variable ownership.
- Added shock engine documentation, YAML contract spec and targeted contract tests.


- Added a Codex handoff roadmap after `3.1-step4.38-vasoactive-infusion-feedback-hotfix`.
- Updated `docs/PCCSIM_V3_1_PHARMACOLOGY_AND_UI_ROADMAP.md` with the proposed continuation sequence from Step 4.39 to Step 4.44.
- Added `docs/CODEX_HANDOFF_v3.1_step4.38_to_step4.39.md` with the exact next Codex prompt and implementation boundaries.
- No code, model, physiology, UI behavior or test changes in this handoff package.

## 3.1-step4.19-time-speed-telemetry

- Added compact simulated-time, wall-clock, and effective speed telemetry beside session metadata.
- Tracks wall elapsed time across Start/Pause and resets on Load/Reset/Load saved.
- Keeps existing speed input as the control while making actual progression visible.
- Added `tests/test_v337_time_telemetry_contract.py`.
## 3.1-step4.18-always-visible-labs-strip

- Added an always-visible rotating labs strip below the bedside monitor header.
- Rotates four parameters at a time every 8 seconds across lactate, glucose, K, Na, Hb, creatinine, bilirubin, GCS/RASS proxies, ICP, CVP, DO2, and urine output.
- Reuses cached full-profile state and throttles refresh to at most every 8 seconds while a session is active.
- Added `tests/test_v336_labs_strip_contract.py`.
## 3.1-step4.17-ui-human-pass-polish

- Added an always-visible session state pill: not loaded, working, running, paused, or error.
- Wired session action pending/error feedback into that state pill.
- Audio ON now emits an immediate confirmation cue when the browser audio context starts.
- Verified load/start/pause/step/intubate workflow via local API.
- Added `tests/test_v335_ui_human_pass_contract.py`.
## 3.1-step4.16-audio-session-button-state

- Added unified pressed/pending/confirmed/error button states for session controls.
- `Start` remains active while running; `Pause` remains active when loaded but not running.
- Added UI confirmation/error audio cues when monitor audio is enabled.
- Updated audio badge to show SAT+ECG+UI.
- Added `tests/test_v334_audio_session_button_state_contract.py`.


## 3.1-step4.15-hf4-monitor-benchmark-tau

- Fixed extended monitor stale UI keys and added full-state aliases for display compatibility.
- Retained visible 10-minute sparkline UI while satisfying legacy CSS contract markers.
- Corrected neonatal RDS benchmark scenario as treated/stabilized ventilator optimization.
- Added runtime tau guards for renal AKI and sepsis resolution time constants.
- Added `tests/test_v333_hf4_corrections_contract.py`.

## v3.1 step4.15 - emogas full profile autorefresh

- Fixes Emogas panel showing only bedside-fast fields while the tab is open.
- Emogas and Monitor esteso now fetch `/session/{id}/state?profile=full` immediately and every 2.5 seconds while open.
- Bedside WebSocket updates no longer make the Emogas panel look complete when the full snapshot is still missing.
- Keeps backend/engine unchanged.


## v3.1 Step 4.5 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Scenario info card
- Added a bedside scenario brief card with patient/context metadata.
- Uses `/scenarios` metadata already available to the UI.


## v3.1 Step 4.4 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Visual threshold alarms
- Added visual warning/critical bedside alarm states for HR, SpO2, MAP, CO2, Paw, and FiO2.
- No audio and no backend change.


## v3.1-step4.3 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Control pending/confirmed feedback

- Added visual pending/confirmed/error states for live UI controls.
- Drug and ventilator inputs now show immediate feedback after a change.
- Confirmation occurs when the backend control value returns through the bedside controls profile.
- No physiology or backend changes.

## v3.1-step4.1C ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Requested popup charts

- Added a manual popup chart modal opened from Monitor esteso.
- Charts are generated only on request; no new WebSocket and no continuous polling.
- Bedside charts use the existing light trend buffer; extended charts use manual monitor snapshots.
- Added first chart set: MAP, SpOÃƒÂ¢Ã¢â‚¬Å¡Ã¢â‚¬Å¡, PaCOÃƒÂ¢Ã¢â‚¬Å¡Ã¢â‚¬Å¡/EtCOÃƒÂ¢Ã¢â‚¬Å¡Ã¢â‚¬Å¡, HR, Paw, lactate, urine output, fluid balance, DOÃƒÂ¢Ã¢â‚¬Å¡Ã¢â‚¬Å¡/VOÃƒÂ¢Ã¢â‚¬Å¡Ã¢â‚¬Å¡, glucose.

## v3.1-step4.1B ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Extended monitor v2 snapshot-only

- Expanded Monitor esteso from 5 to 11 collapsible blocks.
- Converted extended monitor to manual snapshot refresh only; no polling and no additional WebSocket.
- Added coagulation/hematology, hepatic, infection/sepsis, advanced ventilation, drug concentration, and nutrition/catabolism sections.
- Kept the main bedside stream light and unchanged.
# Changelog

## v3.1-step4.1A ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Extended monitor panel

- Added a request-only `Monitor esteso` apparatus panel for single-screen use.
- Grouped calculated/secondary Bus variables into five blocks: hemodynamics/perfusion, respiratory, metabolic/labs, neurologic/sedation, and renal/fluid.
- The panel fetches the existing `full` state profile only while open and falls back to the bedside stream when needed, avoiding high-frequency full-Bus streaming.
- Added client-side derived ScvO2 display when SaO2, VO2, CO and Hb are available; this is a UI-derived value until the later engine-level ScvO2 step.
- Added targeted UI/API contract tests in `tests/test_v317_extended_monitor_panel_contract.py`.

# v3.1-step4.0B ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Real EtCO2 monitor coupling

- Replaced fixed `EtCO2_proxy = PaCO2 - 5` waveform/profile behavior with model-coupled `EtCO2`.
- Added EtCO2 computation inside `GasExchangeModule`, coupled to PaCO2/effective alveolar ventilation, V/Q dead-space burden, shunt/dispersion and low-CO perfusion attenuation.
- Added Bus audit variables: `EtCO2`, `EtCO2_proxy`, `etco2_pa_gradient`, `etco2_perfusion_factor`, `etco2_deadspace_factor`, and `etco2_source`.
- Preserved the legacy `EtCO2_proxy` key as an alias for compatibility with older waveform clients.
- Updated bedside/waveform/debug profiles and UI monitor to display/consume real `EtCO2`.
- Added `tests/test_v316_etco2_model_coupling_contract.py`.

# CHANGELOG ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â v3.1 Step 4.0A ABP/SBP-DBP monitor coupling

## Changed

- Skipped antibiotic revision by user request; antibiotics remain a marginal/backlog item.
- Exposed bedside `SBP`/`DBP` aliases from model arterial pressure outputs instead of relying on `MAP Ãƒâ€šÃ‚Â± constants` in UI profiles.
- Updated `CirculationModule` to publish `SBP`, `DBP`, `arterial_pulse_pressure` and `arterial_pressure_source` from the circulation pressure envelope.
- Updated API bedside and waveform profiles to prefer model `SBP`/`DBP`/`SAP`/`DAP` values.
- Updated ABP canvas waveform to draw from real `SBP`/`DBP` values instead of a cosmetic MAP-centered amplitude.
- Added a small ABP `SBP/DBP` readout under the MAP vital.
- Added the user-supplied monitor/UI roadmap items to the project roadmap.

## Tests

- Added `tests/test_v315_abp_windkessel_monitor_contract.py`.
- Syntax checks passed for Python modules and UI JavaScript.
- Targeted regression group executed: 76 passed.

## Limitations

- `EtCO2_proxy` is still the old PaCO2-minus-constant proxy; real EtCO2 is queued as Step 4.0B.
- No labs strip, sparkline trend, alarm thresholds, scenario card, or time-speed indicator implemented in this step.
- This step does not redesign the full UI layout; it only fixes ABP numerical/waveform consistency.

# CHANGELOG ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â v3.1 Step 3.9 insulin/glucose/potassium response contract

## Changed

- Made insulin a delayed PK/PD-mediated intervention rather than a raw command directly consumed by downstream physiology.
- Kept `PharmacologyModule` as owner of insulin concentration and effect-site signals.
- Kept `GlucoseModule` as sole owner of final `glucose_mmol_L`.
- Kept `AcidBaseElectrolyteModule` as sole owner of final `K_mmol_L`.
- Replaced immediate raw-insulin effects in endocrine stress and nutrition/refeeding logic with delayed insulin action signals.
- Added safety factors that taper insulin glucose clearance near hypoglycemia and potassium shift near hypokalemia.
- Added insulin audit outputs to the debug profile for the future calculated-parameters window.

## Tests

- Added `tests/test_v314_insulin_glucose_potassium_contract.py`.
- Targeted test groups executed: 76 passed.
- UI syntax check: `node --check ui/app.js` passed.

## Limitations

- No antibiotic revision in this step.
- No all-drug window or calculated-parameter window implemented yet; those remain Step 4.x UI tasks.
- No arterial waveform/monitor redesign yet.

# CHANGELOG ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â v3.1 Step 3.8 furosemide/fluid-balance response contract

## Changed

- Removed raw cumulative furosemide counter as a direct driver of final urine output.
- Kept `PharmacologyModule` as owner of furosemide concentration/effect-site signal.
- Kept `AKICRRTModule` as renal-adjusted audit signal owner through `diuretic_response_index`.
- Kept `FluidBalanceModule` as sole owner of `urine_rate_mL_h`, cumulative urine and final `fluid_balance`.
- Added furosemide audit outputs for effective diuretic signal, urine gain, extra urine rate and hypovolemia risk.
- Added roadmap note for later UI windows covering all drugs and hidden calculated parameters.

## Tests

- Added `tests/test_v313_furosemide_fluid_balance_contract.py`.
- Targeted pharmacology/renal contract group: 52 passed.
- API/smoke/furosemide legacy group: 19 passed.

## Limitations

- No insulin or antibiotic revision in this step.
- No all-drug window or hidden-calculated-parameter window yet.
- No arterial waveform/monitor redesign yet.

# CHANGELOG ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â v3.1 Step 3.5 rocuronium/NMB response contract

## Changed

- Separated rocuronium from analgosedation: neuromuscular blockade is no longer counted as sedation or respiratory sedation.
- Kept rocuronium's respiratory effect in a single `drug_NMB_frac` pathway consumed by ChemoreflexModule.
- Made spontaneous/assisted RR follow the post-pharmacologic motor-output target so high NMB suppresses effective spontaneous effort.
- Added explicit NMB audit outputs: `rocuronium_nmb_signal`, `neuromuscular_blockade_active`, `spontaneous_effort_available`, and `nmb_trigger_block_active`.
- Documented that rocuronium blocks effort/triggering but does not improve gas exchange by itself.

## Tests

- Added `tests/test_v310_rocuronium_nmb_response_contract.py`.
- Targeted suite: 53 passed.
- Additional legacy/smoke group: 6 passed.

## Limitations

- No TOF/PTC/sugammadex/neostigmine model yet.
- No change to graphical monitor curves, Docker packaging or non-NMBA drugs in this step.

# Changelog

## v3.1-step3.4D-alpha2-agonist-response-contract ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Dexmedetomidine/clonidine response cleanup

- Keeps alpha-2 agonists out of `drug_drive_mod`, avoiding duplicate respiratory-drive depression.
- Keeps alpha-2 HR/SVR coupling in `PainStressSedationModule` via `sed_HR_mod`/`sed_SVR_mod`, avoiding duplicate `drug_HR_mod`/`drug_SVR_mod` suppression.
- Adds audit signals for dexmedetomidine sedation, dexmedetomidine sympatholysis, bradycardia/hypotension risk, combined alpha-2 sedation and sympatholysis.
- Preserves clonidine withdrawal-modulation signal and slow qualitative PK/PD behavior.
- Adds v3.1 Step 3.4D regression tests for dose-response, preserved respiratory drive, and no double-counting.

## v3.1-step3.4B-gaba-sedative-response-contract ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Midazolam/propofol response cleanup

- Keeps GABA sedative respiratory-drive depression in `drug_drive_mod` instead of duplicating it through `sed_resp_mod`.
- Adds audit signals for midazolam sedation, propofol sedation, propofol vasodilation, combined GABA sedation and sedative drive depression.
- Preserves `sed_resp_mod` for opioids and non-GABA respiratory modifiers so opioid Step 3.4A behavior remains intact.
- Adds v3.1 Step 3.4B regression tests for dose-response, no double respiratory depression and propofol hemodynamic signal.

## v3.1-step2-ui-bidirectional ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â UI/backend control round-trip

- Adds a compact `controls` state projection for command values such as FiO2, PEEP, RR and currently routed drug infusions.
- Adds `/session/{id}/state?profile=controls` for explicit control-state inspection.
- Mirrors backend command values back into bedside and bedside_fast payloads.
- Updates the web UI to resynchronise sliders and drug inputs from backend state without overwriting an active edit.
- Adds v3.1 Step 2 regression tests for API round-trip and UI sync hooks.

## v3.0-alpha ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Packaging and distribution hardening

- Adds Dockerfile, docker-compose.yml and .dockerignore for easier local deployment.
- Rewrites public README around installation, Docker, safety and distribution status.
- Updates package metadata to v3.0-alpha.
- Adds Docker quickstart, installation guide, release notes and distribution checklist.
- Removes generated cache artifacts from the distributable source bundle.

## v2.7-alpha ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Scenario authoring assistant

- Added template-based scenario authoring from the web console.
- Added authoring API endpoints for templates, draft, validation, save, and listing.
- Added YAML editor panel with validate/save/load workflow.
- Added audit and tests for authored scenarios.

# v2.5-alpha ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Session save/load + export report

- Added portable JSON session save bundles.
- Added Markdown session report export.
- Added `/session/{id}/export`, `/session/{id}/save`, and `/session/load_saved`.
- Added GUI buttons for save/export/load-saved.
- Added action-replay based restoration.
- Added session export audit and v2.5 regression tests.

# Changelog

## v2.4-alpha
- Console performance hardening and one-command launcher.
- Fast profiles and bounded history for smoother web monitor use.

## v2.3-alpha

- Added instructor-mode presets, notes/bookmarks, diagnosis concealment, and instructor report export.
- Integrated the instructor panel into the lightweight web monitor.

# v2.0-alpha ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Clinical Training API

- Added clean FastAPI backend with in-memory sessions.
- Added compact state profiles and WebSocket streams for future browser UI integration.
- Added action router for selected ventilator, drug, oxygen, and airway-event actions.
- Added `start_pdt_api.py` and API documentation.

# v1.25-alpha ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Airway decision scenario pack

Added six executable airway decision scenarios using the v1.24 airway-event system: failed airway/cannot oxygenate, extubation failure, post-extubation laryngospasm, aspiration during RSI, opioid/sedative apnea rescue, and NIV failure to intubation. Added scenario pack metadata, audit tool, docs and tests.

# v1.24-alpha ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Airway intubation/extubation event system

Added airway event layer, two airway decision scenarios, audit and tests.


## v1.23.3-alpha
- Added artificial-airway ETT/tracheostomy resistance, dead-space, cuff-leak and obstruction scaffold.


## v1.23.2-alpha

- Added NIV CPAP/BiPAP educational interface scaffold.
- Added mask-leak, delivered-pressure, oxygen-delivery and qualitative failure-risk proxies.
- Added two non-invasive ventilation scenarios and audit/test support.

## v1.23.1-alpha ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Oxygen delivery / HFNC base

- Added low-flow oxygen, simple-mask and HFNC interface behavior.
- Added effective FiO2 delivery, HFNC distending-pressure and dead-space washout proxies.
- Added two oxygen-interface scenarios and regression/audit coverage.


## v1.23-alpha ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Airway interface model base

- Added explicit airway-interface state fields to the physiological bus.
- Added `AirwayInterfaceModule` for public educational interface metadata.
- Added ventilator modes `NONE` and `UNASSISTED` for spontaneous breathing without active ventilator pressure.
- Added one smoke scenario for unassisted spontaneous breathing.
- Added audit and tests for the airway-interface base layer.


## v1.22.1-alpha ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â EPALS 5H scenario pack

- Added five executable EPALS H-cause scenarios.
- Added audit and test coverage for scenario loading, smoke runs and key physiological markers.
- No engine changes.


## v1.20-alpha ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Adaptive V/Q Dispersion

- Added pathology-adaptive V/Q dispersion for ARDS-like derecruitment, obstructive disease, sepsis/shock and neonatal/RDS-like physiology.
- Added explicit V/Q driver audit fields and a compact validation tool.
- Added tests and documentation for the v1.20 gas-exchange refinement.

## v1.17-alpha ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Piperacillin/Tazobactam PK/PD scaffold

- Added piperacillin/tazobactam as the 15th centralized PharmacologyModule drug.
- Added renal-function-dependent piperacillin PK, CRRT-lite clearance and qualitative fT>MIC target-attainment outputs.
- Added antimicrobial coverage coupling for time-dependent beta-lactam effect.
- Added infection scenario, audit tool, documentation and regression tests.

## v1.16-alpha ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Insulin / Glucose PD scaffold

- Added insulin as the 14th PharmacologyModule drug.
- Added delayed insulin concentration proxy `C_insulin_mU_L`.
- Added qualitative glucose-clearance, potassium-shift and hypoglycemia-risk signals.
- Connected `GlucoseModule` to the central insulin PK/PD signal with legacy fallback.
- Connected acid-base/electrolyte potassium shift to the central insulin signal.
- Added insulin stress-hyperglycemia scenario, audit tool, documentation and regression tests.

## v1.14-alpha ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Morphine PK/PD scaffold

- Added morphine as the 12th supported PharmacologyModule drug.
- Added allometric parent-drug PK, qualitative analgesia and respiratory-depression signals.
- Added renal-impairment/M6G accumulation proxy and CRRT-lite audit field.
- Centralized morphine concentration ownership in PharmacologyModule v1.14+, with PainStressSedation fallback preserved.
- Added morphine scenario, audit tool, tests and documentation.


## v1.13-alpha ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Furosemide PK/PD scaffold

- Added furosemide as the 11th PharmacologyModule drug.
- Linked bolus-equivalent exposure and continuous infusion to C_furosemide_mg_L.
- Added renal-function-dependent furosemide clearance/effect factor.
- Added qualitative furosemide_effect_signal consumed by renal AKI/fluid-balance modules.
- Added CRRT-lite furosemide audit field and scenario/test coverage.

# Changelog

## v1.23.3-alpha
- Added artificial-airway ETT/tracheostomy resistance, dead-space, cuff-leak and obstruction scaffold.


## v1.12-alpha

- Added vancomycin PK/PD educational scaffold with renal-function-dependent clearance.
- Added CRRT-lite vancomycin extracorporeal clearance audit field.
- Added qualitative vancomycin target-attainment and antimicrobial coverage coupling.
- Added vancomycin AKI/CRRT scenario and regression tests.


## v1.11 public-clean

Public-clean source bundle prepared from the alpha development line.

Included public-facing components:

- pediatric scenario engine and YAML scenarios;
- shared physiology bus and modular physiology architecture;
- pediatric PK/PD allometric scaffold;
- priority PICU pharmacology scaffold;
- CRRT-lite drug clearance scaffold;
- public respiratory mechanics and three-zone V/Q gas-exchange scaffold;
- pediatric cardiovascular scaling scaffold;
- curriculum metadata, starter notebooks and Streamlit educational interface;
- expert-review package tools and templates.

Excluded from this public-clean bundle:

- generated outputs;
- internal development notes;
- historical fragmented changelogs;
- private working documents.

## v1.15-alpha ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Clonidine PK/PD scaffold

- Added clonidine as the 13th centralized PK/PD drug.
- Added educational outputs for alpha-2 sedation, sympatholysis, bradycardia/hypotension risk and withdrawal modulation.
- Added clonidine withdrawal-weaning scenario, audit tool and tests.


## v1.18-alpha ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Benchmark matrix expansion

- Added `data/literature_benchmark_targets_v1.18.yaml` with expanded plausibility corridors for bronchiolitis, neonatal RDS, CRRT-lite, new PK/PD scaffolds, endocrine, hepatic, hemolysis and pulmonary hypertension scenarios.
- Added `tools/benchmark_matrix_v1_18.py` to generate target matrix, source matrix, scenario coverage and optional evaluation output.
- Added `docs/BENCHMARK_MATRIX_v1.18.md`.
- Added `tests/test_v118_benchmark_matrix.py`.
- This layer is not external clinical validation.


# CHANGELOG v1.19-alpha ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Score assumption registry hardening

## Added

- `data/score_assumption_registry_v1.19.yaml` with hardened score/proxy/modifier metadata.
- `data/score_assumption_audit_scenarios_v1.19.yaml` default audit subset.
- `tools/score_assumption_audit_v1_19.py` for registry completeness and range-audit reporting.
- `docs/SCORE_ASSUMPTION_HARDENING_v1.19.md`.
- `tests/test_v119_score_assumption_hardening.py`.

## Changed

- Updated public alpha check to require the v1.19 score registry, audit tool, documentation and tests.
- Updated score registry audit default to v1.19.
- Updated version metadata to 1.19-alpha.

## Limitations

- This is not external validation.
- Numeric ranges are software sanity ranges for internal qualitative variables, not clinical targets.

## v1.21-alpha ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Sobol full runner

- Added configurable Sobol/Saltelli-Jansen full runner with smoke, exploratory, report and paper presets.
- Added dry-run planning, output manifests and guardrails for heavy runs.
- Extended sensitivity summary keys for adaptive V/Q, antibiotic and selected PK/PD outputs.
- This is uncertainty-analysis infrastructure only; it is not clinical validation.


## v1.22-alpha ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â EPALS reversible-cause taxonomy scaffold

- Added `data/epals_reversible_causes_v1.22.yaml` with a 5H/5T educational reversible-cause map.
- Added `data/epals_scenario_curriculum_v1.22.yaml` with planned EPALS teaching sequence and staged implementation plan.
- Added `tools/epals_scenario_audit_v1_22.py` and `tests/test_v122_epals_taxonomy.py`.
- Added `docs/EPALS_SCENARIO_ROADMAP_v1.22.md`.
- No simulation-engine changes in this release; scenario YAML implementation is split into v1.22.1 and v1.22.2.

## v1.22.2-alpha

- Added EPALS 5T executable scenario pack and audit tooling.


## v1.22.3-alpha

- Added EPALS debrief scaffold specification, tool, documentation and tests.
- Generates per-scenario instructor-facing reports for the EPALS 5H/5T scenario pack.
- No simulation-engine changes in this release.


## v1.26-alpha ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Airway/emergency debrief engine

- Added `tools/emergency_debrief_engine_v1_26.py`.
- Added `data/emergency_debrief_spec_v1.26.yaml`.
- Added instructor-facing reports for airway decision scenarios.
- Computes oxygenation nadir, time below SpO2 thresholds, rescue ventilation timing, intubation timing, reoxygenation timing, failed attempts and debrief flags.
- Added tests and documentation.


## v2.2-alpha ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Web Monitor MVP

- Added a lightweight browser-based monitor served from the local FastAPI backend.
- Added static UI files under `ui/`: monitor layout, Canvas waveform rendering, bedside vitals, scenario selector, airway controls, drug controls, and event timeline.
- Added `/`, `/monitor`, and `/ui/*` static routes.
- Added `/session/{id}/reset` and `/session/{id}/events` API endpoints.
- Kept waveform generation browser-side and streamed only compact state anchors.


## v2.2-alpha

Emergency training mode: scenario catalogue, live session debrief endpoint and web monitor debrief panel.

## v2.6-alpha

- Reworked the web monitor into a bedside-monitor-first console.
- Added modal apparatus panels for Session, Airway, Drugs, Emergency Training, Instructor Mode, Debrief and Timeline.
- Added learner/instructor view toggle and tablet-friendly responsive layout.
- Preserved API/session/debrief behavior; no physiological-model changes.

## v3.1-step3.7 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Steroid response contract

- Revised hydrocortisone and dexamethasone effects to use delayed PD signals rather than raw command doses.
- Added steroid audit signals for vasopressor sensitization, anti-inflammatory activity, ICP/edema effect, glucose effect, and overall delayed effect.
- Routed hydrocortisone/dexamethasone effects through SteroidsModule outputs before downstream sepsis/endocrine/circulation effects.
- Added CirculationModule consumption of `steroid_SVR_mod`, making hydrocortisone vasopressor sensitization active but delayed.
- Prevented raw hydrocortisone/dexamethasone commands from instantly suppressing sepsis cytokines or instantly activating the endocrine axis.
- Added `tests/test_v312_steroid_response_contract.py`.

## v3.1-step4.2 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Bedside sparkline trends

- Added UI-only miniature sparkline trends for HR, SpO2, MAP, PaCO2/EtCO2, Paw and FiO2 in the primary bedside vital cards.
- Trends use the existing bedside WebSocket stream and keep approximately the last 60 simulated seconds, with a bounded 360-sample buffer.
- Added dual PaCO2/EtCO2 trend rendering to make ventilation-perfusion changes more visible after the real EtCO2 coupling step.
- No backend, model, Docker or pharmacology changes.



## v3.1-step4.13-emogas-panel-clean-trend10min

- Fixed stale VERSION label.
- Normalized ZIP directory paths for safer extraction/build.
- Repaired UI mojibake in key bedside labels.
- Extended bedside sparkline trend buffer from 60 simulated seconds to 10 simulated minutes.
- Added README_FIRST_START_HERE.txt with clean Docker start instructions.

## 3.1-step4.13-emogas-panel-hf1-hf2-hf3-trend10min-visible

Hotfix release for pre-release blockers.

- HF-1: normalized UI Unicode/mojibake labels and saved text sources as UTF-8 without BOM.
- HF-2: made `tools/score_assumption_audit_v1_19.py` robust to UTF-8 BOM when parsing `core/bus.py`.
- HF-3: updated `VERSION` to match the integrated Step 4.13 emogas panel build with visible 10-minute trends.
- No physiology-engine changes and no new UI features beyond the already integrated visible trend build.



## v3.1 Step 4.14 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Airway quick-action fix + monitor audio + pressure-coupled ABP
- Fixed quick Intubate button: event-specific severity now sends `emergency` instead of generic `moderate`.
- Added backend severity aliases so legacy `perform_intubation/moderate` requests no longer crash.
- Added browser Web Audio monitor toggle: pulse-ox pitch tone plus ECG QRS click, off by default.
- Strengthened ABP waveform rendering so amplitude visibly follows pulse pressure while vertical position follows MAP.
- Added contract test `test_v333_airway_audio_abp_contract.py`.

## v3.1 Step 4.42 — Organ perfusion model

- Added `OrganPerfusionModule` for pediatric kidney/liver perfusion proxies coupled to MAP, CVP, CO, oxygenation and shock burden.
- Added pediatric MAP low-threshold anchors, organ perfusion pressure, renal/hepatic hypoperfusion indices and organ hypoperfusion burden.
- Added urine-output trajectory, creatinine surrogate/ratio, hepatic/organ lactate-clearance modifier and GFR perfusion modifier.
- Added instructor-facing renal/hepatic warning strings for simulation feedback.
- Updated `core/bus.py`, roadmap and Codex handoff documentation.
- Added `tests/test_v442_organ_perfusion_contract.py`.
- Targeted regression: 12 passed across Step 4.39-4.42 contract tests.


## v3.1 Step 4.45 — Scenario timing and critical-event trigger

- Added explicit scenario timing metadata: nominal real-time duration, virtual duration, acceleration factor, and critical-event trigger time.
- Added stable-start wrapper so scenarios can begin from a healthy/stable child and shift the critical event after a visible manual/configured trigger.
- Updated Streamlit UI to show real-time duration before scenario start and expose stable-start + trigger controls.
- Added contract tests for timing metadata, shifted timelines, and stable-start behavior.
- Educational alpha only; no clinical timing prediction implied.

## v3.1 step5.1D — Sensitivity maps

Added internal sensitivity mapping before publication freeze.

- Added `tools/sensitivity_maps_v5_1D.py`.
- Added `data/sensitivity_maps_v5.1D.yaml`.
- Added deterministic parameter-to-outcome mapping across representative scenarios.
- Added sensitivity ranking, dominant variable detection, and fragility flags.
- Added Markdown/JSON/CSV outputs under `outputs/sensitivity_maps_v5.1D/`.
- Added regression tests for output generation and ranking schema.

Validation: targeted Step 5.1D tests passed; cumulative validation line extended from 5.0A through 5.1D.



## Step 5.2 — Publication freeze / release candidate

- Added `data/release_candidate_manifest_v5.2.yaml` with package-level SHA-256 hashes and frozen scope.
- Added `docs/RELEASE_CANDIDATE_FREEZE_v5.2.md`.
- Added `docs/CODEX_HANDOFF_v5.2_to_next.md`.
- Added release-candidate freeze tests.
- Declared current package a release candidate, not a clinical validation or medical device certification.

