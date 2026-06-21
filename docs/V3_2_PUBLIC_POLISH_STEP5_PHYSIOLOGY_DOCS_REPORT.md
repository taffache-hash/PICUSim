# v3.2.0 public-polish Step 5 report — soft caps, README/CITATION and validation docs

## Scope

This step continues the local v3.2.0 public-polish branch after Step 4 test hygiene and Step 3 FiO2 persistence fixes.

## Changes made

### Physiological display polish

- Added a soft PaCO2 upper transition in `modules/respiratory/gas_exchange.py` so severe scenarios no longer repeatedly converge to the old public-demo wall of PaCO2 = 105 mmHg.
- Added a visible HR reserve below age-group absolute safety ceilings in `modules/cardiovascular/baroreflex.py` so summaries no longer repeatedly print exact ceilings such as 180, 210 or 220 bpm.
- Preserved severe physiology in bronchiolitis, near-fatal asthma, sepsis, neonatal RDS and excessive-PEEP ARDS.

### Documentation and metadata

- Updated `README.md` for the local v3.2.0 public-polish candidate.
- Updated `CITATION.cff` and `CITATION.bib` for the local candidate while avoiding a false new DOI claim before Zenodo deposition.
- Updated `VERSION` to `3.2.0-public-polish-step5-local`.
- Updated `pyproject.toml` to `3.2.0rc1` for local package coherence.
- Added `docs/VALIDATION.md`.
- Added `docs/LIMITATIONS.md`.
- Updated `CHANGELOG.md`.

### Tests

- Added `tests/test_v320_public_polish_soft_caps_contract.py`.

## Targeted test results

- `tests/test_public_smoke.py`: 2 passed.
- `tests/test_v320_public_polish_contracts.py`: 4 passed.
- `tests/test_v320_public_polish_deviation_contracts.py`: 5 passed.
- `tests/test_v320_fio2_control_persistence.py`: 5 passed.
- `tests/test_v320_public_package_regression_cleanup.py`: 5 passed.
- `tests/test_v320_public_polish_soft_caps_contract.py`: 4 passed.
- ETCO2/RR/shock/ScvO2/plausibility block: 17 passed, 1 skipped.
- API/UI/emogas/monitor block: 11 passed.

## Remaining checklist

- Run a broader slow-suite pass when runtime allows.
- Regenerate final package facts and release manifest only after all v3.2.0 changes are frozen.
- Update `.zenodo.json` with the final v3.2.0 version DOI only after creating the Zenodo new version.
- Generate final archive and checksum.
- Re-test the final extracted archive.
