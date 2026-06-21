"""v3.2.0 public RC3 manifest and package-facts contracts."""

import json
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.2.0-public"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_v320_public_rc3_version_and_metadata_are_aligned():
    assert read("VERSION").strip() == VERSION
    assert VERSION in read("README.md")
    assert VERSION in read("CITATION.cff")
    assert VERSION in read(".zenodo.json")
    assert VERSION in read("data/release_candidate_manifest_v3.2.0.yaml")
    assert VERSION in read("metadata/package_facts_v3.2.0.json")
    assert "10.5281/zenodo.20777589" in read("README.md")
    assert "isNewVersionOf" in read(".zenodo.json")


def test_v320_public_rc3_package_counts_match_filesystem():
    facts = json.loads(read("metadata/package_facts_v3.2.0.json"))
    counts = facts["package_counts"]
    assert counts["scenario_yaml_count"] == len(list((ROOT / "scenarios").glob("*.yaml")))
    assert counts["test_py_count"] == len(list((ROOT / "tests").glob("test_*.py")))
    assert counts["module_py_non_init_count"] == len([p for p in (ROOT / "modules").rglob("*.py") if p.name != "__init__.py"])
    assert counts["docs_markdown_count"] == len(list((ROOT / "docs").glob("*.md")))


def test_v320_public_rc3_required_entrypoints_exist():
    facts = json.loads(read("metadata/package_facts_v3.2.0.json"))
    for rel in facts["required_public_entrypoints"]:
        assert (ROOT / rel).exists(), rel
    for rel in facts["v3_2_public_polish_artifacts"]:
        assert (ROOT / rel).exists(), rel


def test_v320_public_rc3_does_not_claim_new_v32_doi_yet():
    cff = read("CITATION.cff")
    assert "Add the new v3.2.0 Zenodo version DOI here only after final deposition" in cff
    assert "doi:" not in "\n".join([line for line in cff.splitlines() if not line.strip().startswith("#")])
    zenodo = json.loads(read(".zenodo.json"))
    assert zenodo["version"] == VERSION
    assert all(item["identifier"] != "NEW_DOI_PENDING" for item in zenodo.get("related_identifiers", []))


def test_v320_public_final_pyproject_version():
    project = tomllib.loads(read("pyproject.toml"))["project"]
    assert project["version"] == "3.2.0"
    assert "not for clinical use" in project["description"]
    assert project["license"]["text"] == "Apache-2.0"
