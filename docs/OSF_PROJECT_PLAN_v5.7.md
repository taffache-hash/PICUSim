# Step 5.7 - OSF project preparation

Date: 2026-06-20
Status: completed locally; no OSF project was created and no upload was performed.
Current package version: `3.1-step5.9-final-public-release-candidate`
Clinical status: not for clinical use.

## Goal

Prepare a reproducible OSF project layout around the software release candidate, validation artifacts, scenario library and supplementary documentation, while keeping Zenodo as the eventual citable software-release archive. Manuscripts/papers are deliberately out of scope until after deposit.

## Current boundary decision

- Zenodo: final immutable software archive after Step 5.9 rebuild and user-controlled deposition.
- OSF: broader project workspace containing validation outputs, scenario library, supplementary documentation and public cross-links. Manuscripts/figures are a post-deposit task.
- GitHub, if used later: live development/release-tag repository, not the only archival source.

## Why this is not uploaded yet

The Step 5.6 Zenodo candidate archive is stale after the Step 5.6A crystalloid infusion-control deviation. The package must be rebuilt and remanifested before any final public upload. The user will personally handle actual public upload/deposition steps.

## Prepared files

- `metadata/osf_project_structure_v5.7.md`
- `metadata/osf_artifact_index_v5.7.json`
- `metadata/osf_artifact_index_v5.7.csv`

## Observed package facts

- YAML scenarios observed: 99
- Python test files observed: 114
- Non-init module files observed under `modules/`: 35
- Output directories observed: 13

## Recommended OSF upload order

1. Create OSF project landing page with title, safety disclaimer and license note.
2. Add component `00_Project_overview_and_safety`.
3. Add component `03_Validation_and_regression_outputs`.
4. Add component `02_Scenario_library`.
5. Add component `04_Methods_and_supplementary_documentation`.
6. Do not add manuscripts yet. Add component `05_Manuscripts_and_figures` only after public deposit and final identifiers exist.
7. After Step 5.9/6.0, add `06_Public_archive_crosslinks` with Zenodo DOI and OSF URL. Manuscript identifiers come later.

## Required OSF landing-page disclaimer

PICUSim / Pediatric Critical Care Sim is educational and research software only. It is not a medical device and is not for clinical use, diagnosis, treatment, prescribing, triage, bedside monitoring, prognostication, device control, patient-specific modelling or patient-care decisions.

## Open decisions before real OSF creation

- final OSF project title;
- author affiliation and ORCID fields;
- manuscript/preprint handling after public deposit and final package-facts manifest;
- whether final code mirror is hosted on GitHub and linked from OSF;
- final Zenodo DOI after Step 5.9 rebuild and deposition.

## Exit status

OSF assembly can be performed reproducibly from the prepared structure and artifact index, but actual public upload must wait until the final release rebuild and user-controlled deposition steps.


## Step 5.7A correction

Manuscripts and paper drafts are not reliable sources for current package counts or archive metadata. They must not be used to decide scenario, module, drug, validation or test counts. The source of truth is the final regenerated manifest plus package-facts JSON produced before public deposit. Paper updates are deferred until after Zenodo/OSF/GitHub identifiers are final.
