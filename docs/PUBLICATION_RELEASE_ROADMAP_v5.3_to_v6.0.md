# PICUSim publication release roadmap v5.3 to v6.0

Status: modified after Step 5.6A crystalloid-infusion deviation and Step 5.7A archive-first/paper-deferred correction.

This roadmap supersedes feature expansion until the release candidate has passed regression, documentation coherence checks and public-archive preparation. Step 5.6A is the only active model/UI deviation currently accepted after the initial archive-preparation pass. Manuscripts/papers are explicitly not a source of truth for package counts or archive metadata; they are deferred until after final deposit identifiers exist. The project remains educational/research software only, not for clinical use.

## Step 5.3 - Release candidate regression sweep

Goal: verify that the v5.2 release candidate is internally executable and has not regressed after the publication-freeze packaging step.

Required checks:
- run the full targeted contract suite used for the v5.2 freeze;
- rerun public smoke, API server, UI static contracts and scenario catalog smoke tests;
- rerun validation-pack tests for 5.0A to 5.1D;
- rerun vasoactive infusion feedback regression from step 4.38;
- verify `data/release_candidate_manifest_v5.2.yaml` exists and matches the frozen package scope;
- record exact commands, Python version, platform and pass/fail counts.

Deliverables:
- `docs/REGRESSION_SWEEP_v5.3.md`;
- `outputs/regression_sweep_v5.3/` with machine-readable test summaries when practical;
- updated `CHANGELOG.md`;
- if any file changes are needed, a new release manifest must be generated.

Exit criteria:
- no critical test failures;
- all scenario catalog smoke tests pass or are explicitly documented as known limitations;
- no silent model, UI, scenario, validation or export behavior changes.

## Step 5.4 - Version and documentation coherence cleanup

Goal: make the package self-consistent for readers, reviewers and future users.

Required cleanup:
- align `VERSION`, zip filename, release manifest and documentation around the same release label;
- replace stale `README_FIRST_START_HERE.txt` content that still references older Step 4.13 instructions;
- update `README.md`, quickstart and Docker/start commands to the current release candidate;
- remove or clearly label stale/generated cache artifacts where appropriate;
- verify that all safety statements consistently say educational/research simulation only, not for clinical use;
- record that package facts must come from manifest/tests/filesystem, not from manuscripts.

Deliverables:
- `docs/DOCUMENTATION_COHERENCE_AUDIT_v5.4.md`;
- updated `README_FIRST_START_HERE.txt`;
- updated `README.md`;
- updated `VERSION`;
- updated release manifest if any file changes are made.

Exit criteria:
- a new user opening the zip sees one coherent version and one coherent start path;
- no document points to an obsolete port, cache URL, version, scenario count or validation state.

## Step 5.5 - Apache-2.0 licensing conversion

Goal: replace the pending-license state with an explicit Apache License 2.0 release posture.

Required work:
- replace or supersede `LICENSE_PENDING.md` with an Apache-2.0 `LICENSE` file;
- add a short `NOTICE` file if attribution or institutional notices are needed;
- update `README.md`, `CITATION.cff`, `CITATION.bib` and package metadata to state Apache-2.0; do not edit manuscript text in this step;
- review third-party dependencies for license compatibility and document any caveats;
- ensure the not-for-clinical-use disclaimer remains separate from the open-source license.

Deliverables:
- `LICENSE`;
- optional `NOTICE`;
- `docs/LICENSE_REVIEW_v5.5.md`;
- updated citation and README metadata;
- updated release manifest.

Exit criteria:
- no remaining ambiguity between pending license and Apache-2.0;
- no safety disclaimer is presented as a license restriction.

## Step 5.6 - Zenodo deposition preparation

Goal: prepare a citable archival software release.

Required work:
- create a clean release archive excluding transient caches where appropriate;
- ensure `CITATION.cff`, `CITATION.bib`, author list, affiliations, keywords and abstract are complete;
- draft Zenodo metadata: title, creators, ORCID fields, description, keywords, license, related identifiers and version;
- decide that the first DOI should point to the software archive; manuscript/preprint links are deferred until after public identifiers exist;
- verify the archive includes reproducibility outputs required by the v5.2 freeze rules.

Deliverables:
- `docs/ZENODO_DEPOSITION_PLAN_v5.6.md`;
- `metadata/zenodo_metadata_v5.6.yaml` or equivalent;
- final candidate archive name and checksum;
- updated release manifest.

Exit criteria:
- Zenodo upload can be performed without needing new content decisions.

## Step 5.6A - Crystalloid infusion controls deviation

Goal: close the missing bedside fluid-resuscitation control gap before public archive assembly.

