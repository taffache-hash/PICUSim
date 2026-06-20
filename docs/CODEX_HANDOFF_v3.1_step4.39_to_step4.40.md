# Codex handoff — v3.1 Step 4.39 to Step 4.40

Current package: `3.1-step4.39-shock-engine`.

## Closed in Step 4.39

- Added `ShockModule` for distributive, hypovolemic, cardiogenic, obstructive and mixed shock.
- Added Bus shock fields and phenotype indices.
- Coupled shock modifiers into circulation, baroreflex, heart and metabolism without taking ownership of final MAP/CO/HR/lactate.
- Added documentation, YAML spec and contract tests.

## Start next

Step 4.40 — Decision engine / EPALS-like contextual prompts.

Suggested implementation rule: one narrow step, explicit non-goals, targeted tests, update `VERSION`, `CHANGELOG.md` and roadmap.

## Non-clinical disclaimer

This project is educational/simulation-only and not a clinical decision support system.
