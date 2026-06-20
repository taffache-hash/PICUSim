# PCCSim v3.1 — Pharmacology and UI/monitor roadmap

## Working principle

Proceed one step at a time. Each step must have:

1. narrow scope;
2. explicit non-goals;
3. targeted contract tests;
4. a new zip package;
5. no unrelated refactor mixed in.

## Already completed

- Step 3.1 — extended drug controls in UI/router.
- Step 3.2 — `drug_MAP_mod` direction fix.
- Step 3.3 — vasoactive response cleanup.
- Step 3.4A — opioids.
- Step 3.4B — midazolam/propofol.
- Step 3.4C — ketamine.
- Step 3.4D — alpha-2 agonists.
- Step 3.5 — rocuronium/NMB.
- Step 3.6 — respiratory drugs/iNO.
- Step 3.7 — steroids.
- Step 3.8 — furosemide/fluid balance.
- Step 3.9 — insulin/glucose/potassium.
- Step 4.0A — ABP/SBP-DBP monitor coupling from model arterial pressures.
- Step 4.0B — real EtCO2 coupled to gas exchange and perfusion.
- Step 4.1A — extended monitor panel on request with hemodynamic, respiratory, metabolic/labs, neurologic/sedation and renal/fluid blocks.

## Explicitly deferred

- Step 3.10 antibiotics is deferred by user request because it is marginal for the current educational goal.

## User monitor/UI review — queued items

### Motor/physiology display realism

- Step 4.0B — real EtCO2, replacing `EtCO2_proxy = PaCO2 - 5` with a value coupled to alveolar ventilation, dead space/VQ burden and perfusion/CO. **Completed.**
- Step 4.0C — ScvO2 calculated from SaO2, VO2, CO and Hb.
- Step 4.0D — explicit module execution order/dependency contract with runtime check.
- Step 4.0E — simulated-time vs wall-clock exposure and speed multiplier indicator/control.

### UI/monitor usability

- Step 4.1A — extended monitor panel on request: **Completed.**
- Step 4.1B — optional always-visible labs strip: lactate, glucose, K, Na, Hb, creatinine, bilirubin, GCS proxy, RASS proxy, ICP, CVP, DO2, urine output, rotating every 5-10 real seconds.
- Step 4.2 — sparkline trends for HR, MAP, SpO2 and key respiratory values over the last 60 seconds. **Completed.**
- Step 4.3 — immediate visual feedback on drug dose changes: pending/confirmed state while backend control profile catches up.
- Step 4.4 — threshold alarms/highlights for HR, SpO2, MAP, PaCO2/EtCO2, Paw. CSS visual alerts first; no audio initially.
- Step 4.5 — scenario information card always visible/collapsible: age, weight, diagnosis, educational objective and current task.

### Advanced panels

- Step 4.6 — all-drugs control window grouped by vasoactive, sedative/analgesic, respiratory, renal/metabolic, steroids and antimicrobials.
- Step 4.7 — calculated-parameters/debug window exposing searchable Bus variables beyond the curated Step 4.1A monitor panel.
- Step 4.8 — per-drug audit panel showing concentration, PD signal, effective response, renal/hepatic modifiers and warning/risk markers.
- Step 4.9 — searchable debug/advanced instructor panel, hidden by default in learner mode.

## Impact/effort priority

Highest value near-term order:

1. Step 4.4 — threshold visual alarms.
2. Step 4.5 — scenario information card.
3. Step 4.1B — optional always-visible labs strip.
4. Step 4.6/4.7 — complete drugs and searchable hidden calculated parameters windows.
5. Step 4.3 — pending/confirmed feedback on drug dose changes.

## Non-clinical-use note

All outputs remain educational, qualitative/semi-mechanistic and not for clinical use.


## Step 4.1B completed — Extended monitor v2 snapshot-only

The extended monitor is now expanded to 11 collapsible blocks and uses manual snapshot refresh only. No continuous polling or new WebSocket is used. This keeps the bedside screen light and avoids UI overload while making hidden Bus parameters available on demand.


