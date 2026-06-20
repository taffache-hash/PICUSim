from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v328_pressure_volume_loop_contract_present():
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    assert "id: 'pressure_volume'" in js
    assert "Pressure-volume loop" in js
    assert "Paw cmH2O" in js
    assert "mode === 'flow_volume' ? s.flow_L_s : s.Paw" in js
    assert "Servono campioni waveform con Vt/flow/Paw" in js
