# OSF project structure v5.7

Status: prepared locally; no OSF upload performed.
Clinical status: not for clinical use.

## Recommended OSF components

### 00_Project_overview_and_safety

Purpose: Project landing material, license, citation metadata, safety disclaimer and start-here instructions.

Upload priority: required

Local paths:
- `README_FIRST_START_HERE.txt`
- `README.md`
- `DISCLAIMER_NOT_FOR_CLINICAL_USE.md`
- `LICENSE`
- `NOTICE`
- `CITATION.cff`
- `CITATION.bib`
- `VERSION`
- `CHANGELOG.md`

### 01_Software_release_candidate

Purpose: Exact software working tree or final regenerated release archive. Zenodo should remain the citable software-release source of truth; OSF should mirror or point to it.

Upload priority: required after Step 5.9 rebuild

Local paths:
- `core/`
- `modules/`
- `api/`
- `ui/`
- `tools/`
- `data/`
- `requirements.txt`
- `pyproject.toml`

### 02_Scenario_library

Purpose: YAML scenario catalog for educational/research simulation runs.

Upload priority: required

Local paths:
- `scenarios/`

Current count: 99

### 03_Validation_and_regression_outputs

Purpose: Regression, benchmark, Monte Carlo, plausibility, solvability, human-factors, sensitivity-map and reproducibility outputs.

Upload priority: required

Local paths:
- `outputs/`
- `docs/REGRESSION_SWEEP_v5.3.md`
- `docs/DOCUMENTATION_COHERENCE_AUDIT_v5.4.md`
- `docs/CRYSTALLOID_INFUSION_CONTROLS_v5.6A.md`

### 04_Methods_and_supplementary_documentation

Purpose: Methods appendix artifacts, model limitations, module docs, quickstarts and supplementary technical notes.

Upload priority: required

Local paths:
- `docs/`
- `metadata/`

### 05_Manuscripts_and_figures

Purpose: Cureus/JMIR manuscripts, figures and submission supplements after public deposit and final package-facts manifest. Do not use paper numbers as source metadata.

Upload priority: deferred until after Step 6.0 public deposit

Local paths:
- `PICUSim_Cureus_TechnicalReport_v2.docx (external root Drive)`
- `PICUSim_JMIR_MedEd_manuscript_v3.docx (external root Drive)`
- `figures/ if created`

### 06_Public_archive_crosslinks

Purpose: Final Zenodo DOI, OSF project URL, manuscript identifiers and release notes after Step 6.0.

Upload priority: deferred until identifiers exist

Local paths:
- `metadata/zenodo_metadata_v5.6.yaml`
- `.zenodo.json`
- `future public identifiers`


## OSF versus Zenodo boundary

Zenodo should be the citable immutable software-release archive once the final package is rebuilt. OSF should organize validation outputs, scenario library, supplementary documentation and public cross-links. Manuscripts/figures are added only after deposit and must use final manifest-derived facts.

Do not upload the stale Step 5.6 Zenodo candidate archive as final public software after the Step 5.6A crystalloid deviation. Regenerate the archive and manifest later.