## Step 4.1C completed — Requested popup charts

A popup chart modal was added. It opens on request from Monitor esteso and draws charts from either the existing bedside trend buffer or manual extended monitor snapshots. No continuous full-Bus stream is used.


## Step 4.3 completed — Control pending/confirmed feedback

Live drug and ventilator controls now display pending/confirmed/error states. This closes the cognitive loop after a dose or ventilator setting change without requiring a new backend endpoint.

## Step 4.18 completed — Always-visible rotating labs strip

A compact bedside labs strip now rotates through four lab/secondary parameters at a time every 8 real seconds. It reuses full-profile state with an 8-second throttle while a session is active, keeping the main monitor informative without streaming the full Bus at high frequency.
## Step 4.19 completed - Simulated time / wall-clock / speed telemetry

The bedside session strip now exposes simulated time, real elapsed wall time and effective speed multiplier, updating during running sessions and resetting cleanly on load/reset.

## Step 4.25 completed — Static UI encoding fix

Static monitor labels in `index.html` and CSS generated symbols now render with proper UTF-8 characters, including SpO₂, PaCO₂, EtCO₂, FiO₂, cmH₂O and speed ×.

## Step 4.26 completed — Dynamic UI and roadmap encoding fix

Dynamic labels and units generated by `app.js`, plus this roadmap document, now avoid visible mojibake in monitor panels, graph status text, instructor/debrief summaries and saved-session metadata.

## Step 4.27 completed — Quick monitor button active state

The bedside quick buttons for ABG, Boli and Monitor+ now mirror the currently open apparatus panel with a visible active state, `aria-pressed` feedback and reset-on-close behavior. This extends the pressed/not-pressed clarity from the dock cards to the monitor header shortcuts.

## Step 4.28 completed — Airway rescue recovery and stale-session handling

The airway workflow now has a contract-tested accidental extubation → bag-mask rescue → reintubation sequence. The UI also detects stale in-memory sessions after a server restart, clears pending airway/session button states, disconnects old streams and shows a clear reload message instead of a raw `Unknown session` alert.

## Step 4.29 completed — Cardiac rhythm/arrest foundation

The Bus now exposes a first cardiac rhythm/arrest state model with rhythm taxonomy, pulse state, shockable/non-shockable classification, CPR/ROSC markers and post-arrest risk hooks for renal hypoperfusion and reperfusion injury. The backend accepts `cardiac_rhythm_event` actions for VF, pulseless VT, PEA, asystole, unstable pulsed rhythms and ROSC. The bedside monitor shows an initial rhythm/pulse/shockability/RCP strip.

## Step 4.30 completed — Minimal RCP operational panel

The app now has an initial RCP apparatus panel with rhythm/pulse/shockability status, EtCO2/MAP feedback, compression quality control and Start/Stop compressions. A new `cpr_control` action updates CPR state and produces educational CPR perfusion effects during arrest before later defibrillation and drug steps.

## Step 4.31 completed — Defibrillation and synchronized cardioversion

The RCP panel now includes shock energy selection, asynchronous defibrillation and synchronized cardioversion controls. The backend records shock energy, mode, appropriate/effective result and counters. VF/pulseless VT can convert with adequate asynchronous shock, PEA/asystole reject shock as non-indicated, and unstable pulsed VT can convert with synchronized cardioversion.

## Step 4.32 completed — RCP drug bolus controls

The RCP panel now includes bolus controls for epinephrine/adrenaline, amiodarone and atropine. The backend tracks counters, last drug, appropriateness and context-specific educational effects: epinephrine in arrest, amiodarone in shockable rhythms and atropine in unstable bradycardia.

## Step 4.33 completed - Respiratory arrest to PEA scenario

