# Step 5.0B — Massive Monte Carlo

Purpose: stress-test PDT v3.1 with randomized scenario-level uncertainty before formal validation hardening.

This module is **not clinical validation**. It is an in-silico robustness gate.

## Added

- `data/monte_carlo_specs_v5.0B.yaml`
- `tools/monte_carlo_runner_v5_0B.py`
- `tests/test_v500b_monte_carlo_runner.py`
- `outputs/monte_carlo_v5.0B/`

## What it checks

- run stability across randomized physiologic uncertainty
- non-finite values
- broad biological bounds for SaO2, PaCO2, pH, MAP, HR, lactate, renal surrogates
- per-scenario flagged-run count
- parameter draw traceability

## Current targeted run

A compact reproducible run was generated for handoff. The full runner supports larger `--n` values for later 10k–50k campaigns in Codex/local execution.
