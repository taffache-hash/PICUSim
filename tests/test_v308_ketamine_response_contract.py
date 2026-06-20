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


def test_v308_ketamine_produces_analgesia_and_dissociation_without_primary_resp_depression():
    ket = _run("ketamine_mg_kg_h", 8.0)

    assert ket.get("C_ketamine_mg_L") > 1.0
    assert ket.get("ketamine_analgesia_signal") > 0.45
    assert ket.get("ketamine_dissociation_signal") > 0.15
    assert ket.get("analgesia_score") > 0.45
    assert ket.get("sedation_score") > 0.15
    assert ket.get("pain_score") < 1.30

    # Step 3.4C contract: ketamine is not treated like an opioid/GABA sedative.
    assert ket.get("ketamine_resp_depression_signal") == 0.0
    assert ket.get("drug_drive_mod") == 1.0
    assert ket.get("sed_resp_mod") == 1.0


def test_v308_ketamine_hemodynamic_support_is_monotonic():
    buses = [_run("ketamine_mg_kg_h", dose) for dose in [0.0, 2.0, 8.0]]
    map_mods = [b.get("drug_MAP_mod") for b in buses]
    hr_mods = [b.get("drug_HR_mod") for b in buses]
    sym = [b.get("ketamine_sympathomimetic_signal") for b in buses]

    assert map_mods[0] < map_mods[1] < map_mods[2]
    assert hr_mods[0] < hr_mods[1] < hr_mods[2]
    assert sym[0] < sym[1] < sym[2]
    assert buses[-1].get("drug_MAP_mod") > 1.05
    assert buses[-1].get("drug_HR_mod") > 1.10


def test_v308_ketamine_preserves_drive_compared_with_propofol():
    ket = _run("ketamine_mg_kg_h", 8.0)
    prop = _run("propofol_mg_kg_h", 20.0)

    assert ket.get("sedation_score") > 0.15
    assert prop.get("sedation_score") > ket.get("sedation_score")
    assert ket.get("drug_drive_mod") == 1.0
    assert prop.get("drug_drive_mod") < 0.65
    assert ket.get("drug_MAP_mod") > 1.0
    assert prop.get("drug_MAP_mod") < 1.0


def test_v308_source_contract_ketamine_not_in_resp_depressant_pathway():
    ps_source = (ROOT / "modules" / "analgosedation" / "pain_stress_sedation.py").read_text(encoding="utf-8")
    pk_source = (ROOT / "modules" / "pharmacology" / "pk_pd.py").read_text(encoding="utf-8")

    assert "Step 3.4C" in ps_source
    assert "ketamine_resp_depression = 0.0" in ps_source
    assert "Keep diss_sed out of" in ps_source
    assert "explicitly keeps ketamine out of this pathway" in pk_source