The scenario library now includes `respiratory_arrest_to_pea_child_v1_31.yaml`, a first cardiac-arrest teaching case that deteriorates from hypoxic respiratory failure to unstable bradycardia and then non-shockable PEA. Scenario timelines can now schedule `cardiac_events`, and scenario perturbations include direct gas, lactate and arterial pH setters for later ROSC/post-arrest physiology work. The new contract test verifies catalog visibility, rhythm progression, CPR activation, epinephrine bolus handling and non-shockable shock rejection.

## Step 4.34 completed - Post-ROSC care markers

ROSC now opens an explicit post-arrest phase instead of making the patient appear fully resolved. The Bus tracks post-ROSC care status, oxygenation/ventilation/perfusion optimization markers, residual acidosis burden, myocardial dysfunction risk, renal hypoperfusion and reperfusion injury risk. The RCP panel exposes those markers and includes a `Stabilizza post-ROSC` control backed by the new `post_rosc_care` action.

## Step 4.35 completed - Shockable VF arrest scenario

The scenario library now includes `shockable_vf_arrest_child_v1_31.yaml`, a first shockable cardiac-arrest teaching case. It progresses to VF arrest, verifies shockable classification, supports CPR and amiodarone in the correct context, rejects inadequate shock energy, converts with adequate asynchronous defibrillation and then transitions into post-ROSC care.

## Step 4.36 completed - Unstable VT with pulse scenario

The scenario library now includes `unstable_vt_with_pulse_child_v1_31.yaml`, a pulsed unstable tachyarrhythmia case. It verifies that VT with pulse is not cardiac arrest, rejects asynchronous defibrillation as not indicated, requires synchronized cardioversion, distinguishes inadequate from adequate energy and avoids incorrectly entering post-ROSC care after pulsed rhythm conversion.

## Step 4.37 completed - Unstable bradycardia with pulse scenario

The scenario library now includes `unstable_bradycardia_with_pulse_child_v1_31.yaml`, a pulsed unstable bradycardia case. It verifies pulse-aware classification, rejects asynchronous defibrillation, rejects arrest-only epinephrine framing, and accepts atropine as appropriate in the bradycardia context while keeping the patient out of ROSC/post-arrest state.

## Step 4.38 completed - Vasoactive infusion feedback hotfix

Continuous vasoactive infusions in septic shock were accepted by the backend but could remain visually stuck as `pending` in the UI. Live numeric controls now use the immediate action response to resync/confirm control values, so adrenaline, noradrenaline, dopamine, vasopressin and milrinone infusion fields clear pending promptly after the server accepts them.

---

# Codex handoff roadmap — continuation after Step 4.38

## Current verified stopping point

Current package: `3.1-step4.38-vasoactive-infusion-feedback-hotfix`.

Step 4.38 closed the active UI regression where continuous vasoactive infusions were accepted by the backend but could remain visually stuck as `pending`. The immediate action response now resynchronizes/clears the live numeric infusion fields for adrenaline, noradrenaline, dopamine, vasopressin and milrinone.

## Development rule for Codex

Continue exactly one step at a time. For every new step:

1. keep scope narrow;
2. state explicit non-goals;
3. add at least one targeted contract test;
4. update `VERSION`, `CHANGELOG.md`, and this roadmap;
5. avoid unrelated refactors;
6. preserve the non-clinical educational disclaimer.

## Proposed next roadmap

### Step 4.39 — RCP cycle timer and algorithm prompts

Goal: make the RCP panel more educational during arrest by exposing cycle time, time since last rhythm check, time since last shock, time since last epinephrine, and simple context-aware prompts.

Suggested scope:

- add backend state fields for CPR cycle timing and last-intervention timestamps;
- expose them in the RCP panel;
- add educational prompts such as rhythm check due, adrenaline window, shockable rhythm detected, non-shockable rhythm, optimize compressions/ventilation;
- add contract test verifying timer fields and prompt changes after CPR, shock and drug actions.

Explicit non-goals:

- no real ACLS/PALS prescribing engine;
- no dose recommendation beyond existing educational controls;
- no full scoring engine yet.

