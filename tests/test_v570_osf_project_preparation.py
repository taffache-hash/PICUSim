from pathlib import Path
import json
import tomllib

ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.1-step5.9-final-public-release-candidate"


def read_text(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_v570_osf_plan_and_metadata_exist_without_upload_claims():
    assert read_text("VERSION").strip() == VERSION
    plan = read_text("docs/OSF_PROJECT_PLAN_v5.7.md")
    assert "Status: completed locally" in plan
    assert "no OSF project was created" in plan
    assert "not for clinical use" in plan.lower()
    assert "Step 5.6A" in plan
    assert "stale" in plan.lower()

    structure = read_text("metadata/osf_project_structure_v5.7.md")
    assert "00_Project_overview_and_safety" in structure
    assert "03_Validation_and_regression_outputs" in structure
    assert "05_Manuscripts_and_figures" in structure
    assert "Zenodo should be the citable" in structure


def test_v570_artifact_index_has_required_components_and_deferred_items():
    data = json.loads(read_text("metadata/osf_artifact_index_v5.7.json"))
    assert data["version"] == VERSION
    assert data["status"] == "prepared_no_upload"
    assert data["scenario_yaml_count"] >= 90
    assert data["test_file_count"] >= 100
    components = {item["component"] for item in data["components"]}
    assert "00_Project_overview_and_safety" in components
    assert "01_Software_release_candidate" in components
    assert "02_Scenario_library" in components
    assert "03_Validation_and_regression_outputs" in components
    assert "05_Manuscripts_and_figures" in components
    assert any("Zenodo DOI" in item for item in data["known_deferred_items"])


def test_v570_entrypoints_reference_osf_preparation():
    readme = read_text("README.md")
    first = read_text("README_FIRST_START_HERE.txt")
    pyproject = tomllib.loads(read_text("pyproject.toml"))
    assert VERSION in readme
    assert "docs/OSF_PROJECT_PLAN_v5.7.md" in readme
    assert "metadata/osf_artifact_index_v5.7.json" in readme
    assert "Paper/manuscript policy" in readme
    assert "docs/OSF_PROJECT_PLAN_v5.7.md" in first
    assert pyproject["project"]["version"] == "3.1.0rc12"
    assert "final public release candidate" in pyproject["project"]["description"]
