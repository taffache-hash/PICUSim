from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_v320_step4_changelog_records_public_package_test_policy():
    changelog = read("CHANGELOG.md")
    assert "v3.2.0 public polish Step 4" in changelog
    assert "repository-only release archive tests" in changelog
    assert "README.md and CITATION.cff were intentionally left unchanged" in changelog
    assert "v3.2.0 public polish Step 5" in changelog
    assert "Updated `README.md`, `CITATION.cff`, `CITATION.bib`, `VERSION`, and `pyproject.toml`" in changelog


def test_v320_public_package_tests_skip_missing_nested_archives():
    v560 = read("tests/test_v560_zenodo_deposition_preparation.py")
    v590 = read("tests/test_v590_final_release_archive.py")
    assert "import pytest" in v560
    assert "pytest.skip" in v560
    assert "intentionally excluded from distributed public source packages" in v560
    assert "import pytest" in v590
    assert "pytest.skip" in v590
    assert "intentionally excluded from distributed public source packages" in v590


def test_v320_legacy_snapshot_tests_allow_panel_gated_refresh():
    v319 = read("tests/test_v319_extended_monitor_v2_snapshot_contract.py")
    v320 = read("tests/test_v320_popup_charts_requested_contract.py")
    assert "full_profile_refresh_is_panel_gated" in v319
    assert "shouldRefreshFullProfilePanels" in v319
    assert "panel-gated full-profile refresh" in v320
    assert "not popup-chart polling" in v320


def test_v320_frozen_manifest_test_allows_public_polish_growth():
    v580 = read("tests/test_v580_archive_preflight_manifest.py")
    assert "frozen preflight snapshot" in v580
    assert "current_module_count >= counts" in v580


def test_v320_generated_outputs_are_optional_in_source_package():
    v500c = read("tests/test_v500c_plausibility_guardrails.py")
    assert "Generated Monte Carlo output artifacts are intentionally excluded" in v500c
    assert "pytest.skip" in v500c
