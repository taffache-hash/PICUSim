# Step 5.9 - Final Public Release Candidate Rebuild

Status: completed locally on 2026-06-20. No GitHub, Zenodo or OSF upload was performed.

Current package version: `3.1-step5.9-final-public-release-candidate`

## What this release candidate contains

This package is the post-regression, Apache-2.0, archive-preflight public release candidate for PICUSim / Pediatric Critical Care Sim. It includes the local FastAPI backend, browser training console, physiology/pharmacology modules, scenario library, validation artifacts, documentation, citation metadata, OSF/Zenodo preparation metadata and safety disclaimers.

## Package facts

The filesystem-derived package facts at rebuild time are:

- scenario YAML files: 99
- Python test files: 118
- non-init module Python files under `modules/`: 35
- markdown technical documents under `docs/`: 79
- metadata files under `metadata/`: 6
- output subdirectories under `outputs/`: 13

The Step 5.8 package facts remain the source table for manuscript drafting later, but manuscripts/papers are still deferred until after public identifiers exist.

## Archive policy

The stale Step 5.6 archive is retained for provenance only and is not for upload. The Step 5.9 archive excludes transient caches, local logs, nested release zip files, virtual environments and compiled Python files.

## Still pending before public citation text

- actual Zenodo upload and DOI assignment;
- OSF project assembly and URL;
- optional GitHub repository/tag publication;
- final update of manuscript data/code availability statements after stable identifiers exist.