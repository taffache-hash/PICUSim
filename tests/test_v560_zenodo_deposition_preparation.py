from pathlib import Path
import json
import tomllib
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.1-step5.9-final-public-release-candidate"
ZENODO_VERSION = "3.1-step5.9-final-public-release-candidate"
ARCHIVE = ROOT / "outputs" / "release_archives" / "pediatric_critical_care_sim_v3.1_step5.6_zenodo_candidate.zip"
SHA = ROOT / "outputs" / "release_archives" / "pediatric_critical_care_sim_v3.1_step5.6_zenodo_candidate.zip.sha256"
if (ROOT / "VERSION").read_text(encoding="utf-8").strip().startswith("3.2.0"):
    pytestmark = pytest.mark.skip(reason="historical v3.1 release metadata contract; superseded by v3.2 public-polish metadata tests")



def read_text(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_zenodo_metadata_and_entrypoints_are_present():
    assert read_text("VERSION").strip() == VERSION
    assert "Zenodo" in read_text("README.md")
    assert "docs/ZENODO_DEPOSITION_PLAN_v5.6.md" in read_text("README_FIRST_START_HERE.txt")
    assert "metadata/zenodo_metadata_v5.6.yaml" in read_text("README.md")

    metadata = read_text("metadata/zenodo_metadata_v5.6.yaml")
    assert "upload_type: software" in metadata
    assert 'license: "Apache-2.0"' in metadata
    assert ZENODO_VERSION in metadata
    assert "DOI" in metadata and "pending" in metadata.lower()
    assert "not for clinical use" in metadata.lower()

    zenodo_json = json.loads(read_text(".zenodo.json"))
    assert zenodo_json["upload_type"] == "software"
    assert zenodo_json["license"] == "Apache-2.0"
    assert zenodo_json["version"] == ZENODO_VERSION


def test_package_metadata_tracks_zenodo_ready_candidate():
    pyproject = tomllib.loads(read_text("pyproject.toml"))
    assert pyproject["project"]["version"] == "3.1.0rc12"
    assert pyproject["project"]["license"]["text"] == "Apache-2.0"
    assert "final public release candidate" in pyproject["project"]["description"]

    cff = read_text("CITATION.cff")
    assert VERSION in cff
    assert 'license: "Apache-2.0"' in cff

    bib = read_text("CITATION.bib")
    assert VERSION in bib
    assert "DOI pending deposition" in bib


def test_candidate_archive_and_checksum_exist_and_exclude_caches():
    if not ARCHIVE.exists() or not SHA.exists():
        pytest.skip("Repository-only archive payload is intentionally excluded from distributed public source packages")
    assert ARCHIVE.exists()
    assert SHA.exists()
    checksum_line = SHA.read_text(encoding="utf-8").strip()
    assert checksum_line.endswith("  pediatric_critical_care_sim_v3.1_step5.6_zenodo_candidate.zip")
    assert len(checksum_line.split()[0]) == 64

    with zipfile.ZipFile(ARCHIVE) as zf:
        names = zf.namelist()
    assert "VERSION" in names
    assert "LICENSE" in names
    assert "NOTICE" in names
    assert "metadata/zenodo_metadata_v5.6.yaml" in names
    assert "docs/ZENODO_DEPOSITION_PLAN_v5.6.md" in names
    assert "outputs/regression_sweep_v5.3/regression_summary_v53.json" in names
    assert not any("__pycache__/" in name for name in names)
    assert not any(name.startswith(".git/") for name in names)
    assert not any(name.endswith(".zip") for name in names)