Required work:
- add user-controlled crystalloid type and infusion rate in mL/h;
- support normal saline, Ringer lactate, Sterofundin and 5% dextrose;
- route crystalloid rate through the fluid-balance engine, not drug PK;
- expose a main-page `Flebo` control plus a fluid section in the infusions panel;
- keep hemodynamic and renal effects bounded and conditional on fluid responsiveness, hypovolemia, leak and overload;
- document that the previous Step 5.6 Zenodo archive is stale after this code/UI deviation.

Deliverables:
- `docs/CRYSTALLOID_INFUSION_CONTROLS_v5.6A.md`;
- `tests/test_v56a_crystalloid_fluids_contract.py`;
- updated `VERSION`, README, changelog and metadata;
- later archive/manifest regeneration before upload.

Exit criteria:
- API accepts crystalloid type/rate and round-trips controls;
- UI exposes a main-page fluid control;
- fluid balance, cumulative crystalloid input and bounded response markers are test-covered;
- no public upload uses the stale Step 5.6 archive.

## Step 5.7 - OSF project preparation

Goal: prepare the broader project repository around code, validation artifacts, scenario library and supplementary materials, without using manuscript text or paper numbers as source data.

Required work:
- define OSF component structure for software, validation outputs, scenario library and supplementary material; keep manuscripts out until after deposit;
- decide what belongs in OSF versus Zenodo;
- add project-level README and not-for-clinical-use disclaimer;
- prepare data dictionary or artifact index for validation outputs;
- cross-link Zenodo DOI and OSF project pages after deposit; manuscript links are later.

Deliverables:
- `docs/OSF_PROJECT_PLAN_v5.7.md`;
- `metadata/osf_project_structure_v5.7.md`;
- artifact index for upload.

Exit criteria:
- OSF project can be assembled reproducibly from local files with clear component names and descriptions.

## Step 5.8 - Archive preflight and manifest rebuild

Goal: prepare the real source-of-truth package facts before any public deposit or paper update.

Required work:
- regenerate package counts from filesystem and tests, not from manuscripts;
- regenerate release manifest after Step 5.6A and Step 5.7A changes;
- mark stale Step 5.6 Zenodo archive as superseded;
- rerun regression subset needed for code/UI/archive changes;
- prepare a package-facts table for later manuscripts, but do not edit manuscripts yet.

Deliverables:
- `data/release_candidate_manifest_v5.8.yaml`;
- `docs/ARCHIVE_PREFLIGHT_v5.8.md`;
- `metadata/package_facts_v5.8.json`;
- updated changelog and tests.

Exit criteria:
- archive metadata and package counts are internally generated and ready for final public rebuild.

## Step 5.9 - Final public release candidate rebuild

Goal: rebuild a clean public-release archive after regression, documentation, licensing and archive-preparation updates.

Required work:
- regenerate release manifest;
- rerun regression sweep subset required after documentation/licensing changes;
- verify archive contents and checksums;
- prepare release notes.

Deliverables:
- final public release zip;
- `data/release_candidate_manifest_v5.9.yaml`;
- `docs/FINAL_RELEASE_NOTES_v5.9.md`.

Exit criteria:
- package is ready for upload to Zenodo/OSF. Manuscript data/code availability statements are still deferred until public identifiers exist.

## Step 6.0 - Public archive release

Goal: publish the software and supporting material.

Required work:
- upload final archive to Zenodo and reserve/publish DOI;
- assemble OSF project with agreed components;
- update README and citation files with final persistent identifiers; manuscripts remain deferred until after deposit is complete;
- tag the release if a Git repository is used;
- preserve the frozen package and manifest as the source of truth.

Deliverables:
- Zenodo DOI;
- OSF project URL;
- updated citation metadata;
- `docs/PUBLIC_ARCHIVE_RELEASE_v6.0.md`.

Exit criteria:
- an external reviewer can locate the exact software, documentation and validation artifacts from stable public links. Manuscripts/papers are updated only after these links are final.


## Step 6.1 - Manuscript and paper consistency pass

Goal: update papers only after Zenodo/OSF/GitHub/public archive identifiers and package facts are final.

Required work:
- replace placeholders and author/correspondence metadata;
- update scenario/module/drug/test/validation counts from final manifest and package-facts JSON only;
- update data/code availability statements with final Zenodo DOI, OSF URL and optional GitHub release URL;
- ensure claims do not imply clinical validation, medical-device status or bedside decision support;
- keep paper text out of the archive-generation source-of-truth loop.

Exit criteria:
- manuscripts can be submitted using final archive identifiers and final manifest-derived package facts.
