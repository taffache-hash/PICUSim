from pathlib import Path
import hashlib
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.1-step5.9-final-public-release-candidate"
ARCHIVE = ROOT / "outputs" / "release_archives" / "pediatric_critical_care_sim_v3.1_step5.9_public_release_candidate.zip"
SHA = ROOT / "outputs" / "release_archives" / "pediatric_critical_care_sim_v3.1_step5.9_public_release_candidate.zip.sha256"
if (ROOT / "VERSION").read_text(encoding="utf-8").strip().startswith("3.2.0"):
    pytestmark = pytest.mark.skip(reason="historical v3.1 release metadata contract; superseded by v3.2 public-polish metadata tests")



def read_text(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_v590_entrypoints_track_final_release_candidate():
    assert read_text("VERSION").strip() == VERSION
    assert VERSION in read_text("README.md")
    assert VERSION in read_text("CITATION.cff")
    assert VERSION in read_text("CITATION.bib")
    assert "data/release_candidate_manifest_v5.9.yaml" in read_text("README.md")
    assert "No GitHub, Zenodo or OSF upload was performed" in read_text("docs/FINAL_RELEASE_NOTES_v5.9.md")


def test_v590_archive_and_checksum_are_valid():
    if not ARCHIVE.exists() or not SHA.exists():
        pytest.skip("Repository-only release archive is intentionally excluded from distributed public source packages")
    assert ARCHIVE.exists()
    assert SHA.exists()
    digest = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    checksum_line = SHA.read_text(encoding="utf-8").strip()
    assert checksum_line == f"{digest}  {ARCHIVE.name}"


def test_v590_archive_contains_required_files_and_excludes_transients():
    if not ARCHIVE.exists():
        pytest.skip("Repository-only release archive is intentionally excluded from distributed public source packages")
    with zipfile.ZipFile(ARCHIVE) as zf:
        names = set(zf.namelist())

    required = {
        "README_FIRST_START_HERE.txt",
        "README.md",
        "VERSION",
        "LICENSE",
        "NOTICE",
        "DISCLAIMER_NOT_FOR_CLINICAL_USE.md",
        "CITATION.cff",
        "CITATION.bib",
        ".zenodo.json",
        "data/release_candidate_manifest_v5.9.yaml",
        "docs/FINAL_RELEASE_NOTES_v5.9.md",
        "metadata/package_facts_v5.8.json",
    }
    assert required.issubset(names)
    assert not any(name.startswith(".git/") for name in names)
    assert not any(name.startswith(".pytest_cache/") for name in names)
    assert not any("__pycache__/" in name for name in names)
    assert not any(name.startswith("outputs/release_archives/") and name.endswith(".zip") for name in names)
    assert not any(name.endswith(".pyc") for name in names)
    assert "server_8765_stdout.log" not in names
    assert "server_8765_stderr.log" not in names