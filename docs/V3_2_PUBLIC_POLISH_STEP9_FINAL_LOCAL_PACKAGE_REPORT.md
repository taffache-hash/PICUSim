# V3.2 public polish Step 9 — final local package cleanup

Status: local `3.2.0-public` package prepared for owner review, GitHub release, and Zenodo new-version deposition. No GitHub or Zenodo upload was performed in this step.

## Changes

- Promoted metadata from `3.2.0-public-rc3` to `3.2.0-public`.
- Updated UI script cache-busting suffixes to `v=3.2.0-public`.
- Regenerated `VERSION`, README, README-first, CITATION.cff, CITATION.bib, pyproject and `.zenodo.json` for the final local package label.
- Regenerated v3.2.0 filesystem package facts and release manifest after RC3 hotfixes.
- Kept the previous v3.1 DOI (`10.5281/zenodo.20777589`) as an `isNewVersionOf` reference only. No false v3.2 DOI is claimed before Zenodo assigns one.
- Generated a final local archive and SHA256 checksum.

## Remaining release actions

1. Owner manual UI review.
2. Commit source to GitHub.
3. Create GitHub tag/release `v3.2.0-public`.
4. Use Zenodo **New version** from the previous record.
5. Insert the newly assigned v3.2 DOI in README/CITATION/.zenodo.json if desired after deposition.