### Step 4.40 — Reversible causes bedside checklist

Goal: connect the existing 5H/5T educational taxonomy to the live arrest/unstable-rhythm workflow.

Suggested scope:

- add a collapsible RCP checklist for hypoxia, hypovolemia, hydrogen ion/acidosis, hypo/hyperkalemia, hypothermia, tension pneumothorax, tamponade, thrombosis, toxins;
- mark likely causes from scenario metadata and current Bus signals;
- allow instructor/learner to mark items as considered/treated;
- add contract test for scenario-linked checklist visibility and state persistence.

Explicit non-goals:

- no automatic definitive diagnosis;
- no clinical treatment protocol;
- no new physiology modules unless a minimal signal is already present.

### Step 4.41 — Post-ROSC instability and re-arrest risk

Goal: make ROSC less binary and more realistic educationally.

Suggested scope:

- let residual hypoxia, acidosis, hypotension or poor ventilation increase post-ROSC instability markers;
- allow deterioration back to unstable rhythm/arrest in selected scenarios if stabilization is ignored;
- expose warning markers in RCP/post-ROSC panel;
- add contract test for ROSC followed by instability when post-ROSC care is not performed.

Explicit non-goals:

- no validated prognostic prediction;
- no patient-specific mortality model.

### Step 4.42 — Emergency debrief extension for cardiac-arrest cases

Goal: extend existing emergency debrief logic to arrest/rhythm scenarios.

Suggested scope:

- report time to CPR start, compression interruptions, shock appropriateness, shock energy adequacy, time to epinephrine in non-shockable arrest, inappropriate shock attempts, ROSC achievement and post-ROSC stabilization;
- generate instructor-facing summary lines;
- add contract test using the respiratory arrest/PEA and VF scenarios.

Explicit non-goals:

- no grading/credentialing;
- no real clinical performance certification.

### Step 4.43 — RCP UI polish and learner/instructor separation

Goal: reduce UI overload while preserving instructor depth.

Suggested scope:

- learner view: essential rhythm, pulse, CPR, shock, key prompts;
- instructor view: detailed counters, last actions, appropriateness/effectiveness flags, internal rhythm state;
- add ARIA/active button consistency with previous UI state work;
- add contract test for learner/instructor visibility separation.

Explicit non-goals:

- no new model behavior;
- no visual redesign outside the RCP/emergency panel.

### Step 4.44 — Regression audit and stale-state hardening

Goal: stabilize the whole v3.1 step4 line before adding larger modules.

Suggested scope:

- run the full current targeted test suite;
- specifically verify session restart, stale session, WebSocket reconnect, load/start/pause/step, airway actions, RCP actions, vasoactive controls and monitor panels;
- fix only blockers found by the audit;
- add a release audit note.

Explicit non-goals:

- no feature additions unless required to fix a regression.

## Later backlog after stabilization

- Broader shock algorithm teaching panel: septic, hemorrhagic, cardiogenic, obstructive and distributive shock patterns.
- Fluid/vasoactive decision support for educational “what changed and why” feedback.
- More scenario-authoring templates for arrest and shock cases.
- Optional ECG waveform morphology beyond rhythm labels.
- ECMO-lite only after arrest/shock pathways are stable.

## Codex next instruction

Recommended next Codex prompt:

```text
Continue from PCCSim v3.1 package VERSION 3.1-step4.42-organ-perfusion-model.
Use docs/PCCSIM_V3_1_PHARMACOLOGY_AND_UI_ROADMAP.md as the source of truth.
Implement Step 4.43 only: Advanced vasoactive engine.
Scope: receptor-weighted response and bounded interaction handling for norepinephrine, epinephrine, dopamine, dobutamine, milrinone and vasopressin; include hysteresis/tachyphylaxis/audit signals where appropriate.
Keep scope narrow, add targeted contract tests, update VERSION, CHANGELOG.md and the roadmap.
Do not refactor unrelated code and preserve the educational/non-clinical disclaimer.
```


