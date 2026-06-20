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


def _run_opioid(drug_key: str, dose: float, seconds: float = 900.0, dt: float = 5.0):
    bus, ph, ps = _init_pair()
    bus.set(drug_key, dose)
    for _ in range(int(seconds // dt)):
        ph.step(bus, dt)
        ps.step(bus, dt)
    return bus


def test_v306_fentanyl_morphine_pkpd_signals_without_double_drive_depression():
    fentanyl = _run_opioid("fentanyl_mcg_kg_h", 20.0, seconds=900.0)
    morphine = _run_opioid("morphine_mcg_kg_h", 200.0, seconds=3600.0)

    assert fentanyl.get("C_fentanyl_ng_mL") > 0.5
    assert fentanyl.get("fentanyl_analgesia_signal") > 0.20
    assert fentanyl.get("fentanyl_resp_depression_signal") > 0.05
    assert fentanyl.get("opioid_resp_depression") > 0.05
    assert fentanyl.get("sed_resp_mod") < 0.98
    assert fentanyl.get("drug_drive_mod") == 1.0

    assert morphine.get("C_morphine_ng_mL") > 20.0
    assert morphine.get("morphine_analgesia_signal") > 0.30
    assert morphine.get("morphine_resp_depression_signal") > 0.10
    assert morphine.get("opioid_resp_depression") > 0.10
    assert morphine.get("sed_resp_mod") < 0.95
    assert morphine.get("drug_drive_mod") == 1.0


def test_v306_remifentanil_has_fast_onset_and_fast_offset():
    bus, ph, ps = _init_pair()
    bus.set("remifentanil_mcg_kg_min", 0.2)
    for _ in range(int(900 // 5)):
        ph.step(bus, 5.0)
        ps.step(bus, 5.0)
    on_conc = bus.get("C_remifentanil_ng_mL")
    on_resp = bus.get("remifentanil_resp_depression_signal")
    on_anal = bus.get("remifentanil_analgesia_signal")
    on_sed_resp = bus.get("sed_resp_mod")

    bus.set("remifentanil_mcg_kg_min", 0.0)
    for _ in range(int(600 // 5)):
        ph.step(bus, 5.0)
        ps.step(bus, 5.0)

    assert on_conc > 1.0
    assert on_anal > 0.30
    assert on_resp > 0.10
    assert on_sed_resp < 0.95
    assert bus.get("C_remifentanil_ng_mL") < on_conc * 0.20
    assert bus.get("remifentanil_resp_depression_signal") < on_resp * 0.25
    assert bus.get("sed_resp_mod") > on_sed_resp


def test_v306_opioid_dose_response_is_monotonic_for_respiration_and_analgesia():
    fentanyl_doses = [0.0, 5.0, 20.0]
    remi_doses = [0.0, 0.05, 0.20]

    fentanyl = [_run_opioid("fentanyl_mcg_kg_h", dose, seconds=900.0) for dose in fentanyl_doses]
    remi = [_run_opioid("remifentanil_mcg_kg_min", dose, seconds=900.0) for dose in remi_doses]

    f_anal = [b.get("fentanyl_analgesia_signal") for b in fentanyl]
    f_resp = [b.get("opioid_resp_depression") for b in fentanyl]
    f_mod = [b.get("sed_resp_mod") for b in fentanyl]
    assert f_anal[0] < f_anal[1] < f_anal[2]
    assert f_resp[0] < f_resp[1] < f_resp[2]
    assert f_mod[0] > f_mod[1] > f_mod[2]

    r_anal = [b.get("remifentanil_analgesia_signal") for b in remi]
    r_resp = [b.get("opioid_resp_depression") for b in remi]
    r_mod = [b.get("sed_resp_mod") for b in remi]
    assert r_anal[0] < r_anal[1] < r_anal[2]
    assert r_resp[0] < r_resp[1] < r_resp[2]
    assert r_mod[0] > r_mod[1] > r_mod[2]


def test_v306_source_contract_opioids_not_applied_twice_to_drive():
    source = (ROOT / "modules" / "pharmacology" / "pk_pd.py").read_text(encoding="utf-8")
    assert "(1.0 - 0.45 * E_fen_resp)" not in source
    assert "(1.0 - 0.35 * E_mor_resp)" not in source
    assert "PainStressSedationModule" in source
