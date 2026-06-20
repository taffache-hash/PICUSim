# Step 5.6 - Zenodo deposition preparation

Date: 2026-06-20
Status: completed for the extracted working release-candidate folder; upload not performed.
Clinical status: not for clinical use.

## Goal

Prepare a citable archival software release candidate for Zenodo while avoiding premature DOI claims.

## Deposit scope

Primary Zenodo object: software archive only.

Included in the archive:

- source code, modules, scenarios, API and UI files;
- validation, benchmark, Monte Carlo, guardrail, solvability, human-factors and reproducibility outputs already present in the release-candidate folder;
- release-candidate freeze, regression, documentation-coherence and Apache-2.0 licensing documents;
- `README.md`, `README_FIRST_START_HERE.txt`, `DISCLAIMER_NOT_FOR_CLINICAL_USE.md`, `CITATION.cff`, `CITATION.bib`, `LICENSE`, `NOTICE`, `.zenodo.json` and metadata files.

Excluded from the archive:

- `.git`, `.agents`, `.codex` and local Codex/cache metadata;
- `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.venv`, `node_modules`, desktop/system files and nested zip archives;
- manuscripts and paper drafts. Papers are post-deposit artifacts and must not supply archive counts or metadata.

## Metadata prepared

- `metadata/zenodo_metadata_v5.6.yaml`
- `.zenodo.json`

The metadata uses Apache-2.0, open access, software upload type, current Step 5.6 version label, and explicit not-for-clinical-use language. DOI, ORCID, affiliation and final related identifiers remain intentionally blank or marked pending until actual deposition.

## Candidate archive

- Archive: `outputs/release_archives/pediatric_critical_care_sim_v3.1_step5.6_zenodo_candidate.zip`
- SHA256: recorded in `outputs/release_archives/pediatric_critical_care_sim_v3.1_step5.6_zenodo_candidate.zip.sha256`
- Archive includes reproducibility outputs: yes
- Archive excludes transient caches: yes

## Open decisions before upload

1. Confirm author affiliation and ORCID.
2. Decide whether Zenodo should link OSF at first upload or after Step 5.7 creates the OSF structure.
3. Do not link manuscript records until journal/preprint identifiers exist after deposit.
4. Regenerate the final release manifest before public upload; paper cleanup is later and must use manifest-derived facts.

## Exit status

Zenodo upload can be performed without new software-content decisions, but final author identity fields and public related identifiers still need confirmation at deposition time.

## Step 5.7A correction

The initial Zenodo metadata draft must be treated as software/archive metadata only. Manuscript/paper numbers are not authoritative and must not be copied into Zenodo or OSF metadata.
