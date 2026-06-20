from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v326_capnography_popup_uses_real_etco2_waveform_buffer():
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    assert "id: 'capnogram'" in js
    assert "label: 'Capnografia'" in js
    assert "function capnogramValue" in js
    assert "function drawCapnogram" in js
    assert "EtCO2: Number(st.EtCO2 ?? st.EtCO2_proxy" in js
    assert "Capnogramma accoppiato a EtCO2 reale" in js
