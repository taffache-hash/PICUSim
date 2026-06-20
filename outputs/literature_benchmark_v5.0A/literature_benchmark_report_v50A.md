# Step 5.0A — Literature Benchmark Engine Report

Scope: physiological plausibility benchmarking for the PDT v3.1 alpha simulator.

This is **not** external clinical validation and **not** medical decision support.
It is a regression and plausibility gate before the larger 5.0 validation pack.

Spec version: **v5.0A**

## Benchmarked scenarios

- **healthy_child_20kg** — Stable child baseline benchmark.
- **infant_bronchiolitis** — Bronchiolitis gas-exchange plausibility benchmark.
- **epals_v2_septic_shock_warm** — Warm septic shock deterioration and rescue corridor.
- **epals_v2_dka_dehydration_shock** — DKA/dehydration shock acid-base and perfusion corridor.
- **epals_v2_anaphylactic_shock** — Anaphylactic shock rapid collapse/rescue corridor.

## Source traceability

| Scenario | Variable | Range | Sources | Missing sources |
|---|---|---:|---|---|
| healthy_child_20kg | HR | 70.0–140.0 | RCH_vitals;Fleming_2011_vitals |  |
| healthy_child_20kg | MAP | 55.0–85.0 | RCH_vitals |  |
| healthy_child_20kg | SaO2 | 0.94–1.0 | RCH_vitals |  |
| healthy_child_20kg | PaCO2 | 32.0–48.0 | PALICC2_2023 |  |
| healthy_child_20kg | lactate | 0.5–2.5 | SSC_peds_2020 |  |
| infant_bronchiolitis | SaO2_min | 0.82–0.97 | AAP_bronchiolitis_2014 |  |
| infant_bronchiolitis | PaCO2_max | 45.0–85.0 | AAP_bronchiolitis_2014;PALICC2_2023 |  |
| infant_bronchiolitis | HR_max | 120.0–220.0 | RCH_vitals;Fleming_2011_vitals |  |
| epals_v2_septic_shock_warm | MAP_min | 25.0–65.0 | SSC_peds_2020;RCH_vitals |  |
| epals_v2_septic_shock_warm | lactate_max | 2.0–12.0 | SSC_peds_2020 |  |
| epals_v2_septic_shock_warm | HR_max | 130.0–240.0 | RCH_vitals;Fleming_2011_vitals |  |
| epals_v2_dka_dehydration_shock | pH_a_min | 6.85–7.3 | DKA_ISPAD_context |  |
| epals_v2_dka_dehydration_shock | HCO3_mmol_L_min | 3.0–18.0 | DKA_ISPAD_context |  |
| epals_v2_dka_dehydration_shock | MAP_min | 30.0–70.0 | RCH_vitals |  |
| epals_v2_dka_dehydration_shock | K_mmol_L_max | 3.0–7.5 | DKA_ISPAD_context |  |
| epals_v2_anaphylactic_shock | MAP_min | 25.0–65.0 | Anaphylaxis_peds_context;RCH_vitals |  |
| epals_v2_anaphylactic_shock | SaO2_min | 0.75–0.98 | Anaphylaxis_peds_context |  |
| epals_v2_anaphylactic_shock | HR_max | 130.0–240.0 | RCH_vitals;Fleming_2011_vitals |  |

## Evaluation

Checks passed: **12/18**. Review: **6**. No data: **0**.

| Scenario | Variable | Value | Target | Deviation % | Status |
|---|---|---:|---:|---:|---|
| healthy_child_20kg | HR | 166.8 | 70–140 | 19.12 | REVIEW |
| healthy_child_20kg | MAP | 78.68 | 55–85 | 0.00 | PASS |
| healthy_child_20kg | SaO2 | 0.7757 | 0.94–1 | 17.48 | REVIEW |
| healthy_child_20kg | PaCO2 | 58.63 | 32–48 | 22.15 | REVIEW |
| healthy_child_20kg | lactate | 0.9443 | 0.5–2.5 | 0.00 | PASS |
| infant_bronchiolitis | SaO2_min | 0.7737 | 0.82–0.97 | 5.64 | REVIEW |
| infant_bronchiolitis | PaCO2_max | 105 | 45–85 | 23.53 | REVIEW |
| infant_bronchiolitis | HR_max | 210 | 120–220 | 0.00 | PASS |
| epals_v2_septic_shock_warm | MAP_min | 25 | 25–65 | 0.00 | PASS |
| epals_v2_septic_shock_warm | lactate_max | 5.6 | 2–12 | 0.00 | PASS |
| epals_v2_septic_shock_warm | HR_max | 180 | 130–240 | 0.00 | PASS |
| epals_v2_dka_dehydration_shock | pH_a_min | 6.75 | 6.85–7.3 | 1.46 | REVIEW |
| epals_v2_dka_dehydration_shock | HCO3_mmol_L_min | 8 | 3–18 | 0.00 | PASS |
| epals_v2_dka_dehydration_shock | MAP_min | 47.43 | 30–70 | 0.00 | PASS |
| epals_v2_dka_dehydration_shock | K_mmol_L_max | 5.683 | 3–7.5 | 0.00 | PASS |
| epals_v2_anaphylactic_shock | MAP_min | 25 | 25–65 | 0.00 | PASS |
| epals_v2_anaphylactic_shock | SaO2_min | 0.86 | 0.75–0.98 | 0.00 | PASS |
| epals_v2_anaphylactic_shock | HR_max | 180 | 130–240 | 0.00 | PASS |