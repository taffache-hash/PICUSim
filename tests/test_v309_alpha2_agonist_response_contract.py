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


def _run(drug_key: str, dose: float, seconds: float = 1800.0, dt: float = 5.0):
    bus, ph, ps = _init_pair()
    bus.set(drug_key, dose)
    for _ in range(int(seconds // dt)):
        ph.step(bus, dt)
        ps.step(bus, dt)
    return bus


def test_v309_dexmedetomidine_cooperative_sedation_preserves_primary_resp_drive():
    dex = _run("dexmedetomidine_mcg_kg_h", 1.2)

    assert dex.get("C_dexmedetomidine_ng_mL") > 0.20
    assert dex.get("dexmedetomidine_sedation_signal") > 0.15
    assert dex.get("dexmedetomidine_sympatholysis_signal") > 0.03
    assert dex.get("alpha2_sedation_signal") > 0.15
    assert dex.get("sedation_score") > 0.15

    # Step 3.4D contract: alpha-2 agonists are not modelled as primary
    # respiratory-drive depressants like propofol/midazolam/opioids.
    assert dex.get("drug_drive_mod") == 1.0
    assert dex.get("sed_resp_mod") == 1.0
    assert dex.get("alpha2_resp_depression_signal") == 0.0


def test_v309_clonidine_slow_alpha2_sedation_and_withdrawal_signal():
    clo = _run("clonidine_mcg_kg_h", 2.0)

    assert clo.get("C_clonidine_ng_mL") > 0.25
    assert clo.get("clonidine_sedation_signal") > 0.10
    assert clo.get("clonidine_sympatholysis_signal") > 0.03
    assert clo.get("clonidine_withdrawal_mod") > 0.10
    assert clo.get("sedation_score") > 0.10
    assert clo.get("drug_drive_mod") == 1.0
    assert clo.get("sed_resp_mod") == 1.0


def test_v309_alpha2_dose_response_is_monotonic_for_sedation_and_sympatholysis():
    dex_buses = [_run("dexmedetomidine_mcg_kg_h", dose) for dose in [0.0, 0.4, 1.2]]
    dex_sed = [b.get("dexmedetomidine_sedation_signal") for b in dex_buses]
    dex_sym = [b.get("dexmedetomidine_sympatholysis_signal") for b in dex_buses]
    dex_hr = [b.get("sed_HR_mod") for b in dex_buses]

    assert dex_sed[0] < dex_sed[1] < dex_sed[2]
    assert dex_sym[0] < dex_sym[1] < dex_sym[2]
    assert dex_hr[0] > dex_hr[1] > dex_hr[2]

    clo_buses = [_run("clonidine_mcg_kg_h", dose) for dose in [0.0, 0.5, 2.0]]
    clo_sed = [b.get("clonidine_sedation_signal") for b in clo_buses]
    clo_sym = [b.get("clonidine_sympatholysis_signal") for b in clo_buses]
    clo_hr = [b.get("sed_HR_mod") for b in clo_buses]

    assert clo_sed[0] < clo_sed[1] < clo_sed[2]
    assert clo_sym[0] < clo_sym[1] < clo_sym[2]
    assert clo_hr[0] > clo_hr[1] > clo_hr[2]


def test_v309_alpha2_not_double_counted_in_drug_hr_svr_or_drive_paths():
    dex = _run("dexmedetomidine_mcg_kg_h", 1.2)
    clo = _run("clonidine_mcg_kg_h", 2.0)

    # HR/SVR coupling is represented through analgosedation sympatholysis, not
    # an additional duplicate drug_HR_mod/drug_SVR_mod decrement.
    assert dex.get("drug_HR_mod") == 1.0
    assert dex.get("drug_SVR_mod") == 1.0
    assert dex.get("sed_HR_mod") < _run("dexmedetomidine_mcg_kg_h", 0.0).get("sed_HR_mod")

    assert clo.get("drug_HR_mod") == 1.0
    assert clo.get("drug_SVR_mod") == 1.0
    assert clo.get("sed_HR_mod") < _run("clonidine_mcg_kg_h", 0.0).get("sed_HR_mod")


def test_v309_source_contract_alpha2_cooperative_sedation_not_primary_resp_depressant():
    ps_source = (ROOT / "modules" / "analgosedation" / "pain_stress_sedation.py").read_text(encoding="utf-8")
    pk_source = (ROOT / "modules" / "pharmacology" / "pk_pd.py").read_text(encoding="utf-8")

    assert "Step 3.4D" in ps_source
    assert "alpha2_resp_depression = 0.0" in ps_source
    assert "Keep alpha2_sed out of sed_resp_mod" in ps_source
    assert "Step 3.4D keeps alpha-2 agonists out of drug_drive_mod" in pk_source
    assert "duplicate HR suppression" in pk_source
