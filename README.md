# PICUSim / Pediatric Critical Care Sim

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20777589.svg)](https://doi.org/10.5281/zenodo.20777589)

**Distribution:** v3.2.0 public release package  
**Current package version:** `3.2.0-public`  
**Release status:** final local pre-upload package prepared for GitHub release and Zenodo new-version deposition  
**Current published Zenodo DOI:** `10.5281/zenodo.20777589` for the earlier v3.1-step5.9 public archive  
**Clinical status:** not for clinical use; not a medical device; not a validated patient-specific digital twin.

**Final local package note:** This v3.2.0-public package has not yet been pushed to GitHub or deposited as a new Zenodo version. The new v3.2 DOI must be added only after Zenodo assigns it.

Incorporates RC3 UI branding/cache-busting, BEDSIDE_FAST live fluid/RCP fields, pause race-condition guard, RC2 DKA/pneumothorax fixes, FiO2 persistence fixes, and v3.2 validation/limitations documentation.

PICUSim is a modular pediatric critical-care physiology simulation framework for education, scenario design, in-silico research prototyping, software testing, and hypothesis generation. It is designed around structured YAML scenarios, a shared physiological state bus, coupled organ-system modules, a local FastAPI backend, and a browser-based training console.

The framework is not intended for diagnosis, treatment, prescribing, triage, bedside monitoring, prognostication, device control, or any patient-care decision.

## Current v3.2.0 public state

This v3.2.0 public package starts from the published v3.1-step5.9 public archive line and adds targeted public-use corrections: healthy-child gas-exchange recalibration, short-scenario sepsis/pressor response repair, robust electrolyte-baseline initialization, persistent FiO2 controls across ETT/HFNC/NIV/low-flow interfaces, public-package test cleanup, and softened PaCO2/HR public-display ceilings.

Key release artifacts:

- `docs/RELEASE_CANDIDATE_FREEZE_v5.2.md`
- `data/release_candidate_manifest_v5.2.yaml`
- `docs/REGRESSION_SWEEP_v5.3.md`
- `outputs/regression_sweep_v5.3/regression_summary_v53.json`
- `docs/PUBLICATION_RELEASE_ROADMAP_v5.3_to_v6.0.md`
- `docs/DOCUMENTATION_COHERENCE_AUDIT_v5.4.md`
- `docs/APACHE_LICENSE_CONVERSION_v5.5.md`
- `docs/ZENODO_DEPOSITION_PLAN_v5.6.md`
- `docs/CRYSTALLOID_INFUSION_CONTROLS_v5.6A.md`
- `docs/OSF_PROJECT_PLAN_v5.7.md`
- `docs/PAPER_DEFERRED_ARCHIVE_FIRST_v5.7A.md`
- `docs/ARCHIVE_PREFLIGHT_v5.8.md`
- `docs/FINAL_RELEASE_NOTES_v5.9.md`
- `docs/PUBLIC_ARCHIVE_RELEASE_v6.0.md`
- `data/release_candidate_manifest_v5.9.yaml`
- `data/release_candidate_manifest_v3.2.0.yaml`
- `metadata/package_facts_v3.2.0.json`
- `docs/V3_2_PUBLIC_POLISH_CHECKLIST.md`
- `docs/V3_2_PUBLIC_POLISH_STEP7_RC2_EXTERNAL_REVIEW_FIXES.md`
- `docs/V3_2_PUBLIC_POLISH_STEP9_FINAL_LOCAL_PACKAGE_REPORT.md`
- `docs/V3_2_PUBLIC_POLISH_STEP8_RC3_UI_WS_PAUSE_HOTFIX.md`
- `docs/V3_2_PUBLIC_POLISH_STEP5_PHYSIOLOGY_DOCS_REPORT.md`
- `docs/V3_2_PUBLIC_POLISH_STEP6_FINAL_MANIFEST_REPORT.md`
- `docs/V3_2_PUBLIC_POLISH_STEP7_RC3_EXTERNAL_REVIEW_FIXES.md`
- `docs/VALIDATION.md`
- `docs/LIMITATIONS.md`
- `data/release_candidate_manifest_v5.8.yaml`
- `metadata/package_facts_v5.8.json`
- `metadata/osf_project_structure_v5.7.md`
- `metadata/osf_artifact_index_v5.7.json`
- `metadata/zenodo_metadata_v5.6.yaml`
- `.zenodo.json`
- `LICENSE`
- `NOTICE`

The v5.3 targeted regression sweep executed 126 contract checks after a Windows CLI portability hotfix, with 126 passed and 0 failed. The sweep covered public smoke/API/UI checks, advanced Step 4.39-4.51 engines, RCP/arrhythmia scenarios, the Step 4.38 vasoactive infusion feedback fix, and validation-pack checks from Step 5.0A to Step 5.1D.

## Package contents

The current public package includes:

- 36 non-`__init__` physiological/pharmacological Python module files under `modules/`;
- 99 YAML clinical scenarios under `scenarios/`;
- 126 Python test files under `tests/`;
- 89 markdown technical documents under `docs/`;
- a local FastAPI backend in `api/`;
- a browser-based training console in `ui/`;
- validation, benchmark, Monte Carlo, guardrail, solvability, human-factors, reproducibility, methods and sensitivity-map tooling under `tools/`, `data/`, `docs/` and `outputs/`.

The v3.2.0 public release-candidate counts are filesystem-derived from this package and recorded in `data/release_candidate_manifest_v3.2.0.yaml` and `metadata/package_facts_v3.2.0.json`. They supersede the frozen v3.1-step5.9 package-count snapshot for v3.2 development and should be regenerated only if files are added or removed before the final GitHub/Zenodo release.

## Recommended first read

1. `README_FIRST_START_HERE.txt`
2. `VERSION`
3. `docs/RELEASE_CANDIDATE_FREEZE_v5.2.md`
4. `docs/REGRESSION_SWEEP_v5.3.md`
5. `docs/PUBLICATION_RELEASE_ROADMAP_v5.3_to_v6.0.md`
6. `DISCLAIMER_NOT_FOR_CLINICAL_USE.md`
7. `docs/VALIDATION.md`
8. `docs/LIMITATIONS.md`

## Quick smoke test

From the project folder:

```bash
python run_simulation.py --scenario scenarios/healthy_child_20kg.yaml --dt 2 --no-plot
```

On Windows, this release uses ASCII-safe CLI progress output to avoid default console encoding failures.

## Local API and web console

Start the API server:

```bash
python start_pdt_api.py --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000/monitor
```

API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

## Docker quick start

From the folder containing `docker-compose.yml`:

```bash
docker compose up --build
```

Then open:

```text
http://localhost:8000/monitor
```

See `docs/DOCKER_QUICKSTART_v3.0.md` for Docker persistence and troubleshooting notes. Docker documentation will be refreshed during the Step 5.4/5.9 release-publication cleanup.

## Local Python installation

Python 3.9 or later is required. Python 3.11+ is recommended for modern local development; this regression sweep was executed with Python 3.14.5 on Windows 11.

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

Run tests with pytest when installed:

```bash
python -m pytest -q tests/test_public_smoke.py
python -m pytest -q tests/test_v320_public_polish_contracts.py
python -m pytest -q tests/test_v320_fio2_control_persistence.py
python -m pytest -q tests/test_v320_public_polish_soft_caps_contract.py
```

The Step 5.3 sweep was run with manual contract runners because pytest was not installed in the inspected Python environment. See `docs/REGRESSION_SWEEP_v5.3.md` for details.

## Validation and reproducibility artifacts

Important validation-support layers include:

- Step 5.0A literature benchmark engine;
- Step 5.0B Monte Carlo runner;
- Step 5.0C plausibility guardrails;
- Step 5.0D scenario solvability audit;
- Step 5.0E UI human factors audit;
- Step 5.1A export and reproducibility pack;
- Step 5.1B methods appendix generator;
- Step 5.1D sensitivity maps;
- Step 5.2 release-candidate freeze manifest;
- Step 5.3 regression sweep;
- v3.2.0 public-polish physiology and UI-control regression contracts.

Publication or training runs should preserve session JSON, physiological timeline CSV, intervention log CSV, manifest hashes, methods appendix, and relevant figures/sensitivity summaries.

## Project layout

```text
api/          Local FastAPI backend, session management, debriefing, reproducibility endpoints
apps/         Optional Streamlit app
core/         Shared physiology bus, engine, scenario loading and core utilities
data/         Model registries, templates, benchmark targets, validation specs and release manifests
docs/         User, technical, validation and release documentation
modules/      Physiological and pharmacological simulation modules
outputs/      Generated validation, benchmark and reproducibility outputs
scenarios/    YAML scenario library
tests/        Regression and smoke tests
tools/        Audit, reporting, benchmark and validation-support scripts
ui/           Browser-based local monitor and instructor console
```

## Safety and use constraints

This software is qualitative and semi-mechanistic. It contains empirical assumptions, simplified couplings, proxy indices, heuristic thresholds and scenario-specific calibrations.

Do not use outputs from this software for diagnosis, treatment, prescribing, triage, bedside monitoring, prognostication, device control, or any patient-care decision.

This package is for education, research prototyping, scenario design, software testing and hypothesis generation only.

## License

This release-candidate folder is licensed under Apache License 2.0. See `LICENSE` and `NOTICE`.

The clinical-use restriction remains in force as a safety disclaimer: this software is not a medical device and is not for clinical use. The safety disclaimer is separate from the open-source software license and must remain visible in public archives.

## Citation

Citation metadata is provided in `CITATION.cff` and `CITATION.bib`. The current published v3.1-step5.9 archive DOI is `10.5281/zenodo.20777589`. This v3.2.0 release-candidate should receive a new Zenodo version DOI before being cited as the final software version in a manuscript.

## Paper/manuscript policy

Manuscripts and paper drafts are deferred until after public deposit. Package counts and archive metadata must come from the regenerated release manifest, tests and filesystem-derived package facts, not from paper text.

## Next publication-release steps

See `docs/PUBLICATION_RELEASE_ROADMAP_v5.3_to_v6.0.md`.

Planned sequence:

- Step 5.4 version and documentation coherence cleanup - completed;
- Step 5.5 Apache-2.0 licensing conversion - completed;
- Step 5.6 Zenodo deposition preparation - completed, upload pending but archive stale after Step 5.6A;
- Step 5.6A crystalloid infusion controls - completed;
- Step 5.7 OSF project preparation - completed locally, upload pending;
- Step 5.8 archive preflight / manifest rebuild - completed for v3.1;
- Step 5.9 final public release candidate rebuild - completed for v3.1;
- Step 6.0 public archive release - completed for v3.1 on GitHub/Zenodo;
- v3.2.0 public-polish branch - final local release-candidate built;
- v3.2.0 GitHub release and Zenodo new-version deposition - pending.


