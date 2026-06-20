from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.bus import BusState, PhysiologicalBus
from modules.cardiovascular.circulation import CirculationModule


def _bus(**updates):
    bus = PhysiologicalBus(BusState())
    base = {
        "MAP": 65.0, "CVP": 5.0, "PAWP": 8.0, "PAP_mean": 15.0,
        "CO": 3.85, "SV": 36.0, "HR": 105.0, "Ppl": -5.0,
        "PaO2": 90.0, "PEEP": 5.0, "Paw": 12.0, "Paw_current": 12.0,
        "auto_PEEP": 0.0, "auto_PEEP_obstructive": 0.0,
        "dynamic_hyperinflation": 0.0, "overdistension_index": 0.0,
        "fluid_responsiveness": 0.6, "fluid_CVP_correction": 0.0,
        "drug_SVR_mod": 1.0, "drug_MAP_mod": 1.0, "drug_HR_mod": 1.0,
        "sed_SVR_mod": 1.0, "sympathetic_tone": 1.0,
        "sepsis_SVR_mod": 1.0, "sepsis_CO_mod": 1.0,
        "endocrine_SVR_mod": 1.0, "steroid_SVR_mod": 1.0,
        "shock_SVR_mod": 1.0, "shock_preload_mod": 1.0,
        "shock_sympathetic_tone": 1.0, "shock_vasoplegia_index": 0.0,
        "ino_PVR_mod": 1.0, "T_core": 37.0,
        "norad_mcg_kg_min": 0.0, "adrenaline_mcg_kg_min": 0.0,
        "dopamine_mcg_kg_min": 0.0, "vasopressin_mU_kg_min": 0.0,
        "milrinone_mcg_kg_min": 0.0,
    }
    base.update(updates)
    bus.update(base)
    return bus


def _run(seconds=90.0, **updates):
    bus = _bus(**updates)
    module = CirculationModule()
    module.initialize(bus)
    for _ in range(int(seconds / 0.5)):
        module.step(bus, 0.5)
    return bus


def test_v443_receptor_audit_fields_are_emitted():
    bus = _run(norad_mcg_kg_min=0.20, adrenaline_mcg_kg_min=0.06, vasopressin_mU_kg_min=0.04)
    assert int(bus.get("vasoactive_engine_revision")) == 443
    assert float(bus.get("vasoactive_alpha1_signal")) > 0.0
    assert float(bus.get("vasoactive_beta1_signal")) > 0.0
    assert float(bus.get("vasoactive_v1_signal")) > 0.0
    assert float(bus.get("vasoactive_SVR_mod")) > 1.0


def test_v443_milrinone_is_pde3_inodilator_with_interaction_signal():
    base = _run()
    mil = _run(milrinone_mcg_kg_min=0.75)
    combo = _run(norad_mcg_kg_min=0.20, milrinone_mcg_kg_min=0.75)
    assert float(mil.get("vasoactive_pde3_signal")) > 0.0
    assert float(mil.get("vasoactive_CO_mod")) > float(base.get("vasoactive_CO_mod"))
    assert float(mil.get("vasoactive_SVR_mod")) < float(base.get("vasoactive_SVR_mod"))
    assert float(combo.get("vasoactive_interaction_index")) > float(mil.get("vasoactive_interaction_index"))


def test_v443_hysteresis_effective_dose_lags_commanded_infusion():
    bus = _bus(norad_mcg_kg_min=0.40)
    module = CirculationModule()
    module.initialize(bus)
    module.step(bus, 0.5)
    early = float(bus.get("vasoactive_effective_norad"))
    for _ in range(80):
        module.step(bus, 0.5)
    late = float(bus.get("vasoactive_effective_norad"))
    assert 0.0 < early < 0.40
    assert late > early
    assert late <= 0.401


def test_v443_tachyphylaxis_accumulates_during_sustained_high_pressors():
    short = _run(seconds=30.0, norad_mcg_kg_min=0.8, adrenaline_mcg_kg_min=0.3, vasopressin_mU_kg_min=0.12)
    long = _run(seconds=480.0, norad_mcg_kg_min=0.8, adrenaline_mcg_kg_min=0.3, vasopressin_mU_kg_min=0.12)
    assert float(long.get("vasoactive_tachyphylaxis_index")) > float(short.get("vasoactive_tachyphylaxis_index"))
    assert float(long.get("vasoactive_tachyphylaxis_index")) <= 0.32