## Step 4.39 completed — Shock engine

Status: **completed in this handoff package**.

Implemented a bounded educational shock phenotype engine for distributive, hypovolemic, cardiogenic, obstructive and mixed shock. The new module writes disease modifiers for SVR, preload, contractility, sympathetic/HR compensation, lactate production/clearance and shock stage. Existing owner modules remain responsible for final MAP/CO/HR/lactate values.

Files added/updated:

- `modules/cardiovascular/shock.py`
- `core/bus.py`
- `modules/cardiovascular/__init__.py`
- `modules/cardiovascular/circulation.py`
- `modules/cardiovascular/baroreflex.py`
- `modules/cardiovascular/heart.py`
- `modules/metabolism/metabolism.py`
- `data/shock_engine_specs_v4.39.yaml`
- `docs/SHOCK_ENGINE_v3.1_step4.39.md`
- `tests/test_v439_shock_engine_contract.py`

Contract tests: `tests/test_v439_shock_engine_contract.py`.

## Next roadmap after Step 4.39

### Step 4.40 — Decision engine / EPALS-like contextual prompts

Status: **completed**.

Implemented `EPALSDecisionModule`, a non-prescriptive educational ABCDE/pattern-recognition layer. It writes priority, pattern, confidence, instructor prompts, context flags and incoherence warnings for arrest, airway/breathing, shock and selected metabolic emergencies.

Files added/updated:

- `modules/decision/epals.py`
- `modules/decision/__init__.py`
- `core/bus.py`
- `docs/EPALS_DECISION_ENGINE_v3.1_step4.40.md`
- `docs/CODEX_HANDOFF_v3.1_step4.40_to_step4.41.md`
- `tests/test_v440_epals_decision_engine_contract.py`

Contract tests: `tests/test_v440_epals_decision_engine_contract.py`.

### Step 4.41 — Intubation physiology

Status: **completed**.

Implemented `IntubationPhysiologyModule`, a bounded educational peri-intubation physiology layer. It tracks preoxygenation reservoir, apnea timer, safe-apnea reserve proxy, RSI respiratory suppression, desaturation risk/slope, peri-intubation phase and warning. It reads existing airway events/actions and can apply bounded SaO2/PaO2 desaturation during apnea.

Files added/updated:

- `modules/airway/intubation_physiology.py`
- `modules/airway/__init__.py`
- `core/bus.py`
- `docs/INTUBATION_PHYSIOLOGY_v3.1_step4.41.md`
- `docs/CODEX_HANDOFF_v3.1_step4.41_to_step4.42.md`
- `tests/test_v441_intubation_physiology_contract.py`

Contract tests: `tests/test_v441_intubation_physiology_contract.py`.

### Step 4.42 — Organ perfusion model

Status: **completed**.

Implemented `OrganPerfusionModule`, a bounded educational organ-perfusion layer. It couples MAP/CVP/CO/oxygenation/shock burden to pediatric MAP-threshold adjusted renal and hepatic perfusion proxies, urine-output trajectory, creatinine surrogate, organ hypoperfusion burden, GFR modifier and lactate-clearance modifier.

Files added/updated:

- `modules/perfusion/organ_perfusion.py`
- `modules/perfusion/__init__.py`
- `core/bus.py`
- `docs/ORGAN_PERFUSION_MODEL_v3.1_step4.42.md`
- `docs/CODEX_HANDOFF_v3.1_step4.42_to_step4.43.md`
- `tests/test_v442_organ_perfusion_contract.py`

Contract tests: `tests/test_v442_organ_perfusion_contract.py`.

### Step 4.43 — Advanced vasoactive engine [DONE]

Goal: receptor-weighted vasoactive response, hysteresis/tachyphylaxis and interaction handling for norepinephrine, epinephrine, dopamine, dobutamine, milrinone and vasopressin.

