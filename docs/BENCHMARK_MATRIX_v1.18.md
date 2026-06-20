# Benchmark matrix v1.18

This update expands the public-clean scenario benchmark layer from the original core scenarios to a broader set of educational scenarios.

The benchmark matrix is a **plausibility and regression dashboard**. It is not external clinical validation, not calibration against patient-level data, and not a clinical decision-support layer.

## Added coverage

New corridors were added for:

- infant bronchiolitis;
- neonatal RDS;
- CRRT-lite drug-clearance scenario;
- vancomycin in AKI/CRRT;
- furosemide fluid overload;
- morphine analgesia with AKI;
- clonidine withdrawal/weaning;
- insulin stress hyperglycemia;
- piperacillin/tazobactam sepsis;
- adrenal shock;
- hemolysis and oxygen transport;
- hypoxic hepatitis;
- hemolysis/bilirubin scenario;
- pulmonary hypertension/iNO.

## Main tool

```bash
python tools/benchmark_matrix_v1_18.py --no-run
python tools/benchmark_matrix_v1_18.py --scenarios infant_bronchiolitis neonatal_rds_3kg --dt 10
```

Outputs are written to:

```text
outputs/benchmark_matrix_v1.18/
```

The tool creates:

```text
benchmark_target_matrix_v118.csv
benchmark_scenario_coverage_v118.csv
benchmark_evaluation_v118.csv
benchmark_matrix_report_v118.md
benchmark_matrix_summary_v118.json
```

## Interpretation

PASS means the final simulated value lies inside a broad literature-anchor or internal plausibility corridor. REVIEW means the output needs inspection. Neither status is clinical validation.
