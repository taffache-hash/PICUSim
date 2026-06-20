from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bus import PhysiologicalBus
from modules.pharmacology.pk_pd import PharmacologyModule
from modules.nutrition.glucose import GlucoseModule
from modules.acidbase.electrolytes import AcidBaseElectrolyteModule
from modules.endocrine.stress_axis import EndocrineStressAxisModule


def _run_glucose_only(raw_insulin: float, seconds: int = 300) -> PhysiologicalBus:
    bus = PhysiologicalBus()
    bus.set("insulin_UI_h", raw_insulin)
    bus.set("glucose_mmol_L", 12.0)
    bus.set("GIR_mg_kg_min", 4.0)
    gl = GlucoseModule({"weight_kg": 20.0, "glucose_baseline_mmol_L": 12.0, "GIR_mg_kg_min": 4.0})
    gl.initialize(bus)
    for _ in range(seconds):
        gl.step(bus, 1.0)
    return bus


def _run_insulin_chain(raw_insulin: float, glucose: float = 12.0, potassium: float = 5.4, seconds: int = 900) -> PhysiologicalBus:
    bus = PhysiologicalBus()
    bus.set("insulin_UI_h", raw_insulin)
    bus.set("glucose_mmol_L", glucose)
    bus.set("GIR_mg_kg_min", 4.0)
    bus.set("K_mmol_L", potassium)

    ph = PharmacologyModule({"weight_kg": 20.0, "age_y": 6.0, "age_group": "child"})
    gl = GlucoseModule({"weight_kg": 20.0, "glucose_baseline_mmol_L": glucose, "GIR_mg_kg_min": 4.0})
    ab = AcidBaseElectrolyteModule({})
    for mod in (ph, gl, ab):
        mod.initialize(bus)

    for _ in range(seconds):
        ph.step(bus, 1.0)
        gl.step(bus, 1.0)
        ab.step(bus, 1.0)
    return bus


def test_v314_raw_insulin_command_alone_does_not_bypass_pkpd_glucose_owner():
    off = _run_glucose_only(0.0)
    raw_only = _run_glucose_only(10.0)

    # Step 3.9 contract: the pump command is not allowed to directly lower
    # glucose.  PharmacologyModule must first create delayed effect-site signals.
    assert raw_only.get("insulin_effect_revision") >= 319
    assert raw_only.get("insulin_effective_clearance_mmol_L_h") == 0.0
    assert abs(raw_only.get("glucose_mmol_L") - off.get("glucose_mmol_L")) < 1e-9


def test_v314_insulin_pkpd_lowers_glucose_and_k_in_dose_ordered_way():
    off = _run_insulin_chain(0.0)
    low = _run_insulin_chain(0.5)
    high = _run_insulin_chain(2.0)

    assert off.get("C_insulin_mU_L") == 0.0
    assert low.get("C_insulin_mU_L") > 0.0
    assert high.get("C_insulin_mU_L") > low.get("C_insulin_mU_L")

    assert high.get("insulin_action_signal") >= low.get("insulin_action_signal") > 0.0
    assert high.get("insulin_effective_clearance_mmol_L_h") >= low.get("insulin_effective_clearance_mmol_L_h") > 0.0
    assert high.get("insulin_effective_potassium_shift_mmol_L_h") >= low.get("insulin_effective_potassium_shift_mmol_L_h") > 0.0

    assert high.get("glucose_mmol_L") < low.get("glucose_mmol_L") < off.get("glucose_mmol_L")
    assert high.get("K_mmol_L") < low.get("K_mmol_L") < off.get("K_mmol_L")


def test_v314_hypoglycemia_safety_tapers_clearance_and_raises_risk():
    low_glucose = _run_insulin_chain(2.0, glucose=3.1, potassium=5.4, seconds=300)
    high_glucose = _run_insulin_chain(2.0, glucose=12.0, potassium=5.4, seconds=300)

    assert low_glucose.get("insulin_glucose_safety_factor") < high_glucose.get("insulin_glucose_safety_factor")
    assert low_glucose.get("insulin_effective_clearance_mmol_L_h") < high_glucose.get("insulin_effective_clearance_mmol_L_h")
    assert low_glucose.get("insulin_hypoglycemia_risk") > high_glucose.get("insulin_hypoglycemia_risk")


def test_v314_endocrine_uses_delayed_insulin_action_not_raw_command():
    def run(raw_insulin=0.0, insulin_action=0.0):
        bus = PhysiologicalBus()
        bus.update({
            "MAP": 65.0,
            "T_core": 37.0,
            "lactate": 1.5,
            "glucose_mmol_L": 14.0,
            "pain_score": 0.0,
            "stress_index": 0.1,
            "sedation_score": 0.0,
            "cytokine_drive": 0.2,
            "infection_load": 0.2,
            "sepsis_severity_score": 0.2,
            "microcirculatory_failure_index": 0.1,
            "norad_mcg_kg_min": 0.0,
            "adrenaline_mcg_kg_min": 0.0,
            "vasopressin_mU_kg_min": 0.0,
            "Na_mmol_L": 138.0,
            "fluid_balance": 0.0,
            "GFR": 70.0,
            "insulin_UI_h": raw_insulin,
            "insulin_action_signal": insulin_action,
            "insulin_effect_revision": 319,
        })
        mod = EndocrineStressAxisModule({"hpa_tau_s": 1.0, "catechol_tau_s": 1.0})
        mod.initialize(bus)
        mod.step(bus, 1.0)
        return bus

    base = run(raw_insulin=0.0, insulin_action=0.0)
    raw_only = run(raw_insulin=5.0, insulin_action=0.0)
    delayed = run(raw_insulin=5.0, insulin_action=1.0)

    assert abs(raw_only.get("stress_hyperglycemia_index") - base.get("stress_hyperglycemia_index")) < 1e-9
    assert delayed.get("stress_hyperglycemia_index") < base.get("stress_hyperglycemia_index")
