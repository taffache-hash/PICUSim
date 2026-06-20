# Step 5.8 - Archive Preflight and Manifest Rebuild

Status: completed locally on 2026-06-20. No GitHub, Zenodo or OSF upload was performed.

Current package version: `3.1-step5.8-archive-preflight-manifest`

## Purpose

Step 5.8 rebuilds the package facts and manifest after the Step 5.6A crystalloid-control deviation and the Step 5.7A paper-deferred correction. The source of truth is the local filesystem and test tree, not manuscript or paper text.

## Generated facts

- scenario YAML files: 99
- Python test files: 117
- non-init module Python files under `modules/`: 35
- markdown technical documents under `docs/`: 78
- metadata files under `metadata/`: 6
- output subdirectories under `outputs/`: 13

Machine-readable facts are in `metadata/package_facts_v5.8.json`. The archive-facing manifest is in `data/release_candidate_manifest_v5.8.yaml`.

## Superseded archive

The previous archive `outputs/release_archives/pediatric_critical_care_sim_v3.1_step5.6_zenodo_candidate.zip` is retained for provenance but is superseded and must not be uploaded. It was generated before:

- Step 5.6A crystalloid/fluid infusion controls;
- Step 5.7A deposit-first / paper-last correction;
- Step 5.8 package-facts and manifest rebuild.

Known checksum for the superseded archive:

```text
02456548893e05700baa9116f31bc1207adb1d8d54033d35aeae86d3c54a6ece
```

## Public archive exclusions

The final Step 5.9 release archive should exclude transient development material and stale zip files:

- `.git/`, `.agents/`, `.codex/`;
- `.pytest_cache/`, `__pycache__/`, `.mypy_cache/`;
- virtual environments and `node_modules/`;
- local server logs;
- `outputs/release_archives/*.zip`;
- compiled Python artifacts.

## Exit criteria

- package facts are generated from the filesystem/tests;
- manuscripts remain deferred until after public deposit identifiers exist;
- the Step 5.6 archive is explicitly marked superseded;
- Step 5.9 can rebuild a clean final archive from this state.
