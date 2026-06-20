# PCCSim v3.1 — Step 5.2 Release Candidate Freeze

Status: **release candidate**  
Baseline: **Step 5.1D sensitivity maps**  
Date: 2026-06-20

## What is frozen

This step freezes the current publication-grade branch after completion of:

- Step 5.0A — Literature benchmark engine
- Step 5.0B — Massive Monte Carlo
- Step 5.0C — Plausibility guardrails
- Step 5.0D — Scenario solvability audit
- Step 5.0E — UI human factors audit v2
- Step 5.1A — Export & reproducibility pack
- Step 5.1B — Methods appendix generator
- Step 5.1C — Figure generator contract
- Step 5.1D — Sensitivity maps

## Release candidate rules

After this freeze, no model, scenario, UI, validation, or export behavior should be changed silently.
Any change requires:

1. a new roadmap step,
2. a changelog entry,
3. updated tests,
4. a new release manifest.

## Publication-grade outputs expected

For each publication/training run, export:

- session JSON,
- physiological timeline CSV,
- intervention log CSV,
- reproducibility manifest with SHA-256 hashes,
- methods appendix,
- figures and sensitivity summaries when relevant.

## Safety status

This project remains **not for clinical use**. It is an educational and research simulation prototype only.
It must not be used for diagnosis, treatment, drug dosing, triage, or clinical decision making.

## Known residual limitation

The freeze certifies internal consistency and reproducibility of the current package. It does not certify external clinical validity.
Prospective clinical/educational validation remains outside the software freeze.
