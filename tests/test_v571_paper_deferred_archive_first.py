from pathlib import Path
import json
import tomllib
import pytest

ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.1-step5.9-final-public-release-candidate"
if (ROOT / "VERSION").read_text(encoding="utf-8").strip().startswith("3.2.0"):
    pytestmark = pytest.mark.skip(reason="historical v3.1 release metadata contract; superseded by v3.2 public-polish metadata tests")


def read_text(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")

def test_v571_version_and_entrypoints_record_paper_deferred_policy():
    assert read_text("VERSION").strip() == VERSION
    assert "Paper/manuscript policy" in read_text("README.md")
    assert "not from paper text" in read_text("README.md")
    assert "Paper note:" in read_text("README_FIRST_START_HERE.txt")
    pyproject = tomllib.loads(read_text("pyproject.toml"))
    assert pyproject["project"]["version"] == "3.1.0rc12"
    assert "final public release candidate" in pyproject["project"]["description"]

def test_v571_roadmap_defers_manuscripts_until_after_deposit():
    roadmap = read_text("docs/PUBLICATION_RELEASE_ROADMAP_v5.3_to_v6.0.md")
    assert "Manuscripts/papers are explicitly not a source of truth" in roadmap
    assert "## Step 5.8 - Archive preflight and manifest rebuild" in roadmap
    assert "## Step 6.1 - Manuscript and paper consistency pass" in roadmap
    assert "package-facts JSON" in roadmap
    assert "paper text out of the archive-generation" in roadmap

def test_v571_osf_zenodo_metadata_do_not_treat_papers_as_source_of_truth():
    osf = read_text("docs/OSF_PROJECT_PLAN_v5.7.md")
    zenodo = read_text("docs/ZENODO_DEPOSITION_PLAN_v5.6.md")
    correction = read_text("docs/PAPER_DEFERRED_ARCHIVE_FIRST_v5.7A.md")
    assert "Manuscripts/papers are deliberately out of scope until after deposit" in osf
    assert "paper drafts" in zenodo and "not authoritative" in zenodo
    assert "Deposit first, paper last" in correction
    data = json.loads(read_text("metadata/osf_artifact_index_v5.7.json"))
    assert data["version"] == VERSION
    assert "paper_policy" in data
    assert "not source-of-truth" in data["paper_policy"]
