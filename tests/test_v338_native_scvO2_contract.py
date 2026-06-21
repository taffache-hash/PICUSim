from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_v338_native_scvO2_bus_model_and_profiles_present():
    bus = read("core/bus.py")
    gas = read("modules/respiratory/gas_exchange.py")
    profiles = read("api/state_profiles.py")
    ui = read("ui/app.js")
    version = read("VERSION")

    assert version.strip()
    assert "3.1-step" in version or "3.2" in version

    assert "ScvO2: float" in bus
    assert "ScvO2_source" in bus
    assert "ScvO2_revision" in bus

    assert '"ScvO2"' in gas
    assert "def _central_venous_o2" in gas
    assert "SaO2 - extraction" in gas
    assert "CO * Hb * O2_CAPACITY * 10.0" in gas
    assert '"ScvO2_revision": 420' in gas
    assert '"ScvO2_source": "gas_exchange_SaO2_VO2_CO_Hb_proxy"' in gas

    assert '"ScvO2"' in profiles
    assert '"SvO2"' in profiles
    assert '"VO2"' in profiles

    assert "deriveScvO2" in ui
    assert "['ScvO2', 'SvO2']" in ui