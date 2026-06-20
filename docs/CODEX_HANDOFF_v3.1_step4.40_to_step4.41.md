# Codex handoff — PCCSim v3.1 Step 4.40 to Step 4.41

Current package status: `3.1-step4.40-epals-decision-engine`.

Step 4.40 is complete. The EPALS-like educational decision engine has been added with targeted contract tests and changelog/roadmap updates.

## Recommended next Codex prompt

```text
Continue from PCCSim v3.1 package VERSION 3.1-step4.40-epals-decision-engine.
Use docs/PCCSIM_V3_1_PHARMACOLOGY_AND_UI_ROADMAP.md as the source of truth.
Implement Step 4.41 only: Intubation physiology.
Scope: preoxygenation reservoir, apnea timer, desaturation trajectory and RSI drug-effect coupling around existing airway actions.
Keep it educational/non-clinical, add targeted contract tests, update VERSION, CHANGELOG.md and the roadmap.
Do not refactor unrelated code.
```

## Step 4.41 boundaries

Expected implementation:

- Bus fields for intubation physiology state.
- A narrow module or airway-event coupling layer.
- Contract tests for preoxygenation improving reserve, apnea worsening reserve/desaturation, and RSI drug effects changing the trajectory.

Explicit non-goals:

- no clinical dosing recommendation;
- no automatic airway decision-making;
- no major UI rewrite unless required to expose already-computed fields.
