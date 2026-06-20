from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.bus import BusState, PhysiologicalBus
from modules.cardiovascular.circulation import CirculationModule


def _steady_map_for_drug_map_mod(modifier: float) -> float:
    bus = PhysiologicalBus(BusState())
    # Isolated cardiovascular setup: keep CO and non-drug modifiers stable so
    # the only intended MAP difference is drug_MAP_mod.
    bus.update({
        'MAP': 65.0,
        'CVP': 5.0,
        'CO': 3.85,
        'Ppl': -5.0,
        'PaO2': 90.0,
        'PEEP': 5.0,
        'Paw_current': 12.0,
        'auto_PEEP': 0.0,
        'auto_PEEP_obstructive': 0.0,
        'dynamic_hyperinflation': 0.0,
        'overdistension_index': 0.0,
        'fluid_responsiveness': 0.6,
        'fluid_CVP_correction': 0.0,
        'norad_mcg_kg_min': 0.0,
        'adrenaline_mcg_kg_min': 0.0,
        'dopamine_mcg_kg_min': 0.0,
        'vasopressin_mU_kg_min': 0.0,
        'milrinone_mcg_kg_min': 0.0,
        'drug_SVR_mod': 1.0,
        'drug_MAP_mod': modifier,
        'sed_SVR_mod': 1.0,
        'sympathetic_tone': 1.0,
        'sepsis_SVR_mod': 1.0,
        'sepsis_CO_mod': 1.0,
        'endocrine_SVR_mod': 1.0,
        'ino_PVR_mod': 1.0,
    })
    module = CirculationModule()
    module.initialize(bus)
    for _ in range(400):
        module.step(bus, 0.5)
    return float(bus.get('MAP'))


def test_v304_drug_map_mod_changes_map_in_same_direction():
    low = _steady_map_for_drug_map_mod(0.8)
    base = _steady_map_for_drug_map_mod(1.0)
    high = _steady_map_for_drug_map_mod(1.2)
    very_high = _steady_map_for_drug_map_mod(1.5)

    assert low < base < high < very_high
    assert abs((low / base) - 0.8) < 0.05
    assert abs((high / base) - 1.2) < 0.05
    assert abs((very_high / base) - 1.5) < 0.05


def test_v304_circulation_uses_multiplicative_resistance_for_drug_map_mod():
    source = (ROOT / 'modules' / 'cardiovascular' / 'circulation.py').read_text(encoding="utf-8")
    assert 'R_sys_eff = R_sys * MAP_drug_mod' in source
