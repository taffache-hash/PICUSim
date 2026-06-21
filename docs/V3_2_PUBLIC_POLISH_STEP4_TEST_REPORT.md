# PICUSim v3.2.0 public polish Step 4 test report

## Scope

This step focused on public-package test hygiene and regression cleanup after the Step 3 FiO2 persistence fix. The intent was not to change public documentation metadata yet. `README.md` and `CITATION.cff` were left unchanged.

## Changes made

1. Repository-only release archive tests now skip cleanly when nested release ZIP/checksum payloads are absent from the distributed source package.
2. Frozen Step 5.8 manifest facts now remain historical snapshots while allowing the v3.2 public-polish branch to add new modules/tests/docs.
3. Older UI snapshot tests were reconciled with the later panel-gated full-profile autorefresh used by emogas and extended-monitor panels.
4. Generated Monte Carlo output files are optional in source-package guardrail tests; the guardrail runner is still tested with synthetic data.
5. A stale hard-coded historical version assertion was removed from the native ScvO2 contract.
6. A new meta-regression test was added: `tests/test_v320_public_package_regression_cleanup.py`.

## Tests run in this step

| Block | Result |
|---|---:|
| Consolidated public-polish/package-policy/API/UI suite | 57 passed, 4 skipped |
| Public-package regression cleanup contract | 5 passed |
| Release archive / preflight tests | 6 passed, 3 skipped |
| Extended monitor / popup chart / emogas autorefresh reconciliation | 9 passed |
| UI/RCP/audio/session contract block | 53 passed |
| Step 4.39-4.51 physiology/engine block | 35 passed |
| Step 5 documentation/audit block | 35 passed, 1 skipped |
| v3.2 FiO2 / shock / public-polish contracts | included in consolidated suite, passing |

## Skips are intentional

The skipped tests correspond to artifacts that should not exist inside the distributed public source package:

- nested release ZIP/checksum files under `outputs/release_archives/`
- generated Monte Carlo output CSVs under `outputs/monte_carlo_v5.0B/`

These tests still execute when those artifacts are present in a full repository/build workspace.

## Remaining technical risks

- Several severe respiratory scenarios still visibly hit high PaCO2 / low pH limits.
- Severe pediatric/neonatal scenarios still often show HR at ceiling values.
- A true final release archive/checksum has not yet been regenerated for v3.2.0-public.
- Final README/CITATION/BibTeX/Zenodo metadata are intentionally deferred.
