"""v3.2 public-polish metadata and documentation contracts."""

from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.2.0-public"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_v320_public_polish_version_and_readme_are_current():
    assert read("VERSION").strip() == VERSION
    readme = read("README.md")
    assert VERSION in readme
    assert "v3.2.0 public" in readme
    assert "Current published Zenodo DOI" in readme
    assert "10.5281/zenodo.20782468" in readme
    assert "Previous v3.1-step5.9 Zenodo DOI" in readme
    assert "https://github.com/taffache-hash/PICUSim/releases/tag/v3.2.0-public" in readme
    assert "not for clinical use" in readme.lower()
    assert "docs/VALIDATION.md" in readme
    assert "docs/LIMITATIONS.md" in readme
    assert "docs/V3_2_PUBLIC_POLISH_STEP7_RC2_EXTERNAL_REVIEW_FIXES.md" in readme


def test_v320_public_polish_citation_records_final_doi_after_deposition():
    cff = read("CITATION.cff")
    assert VERSION in cff
    assert 'license: "Apache-2.0"' in cff
    assert 'repository-code: "https://github.com/taffache-hash/PICUSim"' in cff
    assert 'doi: "10.5281/zenodo.20782468"' in cff
    assert "Previous published v3.1-step5.9 DOI" in cff

    bib = read("CITATION.bib")
    assert "picusim2026v320public" in bib
    assert "picusim2026v31archive" in bib
    assert "10.5281/zenodo.20782468" in bib
    assert "10.5281/zenodo.20777589" in bib
    assert "not for clinical use" in bib


def test_v320_public_polish_pyproject_and_docs_are_coherent():
    project = tomllib.loads(read("pyproject.toml"))["project"]
    assert project["version"] == "3.2.0"
    assert project["license"]["text"] == "Apache-2.0"
    assert "not for clinical use" in project["description"]

    validation = read("docs/VALIDATION.md")
    limitations = read("docs/LIMITATIONS.md")
    report = read("docs/V3_2_PUBLIC_POLISH_STEP7_RC2_EXTERNAL_REVIEW_FIXES.md")
    assert "Golden scenario snapshot" in validation
    assert "healthy_child_20kg" in validation
    assert "not a medical device" in limitations.lower()
    assert "not for clinical use" in limitations.lower()
    assert "DKA oxygen/Fick death spiral" in report


def test_v320_historical_v31_metadata_tests_are_explicitly_skipped_under_v32():
    for path in [
        "tests/test_v540_documentation_coherence.py",
        "tests/test_v550_apache_license_conversion.py",
        "tests/test_v560_zenodo_deposition_preparation.py",
        "tests/test_v570_osf_project_preparation.py",
        "tests/test_v571_paper_deferred_archive_first.py",
        "tests/test_v580_archive_preflight_manifest.py",
        "tests/test_v590_final_release_archive.py",
    ]:
        text = read(path)
        assert "historical v3.1 release metadata contract" in text
        assert "pytestmark = pytest.mark.skip" in text
