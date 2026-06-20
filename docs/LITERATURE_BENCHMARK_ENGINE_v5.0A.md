# Step 5.0A — Literature Benchmark Engine

## Scope

This step introduces the first v5.0 validation-pack component: a reproducible physiological benchmark engine for selected high-value scenarios.

It is **not** external clinical validation and **not** medical decision support. It is an internal plausibility and regression layer before publication-grade validation work.

## Added files

- `data/literature_benchmark_targets_v5.0A.yaml`
- `tools/literature_benchmark_engine_v5_0A.py`
- `tests/test_v500a_literature_benchmark_engine.py`
- `outputs/literature_benchmark_v5.0A/`

## Benchmarked scenario set

- `healthy_child_20kg`
- `infant_bronchiolitis`
- `epals_v2_septic_shock_warm`
- `epals_v2_dka_dehydration_shock`
- `epals_v2_anaphylactic_shock`

## Benchmark logic

The engine evaluates broad, source-traceable physiological corridors:

- final values for stable scenarios;
- trajectory minimum for variables ending in `_min`;
- trajectory maximum for variables ending in `_max`;
- explicit PASS / REVIEW / NO_DATA status;
- percent deviation from the benchmark corridor.

## Current audit result

Full v5.0A benchmark run:

- benchmark scenarios: 5
- target rows: 18
- missing source rows: 0
- evaluated checks: 18
- pass: 12
- review: 6
- no data: 0

The 6 REVIEW rows are expected at this stage and are used to prioritize 5.0B–5.0D hardening, not as automatic failure of the simulator.

## Command

```bash
python tools/literature_benchmark_engine_v5_0A.py --outdir outputs/literature_benchmark_v5.0A --dt 10
```

## Test command

```bash
pytest -q tests/test_v500a_literature_benchmark_engine.py
```

Result: `3 passed`.
