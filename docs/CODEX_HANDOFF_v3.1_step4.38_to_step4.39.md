# Codex handoff — PCCSim v3.1 Step 4.38 → Step 4.39

## Current package

`3.1-step4.38-vasoactive-infusion-feedback-hotfix`

## What is already complete

The project roadmap is updated through Step 4.38 in:

`docs/PCCSIM_V3_1_PHARMACOLOGY_AND_UI_ROADMAP.md`

Recent completed line:

- Step 4.29 cardiac rhythm/arrest foundation.
- Step 4.30 minimal RCP operational panel.
- Step 4.31 defibrillation/synchronized cardioversion.
- Step 4.32 RCP drug bolus controls.
- Step 4.33 respiratory arrest to PEA scenario.
- Step 4.34 post-ROSC care markers.
- Step 4.35 shockable VF arrest scenario.
- Step 4.36 unstable VT with pulse scenario.
- Step 4.37 unstable bradycardia with pulse scenario.
- Step 4.38 vasoactive infusion pending-feedback hotfix.

## Next step to implement

### Step 4.39 — RCP cycle timer and algorithm prompts

Implement only this step.

Scope:

- add backend state fields for CPR cycle timing and last-intervention timestamps;
- expose time since CPR start/current cycle, last rhythm check, last shock and last epinephrine in the RCP panel;
- show simple educational prompts driven by rhythm, pulse, CPR state and recent actions;
- add a targeted contract test for timer/prompt behavior.

Non-goals:

- no real clinical decision engine;
- no treatment prescription;
- no full cardiac-arrest scoring/debrief yet;
- no unrelated UI or physiology refactor.

## Files that probably matter

Likely backend/UI files:

- `core/cardiac_arrest_events.py`
- `core/events.py`
- `api/action_router.py`
- `api/schemas.py`
- `api/session.py`
- `ui/index.html`
- `ui/app.js`
- `ui/styles.css`

Likely tests to mirror:

- `tests/test_v350_rcp_panel_cpr_control_contract.py`
- `tests/test_v351_rcp_defibrillation_contract.py`
- `tests/test_v352_rcp_drug_bolus_contract.py`
- `tests/test_v353_respiratory_arrest_pea_scenario_contract.py`
- `tests/test_v354_post_rosc_care_contract.py`
- `tests/test_v358_vasoactive_infusion_pending_feedback_contract.py`

Create a new test, for example:

`tests/test_v359_rcp_cycle_timer_prompts_contract.py`

## Required updates after implementation

- `VERSION` → `3.1-step4.39-rcp-cycle-timer-prompts`
- prepend `CHANGELOG.md` with Step 4.39 notes
- append completion note to `docs/PCCSIM_V3_1_PHARMACOLOGY_AND_UI_ROADMAP.md`
- keep all wording educational/non-clinical

## Suggested Codex prompt

```text
Continue from PCCSim v3.1 package VERSION 3.1-step4.38-vasoactive-infusion-feedback-hotfix.
Use docs/PCCSIM_V3_1_PHARMACOLOGY_AND_UI_ROADMAP.md and docs/CODEX_HANDOFF_v3.1_step4.38_to_step4.39.md as source of truth.
Implement Step 4.39 only: RCP cycle timer and algorithm prompts.
Keep scope narrow, add tests/test_v359_rcp_cycle_timer_prompts_contract.py, update VERSION, CHANGELOG.md and the roadmap.
Do not refactor unrelated code and preserve the educational/non-clinical disclaimer.
```
