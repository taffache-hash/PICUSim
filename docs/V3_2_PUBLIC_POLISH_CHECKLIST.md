# PICUSim v3.2.0 public polish checklist

Status after publication. This checklist tracks the v3.2.0-public preparation branch through GitHub release and Zenodo new-version deposition.

## Documentation policy

- [x] README and CITATION were preserved during early public-polish steps.
- [x] README, CITATION.cff and CITATION.bib were updated in Step 5 after the user authorized metadata updates.
- [x] CHANGELOG.md is updated after each local step.
- [x] The v3.1 published DOI is retained as the previous archive DOI.
- [x] The final v3.2.0 Zenodo DOI is recorded after deposition: `10.5281/zenodo.20782468`.

## Completed in Steps 1-3

- [x] Recalibrate `healthy_child_20kg` so room-air FiO2 with PEEP does not cause severe desaturation.
- [x] Add lightweight shock labels without reactivating the older hemodynamic shock modifier.
- [x] Preserve electrolyte baselines during acid-base initialization.
- [x] Preserve explicit `set_antibiotic_effect` timeline actions.
- [x] Improve short-horizon septic shock norepinephrine response.
- [x] Add `Paw_display` / `Paw_mean` for stable numeric display while retaining instantaneous `Paw`.
- [x] Fix FiO2 persistence for ETT, HFNC, low-flow oxygen and NIV interfaces.
- [x] Distinguish set FiO2 from delivered FiO2.

## Completed in Step 4

- [x] Convert repository-only nested archive tests to skip when the public source package intentionally excludes nested ZIP/checksum artifacts.
- [x] Keep frozen Step 5.8 manifest counts as historical facts while allowing later public-polish source growth.
- [x] Reconcile stale snapshot-only UI tests with later panel-gated full-profile autorefresh.
- [x] Make generated Monte Carlo output artifacts optional in public source-package guardrail tests.
- [x] Remove stale hard-coded historical version assertion from native ScvO2 contract.
- [x] Add regression test coverage for the public-package test policy.

## Completed in Step 5

- [x] Reduce visible PaCO2/pH cap behavior in bronchiolitis/asthma/severe shock scenarios.
- [x] Reduce visible HR ceiling behavior in severe pediatric/neonatal scenarios.
- [x] Add `VALIDATION.md` with golden-scenario expected-vs-observed table.
- [x] Add `LIMITATIONS.md` with explicit non-clinical boundary.
- [x] Update `VERSION`, `pyproject.toml`, README, CITATION.cff and BibTeX for the local v3.2.0 public-polish candidate.

## Still pending before v3.2.0-public

- [x] Regenerate final filesystem package facts and v3.2.0 release manifest after all source changes are frozen.
- [x] Decide final release label/tag: `v3.2.0-public`.
- [x] Update `.zenodo.json` only after the final release metadata and new Zenodo version DOI are known.
- [x] Generate final public archive/checksum once the source tree is stable.
- [x] Run final release package tests against the generated final archive.
- [x] Create new GitHub release/tag and new Zenodo version only after final validation.

## Current testing note

Full monolithic `pytest` remains too slow for the sandbox timeout because several historical simulation/audit files are long-running. Step 4 therefore uses targeted regression blocks and source-package policy checks. The final release should still run a complete local/CI test matrix outside the constrained sandbox before GitHub/Zenodo upload.


## Step 6 status

- Version label: `3.2.0-public`
- Manifest: `data/release_candidate_manifest_v3.2.0.yaml`
- Package facts: `metadata/package_facts_v3.2.0.json`
- Archive filename target: `PICUSim_v3.2.0_public_local_archive.zip`
- GitHub release: `https://github.com/taffache-hash/PICUSim/releases/tag/v3.2.0-public`
- Zenodo DOI: `10.5281/zenodo.20782468`
- OSF project: `https://osf.io/etj8w/`
