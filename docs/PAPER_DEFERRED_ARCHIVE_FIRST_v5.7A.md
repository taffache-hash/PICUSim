# Step 5.7A - Paper deferred / archive-preflight correction

Date: 2026-06-20
Status: completed locally; no public upload performed.
Current package version: `3.1-step5.9-final-public-release-candidate`

## Correction

Paper drafts and manuscript files are not authoritative for current package facts. They may contain placeholder or stale scenario/module/drug/test/validation numbers. They must not be used to generate OSF, Zenodo, GitHub release or archive metadata.

## Source of truth

The source of truth for public archive metadata is:

- regenerated release manifest;
- filesystem-derived package counts;
- tested API/UI/model contracts;
- package-facts JSON generated during archive preflight.

## Roadmap impact

The old Step 5.8 manuscript consistency pass is replaced by archive preflight and manifest rebuild. Manuscript/paper cleanup moves after public deposit, once Zenodo DOI, OSF URL and optional GitHub release URL exist.

## Rule

Deposit first, paper last.

