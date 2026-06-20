from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bus import PhysiologicalBus
from modules.pharmacology.steroids import SteroidsModule
from modules.sepsis.advanced_sepsis import AdvancedSepsisModule
from modules.endocrine.stress_axis import EndocrineStressAxisModule
from modules.cardiovascular.circulation import CirculationModule


def _base_bus() -> PhysiologicalBus:
    bus = PhysiologicalBus()
    bus.update({
        "MAP": 55.0,
        "CVP": 5.0,
        "PAWP": 8.0,
        "PAP_mean": 15.0,
        "CO": 3.6,
        "SV": 34.0,
        "HR": 110.0,
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
        "drug_SVR_mod": 1.0,
        "drug_MAP_mod": 1.0,
        "sed_SVR_mod": 1.0,
        "sympathetic_tone": 1.0,
        "sepsis_SVR_mod": 1.0,
        "sepsis_CO_mod": 1.0,
        "endocrine_SVR_mod": 1.0,
        "steroid_SVR_mod": 1.0,
        "ino_PVR_mod": 1.0,
        "norad_mcg_kg_min": 0.0,
        "adrenaline_mcg_kg_min": 0.0,
        "dopamine_mcg_kg_min": 0.0,
        "vasopressin_mU_kg_min": 0.0,
        "milrinone_mcg_kg_min": 0.0,
        "T_core": 37.0,
        "lactate": 3.0,
        "DO2": 450.0,
        "VO2": 160.0,
        "infection_load": 0.65,
        "source_control": 0.0,
        "antibiotic_effect": 0.0,
        "cytokine_drive": 0.45,
        "sepsis_severity_score": 0.55,
        "microcirculatory_failure_index": 0.4,
        "glucose_mmol_L": 7.0,
        "pain_score": 0.0,
        "stress_index": 0.2,
        "sedation_score": 0.0,
        "insulin_UI_h": 0.0,
        "Na_mmol_L": 138.0,
        "fluid_balance": 0.0,
    })
    return bus


def test_v312_hydrocortisone_effect_is_delayed_not_instantaneous():
    bus = _base_bus()
    steroid = SteroidsModule({"weight_kg": 20.0, "tau_PD_hc_s": 5400.0})
    steroid.initialize(bus)
    bus.set("hydrocortisone_mg_kg_h", 2.0)

    steroid.step(bus, 1.0)
    early_signal = bus.get("hydrocortisone_vasopressor_sensitization_signal")
    early_svr = bus.get("steroid_SVR_mod")

    for _ in range(7200):
        steroid.step(bus, 1.0)

    late_signal = bus.get("hydrocortisone_vasopressor_sensitization_signal")
    late_svr = bus.get("steroid_SVR_mod")

    assert early_signal < 0.01
    assert early_svr < 1.005
    assert late_signal > early_signal + 0.20
    assert late_svr > early_svr + 0.05


def test_v312_dexamethasone_antiinflammatory_and_icp_effects_are_delayed():
    bus = _base_bus()
    steroid = SteroidsModule({"weight_kg": 20.0, "tau_PD_dexa_s": 7200.0})
    steroid.initialize(bus)
    bus.set("dexamethasone_mcg_kg_h", 1000.0)

    steroid.step(bus, 1.0)
    early_anti = bus.get("dexamethasone_antiinflammatory_signal")
    early_icp = bus.get("dexamethasone_ICP_edema_signal")
    early_sirs_mod = bus.get("steroid_SIRS_mod")

    for _ in range(10800):
        steroid.step(bus, 1.0)

    assert early_anti < 0.01
    assert early_icp < 0.01
    assert early_sirs_mod > 0.995
    assert bus.get("dexamethasone_antiinflammatory_signal") > early_anti + 0.20
    assert bus.get("dexamethasone_ICP_edema_signal") > early_icp + 0.20
    assert bus.get("steroid_SIRS_mod") < early_sirs_mod - 0.05
    assert bus.get("steroid_ICP_mod") < 1.0


