from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bus import PhysiologicalBus
from modules.pharmacology.pk_pd import PharmacologyModule
from modules.analgosedation.pain_stress_sedation import PainStressSedationModule


def _init_pair():
    bus = PhysiologicalBus()
    ph = PharmacologyModule({"weight_kg": 20.0, "age_y": 6.0, "age_group": "child"})
    ps = PainStressSedationModule({"weight_kg": 20.0})
    ph.initialize(bus)
    ps.initialize(bus)
    return bus, ph, ps


def _run_sedative(drug_key: str, dose: float, seconds: float = 1800.0, dt: float = 5.0):
    bus, ph, ps = _init_pair()
    bus.set(drug_key, dose)
    for _ in range(int(seconds // dt)):
        ph.step(bus, dt)
        ps.step(bus, dt)
    return bus


def test_v307_midazolam_propofol_depress_drive_without_double_sed_resp_depression():
    midazolam = _run_sedative("midazolam_mcg_kg_h", 400.0)
    propofol = _run_sedative("propofol_mg_kg_h", 20.0)

    assert midazolam.get("C_midazolam_ng_mL") > 100.0
    assert midazolam.get("midazolam_sedation_signal") > 0.30
    assert midazolam.get("drug_drive_mod") < 0.70
    assert midazolam.get("sed_resp_mod") == 1.0
    assert midazolam.get("sedation_non_gaba_resp_signal") == 0.0

    assert propofol.get("C_propofol_mg_L") > 1.5
    assert propofol.get("propofol_sedation_signal") > 0.40
    assert propofol.get("drug_drive_mod") < 0.65
    assert propofol.get("sed_resp_mod") == 1.0
    assert propofol.get("sedation_non_gaba_resp_signal") == 0.0


def test_v307_gaba_sedative_dose_response_is_monotonic():
    mids = [_run_sedative("midazolam_mcg_kg_h", dose) for dose in [0.0, 100.0, 400.0]]
    pros = [_run_sedative("propofol_mg_kg_h", dose) for dose in [0.0, 6.0, 20.0]]

    mid_sed = [b.get("midazolam_sedation_signal") for b in mids]
    mid_drive = [b.get("drug_drive_mod") for b in mids]
    assert mid_sed[0] < mid_sed[1] < mid_sed[2]
    assert mid_drive[0] > mid_drive[1] > mid_drive[2]

    pro_sed = [b.get("propofol_sedation_signal") for b in pros]
    pro_drive = [b.get("drug_drive_mod") for b in pros]
    assert pro_sed[0] < pro_sed[1] < pro_sed[2]
    assert pro_drive[0] > pro_drive[1] > pro_drive[2]


def test_v307_propofol_has_clearer_hemodynamic_signal_than_midazolam():
    midazolam = _run_sedative("midazolam_mcg_kg_h", 400.0)
    propofol = _run_sedative("propofol_mg_kg_h", 20.0)

    assert propofol.get("propofol_vasodilation_signal") > midazolam.get("midazolam_vasodilation_signal")
    assert propofol.get("drug_MAP_mod") < midazolam.get("drug_MAP_mod")
    assert propofol.get("drug_SVR_mod") < midazolam.get("drug_SVR_mod")
    assert propofol.get("drug_HR_mod") < 1.0
    assert midazolam.get("drug_HR_mod") == 1.0


def test_v307_source_contract_gaba_sedatives_not_applied_twice_to_sed_resp_mod():
    source = (ROOT / "modules" / "analgosedation" / "pain_stress_sedation.py").read_text(encoding="utf-8")
    assert "non_gaba_resp_sedation" in source
    assert "(1.0 - 0.55*sedation)" not in source
    pk_source = (ROOT / "modules" / "pharmacology" / "pk_pd.py").read_text(encoding="utf-8")
    assert "sedative_drive_depression_signal" in pk_source
