from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.bus import BusState, PhysiologicalBus
from modules.cardiovascular.circulation import CirculationModule
from modules.cardiovascular.heart import HeartModule


def _bus(**updates):
    bus = PhysiologicalBus(BusState())
    base = {
        "MAP": 65.0,
        "CVP": 5.0,
        "PAWP": 8.0,
        "PAP_mean": 15.0,
        "CO": 3.85,
        "SV": 36.0,
        "HR": 105.0,
        "EDV_lv": 55.0,
        "ESV_lv": 20.0,
        "Ppl": -5.0,
        "PaO2": 90.0,
        "PEEP": 5.0,
        "Paw": 12.0,
        "Paw_current": 12.0,
        "auto_PEEP": 0.0,
        "auto_PEEP_obstructive": 0.0,
        "dynamic_hyperinflation": 0.0,
        "overdistension_index": 0.0,
        "fluid_responsiveness": 0.6,
        "fluid_CVP_correction": 0.0,
        "norad_mcg_kg_min": 0.0,
        "adrenaline_mcg_kg_min": 0.0,
        "dopamine_mcg_kg_min": 0.0,
        "vasopressin_mU_kg_min": 0.0,
        "milrinone_mcg_kg_min": 0.0,
        "drug_SVR_mod": 1.0,
        "drug_MAP_mod": 1.0,
        "drug_HR_mod": 1.0,
        "drug_inotropy_mod": 1.0,
        "sed_SVR_mod": 1.0,
        "sympathetic_tone": 1.0,
        "sepsis_SVR_mod": 1.0,
        "sepsis_CO_mod": 1.0,
        "endocrine_SVR_mod": 1.0,
        "ino_PVR_mod": 1.0,
        "T_core": 37.0,
    }
    base.update(updates)
    bus.update(base)
    return bus


def _steady_circulation(**updates):
    bus = _bus(**updates)
    module = CirculationModule()
    module.initialize(bus)
    for _ in range(240):
        module.step(bus, 0.5)
    return bus


def test_v305_noradrenaline_adrenaline_vasopressin_raise_map_monotonically():
    for key, doses in {
        "norad_mcg_kg_min": [0.0, 0.05, 0.20],
        "adrenaline_mcg_kg_min": [0.0, 0.05, 0.20],
        "vasopressin_mU_kg_min": [0.0, 0.03, 0.10],
    }.items():
        maps = [float(_steady_circulation(**{key: dose}).get("MAP")) for dose in doses]
        assert maps[0] < maps[1] < maps[2], f"{key} MAP not monotonic: {maps}"


def test_v305_dopamine_alpha_tone_is_high_dose_not_low_dose():
    base = _steady_circulation(dopamine_mcg_kg_min=0.0)
    low = _steady_circulation(dopamine_mcg_kg_min=5.0)
    high = _steady_circulation(dopamine_mcg_kg_min=15.0)
    assert abs(float(low.get("MAP")) - float(base.get("MAP"))) < 1.5
    assert float(high.get("MAP")) > float(base.get("MAP")) + 4.0


def test_v305_milrinone_is_inodilator_not_primary_vasopressor():
    base = _steady_circulation(milrinone_mcg_kg_min=0.0)
    milrinone = _steady_circulation(milrinone_mcg_kg_min=0.75)
    assert float(milrinone.get("vasoactive_SVR_mod")) < float(base.get("vasoactive_SVR_mod"))
    assert float(milrinone.get("vasoactive_CO_mod")) > float(base.get("vasoactive_CO_mod"))
    assert float(milrinone.get("MAP")) <= float(base.get("MAP")) + 2.0


def test_v305_drug_inotropy_mod_increases_heart_contractile_output():
    def run(inotropy):
        bus = _bus(drug_inotropy_mod=inotropy, MAP=65.0, HR=105.0)
        heart = HeartModule()
        heart.initialize(bus)
        for _ in range(40):
            heart.step(bus, 0.25)
        return float(bus.get("SV")), float(bus.get("CO")), float(bus.get("EF_lv"))

    sv_base, co_base, ef_base = run(1.0)
    sv_high, co_high, ef_high = run(1.30)
    assert sv_high > sv_base
    assert co_high > co_base
    assert ef_high > ef_base


def test_v305_pkpd_no_longer_adds_catecholamine_map_mod_in_source():
    source = (ROOT / "modules" / "pharmacology" / "pk_pd.py").read_text(encoding="utf-8")
    assert "0.25 * E_adr_MAP" not in source
    assert "0.12 * E_dop_MAP" not in source
    assert "MAP_mod = 1.0 + E_ket_MAP - E_pro_vaso * 0.3 - E_mid_vaso * 0.2" in source