def _run_sepsis_once(raw_hydro=0.0, hydro_signal=0.0, dexa_signal=0.0):
    bus = _base_bus()
    bus.set("hydrocortisone_mg_kg_h", raw_hydro)
    bus.set("hydrocortisone_antiinflammatory_signal", hydro_signal)
    bus.set("hydrocortisone_vasopressor_sensitization_signal", hydro_signal)
    bus.set("dexamethasone_antiinflammatory_signal", dexa_signal)
    mod = AdvancedSepsisModule({"infection_load": 0.65, "baseline_cytokine": 0.45, "cytokine_tau_s": 1.0})
    mod.initialize(bus)
    mod.step(bus, 1.0)
    return bus


def test_v312_sepsis_uses_delayed_steroid_signals_not_raw_dose():
    base = _run_sepsis_once(raw_hydro=0.0)
    raw_only = _run_sepsis_once(raw_hydro=2.0)
    delayed = _run_sepsis_once(raw_hydro=2.0, hydro_signal=1.0, dexa_signal=0.5)

    # Raw hydrocortisone command alone must not instantly suppress cytokines or
    # vasoplegia.  Downstream sepsis effects appear only when SteroidsModule has
    # generated delayed PD signals.
    assert abs(raw_only.get("cytokine_drive") - base.get("cytokine_drive")) < 1e-9
    assert abs(raw_only.get("vasoplegia_index") - base.get("vasoplegia_index")) < 1e-9
    assert delayed.get("cytokine_drive") < base.get("cytokine_drive")
    assert delayed.get("vasoplegia_index") < base.get("vasoplegia_index")


def _run_endocrine_once(raw_hydro=0.0, raw_dexa=0.0, hydro_signal=0.0, dexa_signal=0.0):
    bus = _base_bus()
    bus.set("hydrocortisone_mg_kg_h", raw_hydro)
    bus.set("dexamethasone_mcg_kg_h", raw_dexa)
    bus.set("hydrocortisone_adrenal_support_signal", hydro_signal)
    bus.set("hydrocortisone_antiinflammatory_signal", hydro_signal)
    bus.set("dexamethasone_antiinflammatory_signal", dexa_signal)
    bus.set("dexamethasone_ICP_edema_signal", dexa_signal)
    mod = EndocrineStressAxisModule({"hpa_tau_s": 1.0, "baseline_cortisol_activity": 0.20})
    mod.initialize(bus)
    mod.step(bus, 1.0)
    return bus


def test_v312_endocrine_axis_uses_delayed_steroid_signals_not_raw_dose():
    base = _run_endocrine_once()
    raw_only = _run_endocrine_once(raw_hydro=2.0, raw_dexa=1000.0)
    delayed = _run_endocrine_once(raw_hydro=2.0, raw_dexa=1000.0, hydro_signal=1.0, dexa_signal=1.0)

    assert abs(raw_only.get("cortisol_activity") - base.get("cortisol_activity")) < 1e-9
    assert abs(raw_only.get("adrenal_insufficiency_index") - base.get("adrenal_insufficiency_index")) < 1e-9
    assert delayed.get("cortisol_activity") > base.get("cortisol_activity")
    assert delayed.get("adrenal_insufficiency_index") < base.get("adrenal_insufficiency_index")


def test_v312_steroid_svr_mod_is_consumed_by_circulation_not_left_orphaned():
    def run(steroid_svr_mod):
        bus = _base_bus()
        bus.set("steroid_SVR_mod", steroid_svr_mod)
        circ = CirculationModule()
        circ.initialize(bus)
        for _ in range(180):
            circ.step(bus, 0.5)
        return bus.get("MAP"), bus.get("SVR")

    map_base, svr_base = run(1.0)
    map_high, svr_high = run(1.20)

    assert svr_high > svr_base
    assert map_high > map_base + 3.0
