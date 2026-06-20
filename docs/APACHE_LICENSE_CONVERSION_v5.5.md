# Step 5.5 - Apache-2.0 licensing conversion

Date: 2026-06-20
Status: completed for the extracted working release-candidate folder.
Clinical status: not for clinical use.

## Goal

Step 5.5 replaces the pending-license posture with an explicit Apache License 2.0 release-candidate posture while preserving the non-clinical safety disclaimer.

## Source checked

The license text was checked against the Apache Software Foundation Apache License 2.0 text at `https://www.apache.org/licenses/LICENSE-2.0.txt`.

## Files updated

- `LICENSE` added with Apache License 2.0 text and project copyright boilerplate.
- `NOTICE` added with project attribution and non-clinical safety notice.
- `VERSION` updated to `3.1-step5.5-apache-2.0-licensed-release-candidate`.
- `pyproject.toml` updated to package version `3.1.0rc6` and `Apache-2.0` license metadata.
- `CITATION.cff` updated to `Apache-2.0` and the Step 5.5 release-candidate version.
- `CITATION.bib` updated to cite the Apache-2.0 licensed release candidate.
- `README.md` and `README_FIRST_START_HERE.txt` updated to make `LICENSE` and `NOTICE` first-class entrypoints.
- `LICENSE_PENDING.md` retained only as a superseded provenance note.
- `CHANGELOG.md` records the Step 5.5 conversion.

## Deferred intentionally

- Zenodo DOI and metadata deposition: Step 5.6.
- OSF archive layout and reproducibility index: Step 5.7.
- Manuscript DOCX consistency pass: Step 5.8.
- Fresh release manifest and final public zip: Step 5.9.

## Safety note

Apache-2.0 governs software redistribution terms. It does not remove the project safety restriction: PICUSim is not a medical device and is not for clinical use, diagnosis, treatment, prescribing, monitoring, triage, bedside decision support, prognostication, device control, patient-specific modelling, or patient-care decisions.