### Step 4.44 — Scenario engine v2

Goal: add/standardize 8-10 scenario packs for septic shock, anaphylaxis, tamponade, hyperkalemia, status epilepticus, TBI crisis, DKA shock and bronchiolitis failure.

Status: **completed**.

Implemented a scenario-engine v2 catalog and validation layer for eight EPALS-oriented teaching scenarios. The step standardizes manifest metadata, expected action focus, key output fields and debrief prompts, while keeping all outputs explicitly educational/research alpha only.

Files added/updated:

- `core/scenario_engine_v2.py`
- `core/scenario.py`
- `data/scenario_engine_v2_step4.44.yaml`
- `scenarios/epals_v2_septic_shock_warm.yaml`
- `scenarios/epals_v2_anaphylactic_shock.yaml`
- `scenarios/epals_v2_tamponade_obstructive_shock.yaml`
- `scenarios/epals_v2_hyperkalemia_aki_instability.yaml`
- `scenarios/epals_v2_status_epilepticus_hypoxia.yaml`
- `scenarios/epals_v2_tbi_icp_crisis.yaml`
- `scenarios/epals_v2_dka_dehydration_shock.yaml`
- `scenarios/epals_v2_bronchiolitis_respiratory_failure.yaml`
- `docs/SCENARIO_ENGINE_V2_v3.1_step4.44.md`
- `docs/CODEX_HANDOFF_v3.1_step4.44_to_step5.0.md`
- `tests/test_v444_scenario_engine_v2_contract.py`

Contract tests: `tests/test_v444_scenario_engine_v2_contract.py`.

## Next roadmap after Step 4.44

### Step 5.0 — Validation pack

Status: **next**.

Goal: run model-level plausibility and reproducibility validation across the Step 4.39-4.44 physiology/decision/scenario stack.

Planned scope:

- scenario catalog smoke validation across all v2 EPALS scenarios;
- benchmark range checks for MAP, HR, SaO2, PaCO2, lactate, K, urine output and selected decision fields;
- Monte Carlo reproducibility harness for selected scenarios;
- sensitivity checks for shock severity, FiO2, vasoactive dose, perfusion pressure and airway support;
- explicit plausibility guardrail report with pass/warn/fail status.

### Step 5.1 — Publication-ready reproducibility pack

Status: **planned**.

Goal: package assumptions, limitations, methods appendix and exportable figures/tables for manuscript/supplement use.


### Step 4.45 — Scenario timing and critical-event trigger — DONE

Deviation from original roadmap requested after live use. Priority: make scenario timing transparent.

Implemented:
- visible nominal real-time duration at scenario start;
- explicit virtual vs real-time metadata;
- stable-start mode: child begins healthy/stable;
- critical event shifted to manual/configured trigger time;
- Streamlit controls for stable start and trigger time;
- Codex-safe documentation and tests.

### Step 4.46 — Failure-to-rescue clock — DONE

Deviation continuation after Step 4.45.

Implemented:
- explicit golden-window timer after critical-event trigger;
- scenario phenotype inference for sepsis/anaphylaxis/tamponade/pneumothorax/bronchiolitis/hyperkalemia/status epilepticus/TBI/DKA;
- reversibility threshold and point-of-no-return markers;
- optional deterministic deterioration after missed rescue window;
- UI display separated from nominal real duration and virtual time;
- targeted tests and documentation.

Next suggested step: Step 4.47 — Adaptive deterioration engine: wrong or delayed actions actively worsen trajectory; correct early actions prevent failure-to-rescue escalation.


## Step 4.48 — Recovery engine [COMPLETED]

Recovery now starts only after a correct action following the critical-event trigger. The engine exposes first-response, partial-response and near-baseline windows, and applies bounded recovery perturbations to shock, perfusion, lactate and respiratory surrogates.

Next: Step 4.49 — Debrief intelligence v2: timeline analysis of delay-to-trigger, delay-to-treatment, in-window/out-of-window rescue and physiologic response.


