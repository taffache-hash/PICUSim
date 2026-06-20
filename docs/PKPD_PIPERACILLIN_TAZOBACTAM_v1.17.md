# v1.17-alpha — Piperacillin/Tazobactam PK/PD scaffold

This release adds a public educational beta-lactam scaffold centred on the piperacillin component of piperacillin/tazobactam.

## Implemented signals

- `C_piperacillin_mg_L`
- `piperacillin_ft_above_MIC`
- `piperacillin_target_attainment`
- `piperacillin_kill_signal`
- `piperacillin_coverage_mod`
- `piperacillin_renal_clearance_factor`
- `pk_crrt_piperacillin_CL_L_min`

## Model scope

The implementation is intentionally qualitative. Piperacillin is represented as a renal-function-dependent one-compartment beta-lactam exposure proxy. Tazobactam is not modelled as a separate PK compartment; it only contributes a small qualitative beta-lactamase-support term.

The pharmacodynamic link is based on the teaching concept that beta-lactam activity is time-dependent and related to the fraction of time above MIC. This is not a clinical dosing model, not a Bayesian forecasting tool and not a substitute for antimicrobial stewardship or therapeutic drug monitoring.

## Coupling

The PharmacologyModule writes antimicrobial coverage signals that the infection module can consume through the shared bus. The new scenario demonstrates dose/exposure → fT>MIC → coverage → infection-response coupling.
