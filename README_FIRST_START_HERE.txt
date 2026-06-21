PICUSim / Pediatric Critical Care Sim 3.2.0-public

Status: final local pre-upload public package for education/research publication preparation.
Clinical status: NOT FOR CLINICAL USE. Not a medical device. Do not use for diagnosis, treatment, triage, prescribing, monitoring, prognostication, device control, or bedside decision support.

Recommended first checks
1. Read VERSION.
2. Read README.md.
3. Read LICENSE and NOTICE.
4. Read DISCLAIMER_NOT_FOR_CLINICAL_USE.md.
5. Read docs/VALIDATION.md.
6. Read docs/LIMITATIONS.md.
7. Read data/release_candidate_manifest_v3.2.0.yaml.
8. Read metadata/package_facts_v3.2.0.json.
9. Read CHANGELOG.md.

Local Python quick smoke
  python run_simulation.py --scenario scenarios/healthy_child_20kg.yaml --dt 2 --no-plot

Local API / console
  python start_pdt_api.py --host 127.0.0.1 --port 8000
  open http://127.0.0.1:8000/monitor

Docker quick start
  docker compose up --build
  open http://localhost:8000/monitor

Previous published archive
  v3.1-step5.9 Zenodo DOI: 10.5281/zenodo.20777589

Current note
  This 3.2.0-public package has not yet been pushed to GitHub or deposited as a new Zenodo version. Add the new v3.2 DOI only after Zenodo assigns it.
