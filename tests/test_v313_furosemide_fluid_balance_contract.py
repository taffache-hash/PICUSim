from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bus import PhysiologicalBus, BusState
from modules.pharmacology.pk_pd import PharmacologyModule
from modules.renal.aki_crrt import AKICRRTModule
from modules.renal.fluid_balance import FluidBalanceModule


def _base_bus(map_value=65.0, gfr=70.0, aki_stage=0, initial_balance=500.0):
    bus = PhysiologicalBus(
        BusState(
            weight_kg=20.0,
            age_y=6.0,
            MAP=map_value,
            T_core=37.0,
            GFR=gfr,
            GFR_baseline=70.0,
            AKI_stage=aki_stage,
            fluid_balance=initial_balance,
            blood_volume_mL=1600.0,
        )
    )
    bus.update({
        "CVP": 5.0,
        "Hb": 11.0,
        "endothelial_leak_index": 0.0,
        "norad_mcg_kg_min": 0.0,
        "external_fluid_input_mL": 0.0,
        "CRRT_UF_mL_h_effective": 0.0,
        "cumulative_fluid_input_mL": 0.0,
        "cumulative_urine_output_mL": 0.0,
        "cumulative_insensible_loss_mL": 0.0,
        "cumulative_crrt_UF_mL": 0.0,
        "sepsis_GFR_mod": 1.0,
        "endocrine_GFR_mod": 1.0,
        "ADH_water_retention_index": 0.0,
    })
    return bus


def _run_renal_chain(dose_mg_kg=0.0, infusion_mg_kg_h=0.0, map_value=65.0, gfr=70.0, aki_stage=0, seconds=300):
    bus = _base_bus(map_value=map_value, gfr=gfr, aki_stage=aki_stage)
    bus.set("furosemide_mg_kg", dose_mg_kg)
    bus.set("furosemide_mg_kg_h", infusion_mg_kg_h)

    pk = PharmacologyModule({"weight_kg": 20.0, "age_y": 6.0, "age_group": "child"})
    aki = AKICRRTModule({"weight_kg": 20.0})
    fluid = FluidBalanceModule({"weight_kg": 20.0})
    for mod in (pk, aki, fluid):
        mod.initialize(bus)

    for _ in range(seconds):
        pk.step(bus, 1.0)
        aki.step(bus, 1.0)
        fluid.step(bus, 1.0)
    return bus


def test_v313_raw_cumulative_bolus_counter_alone_does_not_drive_diuresis():
    base = _base_bus()
    raw_only = _base_bus()
    raw_only.set("furosemide_mg_kg", 1.0)

    base_fluid = FluidBalanceModule({"weight_kg": 20.0})
    raw_fluid = FluidBalanceModule({"weight_kg": 20.0})
    base_fluid.initialize(base)
    raw_fluid.initialize(raw_only)
    base_fluid.step(base, 1.0)
    raw_fluid.step(raw_only, 1.0)

    assert raw_only.get("furosemide_effective_diuretic_signal") == 0.0
    assert raw_only.get("furosemide_urine_gain") == 1.0
    assert abs(raw_only.get("urine_rate_mL_h") - base.get("urine_rate_mL_h")) < 1e-9


def test_v313_furosemide_pkpd_increases_urine_and_reduces_fluid_balance():
    control = _run_renal_chain(dose_mg_kg=0.0, seconds=300)
    treated = _run_renal_chain(dose_mg_kg=1.0, seconds=300)

    assert treated.get("C_furosemide_mg_L") > 0.1
    assert treated.get("furosemide_diuresis_signal") > 0.0
    assert treated.get("furosemide_effective_diuretic_signal") > 0.0
    assert treated.get("furosemide_urine_gain") > 1.0
    assert treated.get("urine_rate_mL_h") > control.get("urine_rate_mL_h")
    assert treated.get("fluid_balance") < control.get("fluid_balance")


def test_v313_furosemide_response_is_dose_ordered_not_flat():
    low = _run_renal_chain(dose_mg_kg=0.25, seconds=300)
    high = _run_renal_chain(dose_mg_kg=1.0, seconds=300)

    assert high.get("C_furosemide_mg_L") > low.get("C_furosemide_mg_L")
    assert high.get("furosemide_diuresis_signal") >= low.get("furosemide_diuresis_signal")
    assert high.get("furosemide_urine_gain") >= low.get("furosemide_urine_gain")
    assert high.get("urine_rate_mL_h") > low.get("urine_rate_mL_h")


def test_v313_aki_or_severe_hypoperfusion_blunts_furosemide_response():
    normal = _run_renal_chain(dose_mg_kg=1.0, map_value=65.0, gfr=70.0, aki_stage=0, seconds=300)
    shocked_aki = _run_renal_chain(dose_mg_kg=1.0, map_value=38.0, gfr=14.0, aki_stage=2, seconds=300)

    assert shocked_aki.get("furosemide_renal_clearance_factor") < normal.get("furosemide_renal_clearance_factor")
    assert shocked_aki.get("furosemide_effective_diuretic_signal") < normal.get("furosemide_effective_diuretic_signal")
    assert shocked_aki.get("furosemide_urine_gain") < normal.get("furosemide_urine_gain")
    assert shocked_aki.get("urine_rate_mL_h") < normal.get("urine_rate_mL_h")
