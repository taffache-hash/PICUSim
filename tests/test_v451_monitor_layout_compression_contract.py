from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v451_monitor_uses_split_numeric_side_column_layout():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    assert 'class="monitor-display-split"' in html
    assert 'class="vitals clean-vitals side-vitals"' in html
    assert 'class="waveform-grid clean-waveforms compact-waveforms"' in html
    for vital_id in ["vHR", "vSpO2", "vMAP", "vABP", "vPaCO2", "vEtCO2", "vPaw", "vFiO2"]:
        assert f'id="{vital_id}"' in html


def test_v451_waveforms_are_compressed_and_numbers_are_emphasised():
    css = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")
    assert ".monitor-display-split" in css
    assert ".side-vitals.clean-vitals" in css
    assert ".side-vitals .vital strong" in css
    assert "clamp(32px, 3.4vw, 48px)" in css
    assert ".compact-waveforms .wave" in css
    assert "clamp(74px, 9.5vh, 106px)" in css
    assert ".side-vitals .vital-trend" in css
