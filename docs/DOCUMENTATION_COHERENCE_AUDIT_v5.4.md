# Step 5.4 - Documentation and version coherence audit

Date: 2026-06-20
Status: completed for the extracted working release-candidate folder.
Clinical status: not for clinical use.

## Goal

Step 5.4 aligns the package-facing metadata and first-read documents with the current release-candidate state after the Step 5.3 regression sweep. It intentionally does not activate the Apache-2.0 license, create Zenodo/OSF records, edit manuscript DOCX files, or regenerate the final release manifest.

## Files updated

- `VERSION` now reads `3.1-step5.3-regression-swept-release-candidate`.
- `README_FIRST_START_HERE.txt` now points to the release-candidate workflow, v5.2 freeze, v5.3 regression sweep, and v5.3-to-v6.0 publication roadmap.
- `README.md` now describes the current package as a v3.1 regression-swept release candidate and records the current package facts: 35 module files, 99 YAML scenarios, and 117 Python test files after Step 5.8.
- `pyproject.toml` now uses package version `3.1.0rc5`, release-candidate description text, and beta development classifier.
- `CITATION.cff` now names PICUSim / Pediatric Critical Care Sim and uses the current release-candidate version.
- `CITATION.bib` now includes a software release-candidate citation entry and keeps the supporting literature stubs.
- `LICENSE_PENDING.md` now states that Apache-2.0 conversion is planned for Step 5.5 but is not active yet.
- `CHANGELOG.md` now records the Step 5.4 documentation coherence pass.

## Deferred intentionally

- Apache License 2.0 file and final package license metadata: Step 5.5.
- Zenodo metadata, DOI placeholders and deposition checklist: Step 5.6.
- OSF archive layout and reproducibility index: Step 5.7.
- Manuscript DOCX consistency pass: Step 5.8.
- Fresh release manifest and final public zip: Step 5.9.

## Notes

Older roadmap, handoff and release-audit files still contain historical Step 4.x and v3.0-alpha references. Those were not rewritten because they are provenance documents rather than package-entry metadata. The current entry points are `VERSION`, `README_FIRST_START_HERE.txt`, `README.md`, `CITATION.cff`, `CITATION.bib`, `LICENSE_PENDING.md`, the Step 5.2 freeze note, this Step 5.4 audit, and the publication-release roadmap.

The existing `data/release_candidate_manifest_v5.2.yaml` is now stale because Step 5.3 and Step 5.4 changed files after the v5.2 freeze. It must be regenerated during the final public release rebuild.
