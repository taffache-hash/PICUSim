from pathlib import Path
import json
import tomllib
import pytest

ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.1-step5.9-final-public-release-candidate"
FACTS_VERSION = "3.1-step5.8-archive-preflight-manifest"
if (ROOT / "VERSION").read_text(encoding="utf-8").strip().startswith("3.2.0"):
    pytestmark = pytest.mark.skip(reason="historical v3.1 release metadata contract; superseded by v3.2 public-polish metadata tests")



def read_text(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_v580_entrypoints_and_metadata_track_archive_preflight():
    assert read_text("VERSION").strip() == VERSION
    assert VERSION in read_text("README.md")
    assert "final public release candidate" in read_text("README_FIRST_START_HERE.txt").lower()
    assert "docs/ARCHIVE_PREFLIGHT_v5.8.md" in read_text("README.md")
    assert "metadata/package_facts_v5.8.json" in read_text("README.md")

    pyproject = tomllib.loads(read_text("pyproject.toml"))
    assert pyproject["project"]["version"] == "3.1.0rc12"
    assert "final public release candidate" in pyproject["project"]["description"]

    assert VERSION in read_text("CITATION.cff")
    assert VERSION in read_text("CITATION.bib")


def test_v580_package_facts_are_filesystem_not_paper():
    facts = json.loads(read_text("metadata/package_facts_v5.8.json"))
    counts = facts["package_counts"]

    assert facts["version"] == FACTS_VERSION
    assert facts["source_of_truth"] == "filesystem_and_tests"
    assert facts["manuscripts_are_source_of_truth"] is False
    assert facts["paper_deferred_until_after_deposit"] is True
    assert facts["public_upload_performed"] is False

    assert counts["scenario_yaml_count"] == len(list((ROOT / "scenarios").glob("*.yaml")))
    assert counts["test_py_count"] == 117
    current_module_count = len([p for p in (ROOT / "modules").rglob("*.py") if p.name != "__init__.py"])
    assert counts["module_py_non_init_count"] == 35
    assert current_module_count >= counts["module_py_non_init_count"]
    assert counts["docs_markdown_count"] == 78
    assert len(list((ROOT / "tests").glob("test_*.py"))) >= counts["test_py_count"]
    assert len(list((ROOT / "docs").glob("*.md"))) >= counts["docs_markdown_count"]
    # Step 5.9 and v3.2 public-polish steps add later files; the Step 5.8 facts stay as a frozen preflight snapshot.


def test_v580_manifest_marks_stale_archive_and_exclusions():
    manifest = read_text("data/release_candidate_manifest_v5.8.yaml")
    preflight = read_text("docs/ARCHIVE_PREFLIGHT_v5.8.md")
    facts = json.loads(read_text("metadata/package_facts_v5.8.json"))

    assert "status: \"archive_preflight_no_upload\"" in manifest
    assert "manuscripts_are_source_of_truth: false" in manifest
    assert "superseded_do_not_upload" in manifest
    assert "outputs/release_archives/*.zip" in manifest
    assert "__pycache__/" in manifest
    assert ".pytest_cache/" in manifest

    superseded = facts["superseded_archives"][0]
    assert superseded["status"] == "superseded_do_not_upload"
    assert superseded["sha256"] == "02456548893e05700baa9116f31bc1207adb1d8d54033d35aeae86d3c54a6ece"
    assert "must not be uploaded" in preflight
    assert "No GitHub, Zenodo or OSF upload was performed" in preflight
