from pathlib import Path
import tomllib
import pytest

ROOT = Path(__file__).resolve().parents[1]
if (ROOT / "VERSION").read_text(encoding="utf-8").strip().startswith("3.2.0"):
    pytestmark = pytest.mark.skip(reason="historical v3.1 release metadata contract; superseded by v3.2 public-polish metadata tests")



def read_text(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_package_entrypoints_match_regression_swept_release_candidate():
    assert read_text("VERSION").strip() == "3.1-step5.9-final-public-release-candidate"

    readme_first = read_text("README_FIRST_START_HERE.txt")
    assert "Apache-2.0 release candidate with final public release candidate" in readme_first
    assert "docs/REGRESSION_SWEEP_v5.3.md" in readme_first
    assert "Step 4.13" not in readme_first

    readme = read_text("README.md")
    assert "3.1-step5.9-final-public-release-candidate" in readme
    assert "126 passed and 0 failed" in readme
    assert "not for clinical use" in readme.lower()
    assert "Apache License 2.0" in readme
    assert "LICENSE" in readme
    assert "NOTICE" in readme
    assert "Windows: .venv\\Scripts\\activate" in readme
    assert "\x07" not in readme


def test_package_metadata_and_citation_are_current_but_license_pending():
    pyproject = tomllib.loads(read_text("pyproject.toml"))
    assert pyproject["project"]["version"] == "3.1.0rc12"
    assert "final public release candidate" in pyproject["project"]["description"]
    assert "Development Status :: 4 - Beta" in pyproject["project"]["classifiers"]

    cff = read_text("CITATION.cff")
    assert "PICUSim / Pediatric Critical Care Sim" in cff
    assert "3.1-step5.9-final-public-release-candidate" in cff
    assert 'license: "Apache-2.0"' in cff

    pending = read_text("LICENSE_PENDING.md")
    assert "License status superseded" in pending
    assert "Apache License 2.0" in pending
    assert "LICENSE" in pending
    assert "NOTICE" in pending


def test_step54_audit_records_deferred_publication_work():
    audit = read_text("docs/DOCUMENTATION_COHERENCE_AUDIT_v5.4.md")
    assert "Status: completed" in audit
    assert "Step 5.5" in audit
    assert "Step 5.6" in audit
    assert "Step 5.7" in audit
    assert "Step 5.8" in audit
    assert "Step 5.9" in audit
    assert "manifest_v5.2.yaml` is now stale" in audit
