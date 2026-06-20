PICUSim / Pediatric Critical Care Sim v3.1 - Apache-2.0 release candidate with final public release candidate

Status: release candidate for education/research publication preparation.
Clinical status: NOT FOR CLINICAL USE. Not a medical device. Do not use for diagnosis, treatment, triage, prescribing, monitoring, prognostication, device control, or bedside decision support.

Recommended first checks
1. Read VERSION.
2. Read README.md.
3. Read LICENSE and NOTICE.
4. Read docs/RELEASE_CANDIDATE_FREEZE_v5.2.md.
5. Read docs/REGRESSION_SWEEP_v5.3.md.
6. Read docs/PUBLICATION_RELEASE_ROADMAP_v5.3_to_v6.0.md before changing files.
7. Read docs/ZENODO_DEPOSITION_PLAN_v5.6.md before public deposition.
8. Read docs/CRYSTALLOID_INFUSION_CONTROLS_v5.6A.md for the fluids deviation.
9. Read docs/OSF_PROJECT_PLAN_v5.7.md before OSF assembly.
10. Read docs/ARCHIVE_PREFLIGHT_v5.8.md and metadata/package_facts_v5.8.json before rebuilding a public archive.
11. Read docs/FINAL_RELEASE_NOTES_v5.9.md and data/release_candidate_manifest_v5.9.yaml before upload.

Local Python quick smoke
  python run_simulation.py --scenario scenarios/healthy_child_20kg.yaml --dt 2 --no-plot

Local API / console
  python start_pdt_api.py --host 127.0.0.1 --port 8000
  open http://127.0.0.1:8000/monitor

Docker quick start
  docker compose up --build
  open http://localhost:8000/monitor

Regression note
The v5.3 targeted regression sweep passed after an ASCII-safe CLI output hotfix. See docs/REGRESSION_SWEEP_v5.3.md and outputs/regression_sweep_v5.3/regression_summary_v53.json.

Next planned work
Step 5.4 documentation/version coherence cleanup completed, Step 5.5 Apache-2.0 licensing conversion completed, Step 5.6 Zenodo deposition preparation completed locally, Step 5.7 OSF project preparation completed locally, Step 5.8 archive preflight / manifest rebuild completed locally, Step 5.9 final public release rebuild completed locally, Step 6.0 public archive release remains pending.

Paper note: manuscripts/papers are deliberately deferred until after final public deposit. Do not use paper numbers as package facts.


