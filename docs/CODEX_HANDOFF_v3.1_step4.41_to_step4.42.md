# Codex handoff — v3.1 Step 4.41 to Step 4.42

Current package version: `3.1-step4.41-intubation-physiology`.

Step 4.41 completed:

- Added `IntubationPhysiologyModule`.
- Added Bus fields for preoxygenation reservoir, apnea timer, RSI suppression and peri-intubation desaturation risk/phase/warning.
- Added targeted contract tests.
- Updated changelog and roadmap.

## Recommended next Codex prompt

```text
Continue from PCCSim v3.1 package VERSION 3.1-step4.41-intubation-physiology.
Use docs/PCCSIM_V3_1_PHARMACOLOGY_AND_UI_ROADMAP.md as the source of truth.
Implement Step 4.42 only: Organ perfusion model.
Scope: kidney/liver perfusion proxies, urine-output trajectory, creatinine surrogate and lactate-clearance modifier coupled to MAP/CO/CVP/shock state.
Keep scope narrow, add targeted contract tests, update VERSION, CHANGELOG.md and the roadmap.
Do not refactor unrelated code and preserve the educational/non-clinical disclaimer.
```
