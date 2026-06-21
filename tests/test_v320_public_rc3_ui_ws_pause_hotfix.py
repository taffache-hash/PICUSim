from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_rc3_index_branding_and_cache_busting():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    assert "PDT Clinical Training Console" not in html
    assert "<title>PICUSim Clinical Training Console</title>" in html
    assert "<h1>PICUSim Clinical Training Console</h1>" in html
    assert "canvas_waveforms.js?v=3.2.0-public" in html
    assert "app.js?v=3.2.0-public" in html
    assert "3.1-step4" not in html


def test_rc3_bedside_fast_fluid_and_rcp_fields():
    from api.state_profiles import BEDSIDE_FAST_KEYS

    required = {
        "crystalloid_preload_response",
        "crystalloid_MAP_support_mmHg",
        "CPR_quality",
        "rhythm_category",
        "compression_fraction",
        "last_shock_energy_J",
        "last_shock_result",
        "last_rcp_drug",
        "last_rcp_drug_result",
        "post_rosc_acidosis_burden",
        "renal_hypoperfusion_index",
        "reperfusion_injury_risk",
    }
    missing = required.difference(set(BEDSIDE_FAST_KEYS))
    assert not missing


def test_rc3_session_pause_race_guard_present():
    source = (ROOT / "api" / "session.py").read_text(encoding="utf-8")
    assert "self.status == \"paused\" and not self._stop_event.is_set()" in source


def test_rc3_version_metadata_consistent():
    assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == "3.2.0-public"
    assert "3.2.0-public" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert "3.2.0-public" in (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert "v3.2.0 public polish Step 8" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