## Step 4.50 — Full pre-validation audit [COMPLETED]

Purpose: pre-5.0 stabilization check requested after live use. This is an engineering audit, not publication-grade validation.

Completed:

- engine/API/UI targeted test pass;
- static human-style UI access audit;
- JS-to-HTML DOM target integrity check;
- core visible control presence check;
- Step 4.44 EPALS v2 scenario catalog smoke execution;
- hyperkalemia/AKI v2 calcium marker blocker fixed;
- audit report added at `docs/FULL_PREVALIDATION_AUDIT_v3.1_step4.50.md`.

Audit test result: **59 passed**.

Roadmap note before Step 5.0:

- Step 4.47 Adaptive deterioration engine and Step 4.49 Debrief intelligence v2 must be explicitly present in the Codex working tree before formal Step 5.0 validation.
- If absent, implement/restore them as Step 4.47 and Step 4.49 before 5.0.
- If present in the user/Codex branch, merge them into this audited package before 5.0.

Next: Step 5.0 — Validation pack, only after the 4.47/4.49 presence check is clean.


### Step 4.51 — Monitor layout compression — COMPLETED

- Numeric vitals moved to a vertical side column beside the curves.
- Waveform area compressed to reduce visual dominance.
- Vital numbers enlarged for scenario usability.
- Existing ids preserved for regression compatibility.

## Step 5.0A — Literature benchmark engine — COMPLETED

Status: completed.

Artifacts:
- `data/literature_benchmark_targets_v5.0A.yaml`
- `tools/literature_benchmark_engine_v5_0A.py`
- `tests/test_v500a_literature_benchmark_engine.py`
- `docs/LITERATURE_BENCHMARK_ENGINE_v5.0A.md`
- `outputs/literature_benchmark_v5.0A/`

Current result: 18 evaluated checks; 12 PASS, 6 REVIEW, 0 NO_DATA.

Next planned step: 5.0B — Massive Monte Carlo / stochastic stress testing.



## Step 5.0B — Massive Monte Carlo stress runner

Status: completed.

Deliverables:
- Monte Carlo spec for core benchmark scenarios.
- Reproducible runner with deterministic seed and parameter draw traceability.
- Plausibility/outlier detector for non-finite values and broad biological bounds.
- Compact handoff run generated; larger 10k–50k campaigns remain possible locally/Codex.

Next: Step 5.0C — Plausibility guardrails.


## Step 5.0C — Plausibility guardrails

Status: completed.

Deliverables:
- critical biological bounds for core outputs;
- scenario-specific soft REVIEW corridors;
- logical consistency rules for fraction/percent mistakes and incompatible physiology;
- audit-only clamp policy;
- reproducible guardrail report over current Monte Carlo outputs.

Current result: 15 rows audited; 0 critical findings; 0 review findings; guardrails passed.

Next: Step 5.0D — Scenario solvability audit.


## Step 5.1A — Export & reproducibility pack — COMPLETE

Status: complete.

Deliverables:
- session JSON export
- physiological timeline CSV
- intervention/action log CSV
- structured Markdown report
- manifest JSON with SHA-256 hashes
- optional seed metadata
- API endpoints and regression tests

Next planned step: 5.1B — Methods appendix generator.


## Step 5.1B — Methods appendix generator [COMPLETED]

- Deterministic methods appendix generator.
- Active module inventory.
- Assumptions and limitations extraction.
- Validation artifact summary from 5.0A–5.0E.
- Reproducibility controls linked to 5.1A.

Next planned: Step 5.1C — Figure generator.

## Step 5.1D — Sensitivity maps [COMPLETED]

Status: completed.

Deliverables:
- parameter-to-outcome sensitivity map generator;
- dominant variable ranking;
- fragile physiology detector;
- CSV/JSON/Markdown reproducibility outputs;
- targeted tests.

Next step: Step 5.2 — Publication freeze / release candidate lock.

