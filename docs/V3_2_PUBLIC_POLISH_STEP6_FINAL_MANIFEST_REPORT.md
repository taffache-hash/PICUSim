# PICUSim v3.2.0 public polish Step 6 — final local manifest and archive preflight

Date: 2026-06-21

Version label: `3.2.0-public-rc2`

This step converts the Step 5 local candidate into a v3.2.0 public release-candidate archive line. No GitHub push and no Zenodo deposition were performed.

## Completed

- Regenerated `VERSION` to `3.2.0-public-rc2`.
- Updated `README.md`, `README_FIRST_START_HERE.txt`, `CITATION.cff`, `CITATION.bib`, `pyproject.toml`, and `.zenodo.json` for v3.2.0 RC2 metadata.
- Preserved the published v3.1 DOI (`10.5281/zenodo.20777589`) as the previous archive DOI only.
- Added `data/release_candidate_manifest_v3.2.0.yaml`.
- Added `metadata/package_facts_v3.2.0.json`.
- Added final manifest/package-facts regression contracts.

## Package counts

```json
{
  "included_file_count": 650,
  "included_total_bytes": 3100815,
  "scenario_yaml_count": 99,
  "test_py_count": 125,
  "module_py_non_init_count": 36,
  "docs_markdown_count": 88,
  "metadata_file_count": 7,
  "output_dir_count": 0
}
```

## Remaining external steps

1. Owner review of the RC2 archive.
2. GitHub release/tag for final v3.2.0.
3. Zenodo new-version deposition.
4. Insert new Zenodo v3.2.0 DOI into `CITATION.cff`, `CITATION.bib`, `README.md`, and `.zenodo.json`.
