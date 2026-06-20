from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def read_text(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_apache_license_files_are_present_and_entrypoints_reference_them():
    license_text = read_text("LICENSE")
    assert "Apache License" in license_text
    assert "Version 2.0, January 2004" in license_text
    assert "Copyright 2026 Paolo Taffache" in license_text

    notice = read_text("NOTICE")
    assert "PICUSim / Pediatric Critical Care Sim" in notice
    assert "Copyright 2026 Paolo Taffache" in notice
    assert "not for clinical use" in notice.lower()

    readme = read_text("README.md")
    assert "licensed under Apache License 2.0" in readme
    assert "See `LICENSE` and `NOTICE`" in readme


def test_package_and_citation_metadata_use_apache_2_0():
    assert read_text("VERSION").strip() == "3.1-step5.9-final-public-release-candidate"

    pyproject = tomllib.loads(read_text("pyproject.toml"))
    assert pyproject["project"]["version"] == "3.1.0rc12"
    assert pyproject["project"]["license"]["text"] == "Apache-2.0"
    assert "LICENSE" in pyproject["project"]["license-files"]
    assert "NOTICE" in pyproject["project"]["license-files"]

    cff = read_text("CITATION.cff")
    assert "3.1-step5.9-final-public-release-candidate" in cff
    assert 'license: "Apache-2.0"' in cff

    bib = read_text("CITATION.bib")
    assert "Apache-2.0 licensed" in bib


def test_license_pending_is_superseded_and_safety_disclaimer_remains():
    pending = read_text("LICENSE_PENDING.md")
    assert "superseded" in pending.lower()
    assert "Apache License 2.0" in pending

    disclaimer = read_text("DISCLAIMER_NOT_FOR_CLINICAL_USE.md")
    assert "not for clinical use" in disclaimer.lower()

    audit = read_text("docs/APACHE_LICENSE_CONVERSION_v5.5.md")
    assert "Status: completed" in audit
    assert "Zenodo" in audit
    assert "OSF" in audit
    assert "Fresh release manifest" in audit
