# Distribution checklist — v3.0-alpha

Before public or semi-public distribution, verify:

- [ ] A final license has been selected, or `LICENSE_PENDING.md` is intentionally retained.
- [ ] Clinical-use disclaimer is present in README and package root.
- [ ] `VERSION` matches `pyproject.toml`, `CITATION.cff`, API health output and release notes.
- [ ] `docker compose up --build` starts successfully on a clean machine.
- [ ] `http://localhost:8000/monitor` opens.
- [ ] `http://localhost:8000/health` returns status `ok`.
- [ ] Public smoke tests pass.
- [ ] No private files, generated outputs, patient data or local cache folders are included.
- [ ] Zenodo/OSF/GitHub release metadata match the selected release tag.

Recommended release tag:

```text
v3.0-alpha
```
