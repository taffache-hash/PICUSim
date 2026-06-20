from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bus import PhysiologicalBus
from modules.pharmacology.pk_pd import PharmacologyModule
from modules.analgosedation.pain_stress_sedation import PainStressSedationModule
from modules.respiratory.chemoreflex import ChemoreflexModule
from modules.ventilator.ventilator import VentilatorModule


def _init_pk_ps():
    bus = PhysiologicalBus()
    ph = PharmacologyModule({"weight_kg": 20.0, "age_y": 6.0, "age_group": "child"})
    ps = PainStressSedationModule({"weight_kg": 20.0})
    ph.initialize(bus)
    ps.initialize(bus)
    return bus, ph, ps


def _run_rocuronium(dose: float, seconds: float = 600.0, dt: float = 5.0):
    bus, ph, ps = _init_pk_ps()
    bus.set("rocuronium_mg_kg_h", dose)
    for _ in range(int(seconds // dt)):
        ph.step(bus, dt)
        ps.step(bus, dt)
    return bus


def test_v310_rocuronium_produces_monotonic_neuromuscular_blockade_signal():
    buses = [_run_rocuronium(dose) for dose in [0.0, 0.3, 1.2]]
    nmb = [b.get("drug_NMB_frac") for b in buses]

    assert nmb[0] < nmb[1] < nmb[2]
    assert buses[-1].get("C_rocuronium_ng_mL") > 100.0
    assert buses[-1].get("rocuronium_nmb_signal") == buses[-1].get("drug_NMB_frac")
    assert buses[-1].get("spontaneous_effort_available") < 0.25


def test_v310_rocuronium_is_not_sedation_or_resp_sedation_pathway():
    roc = _run_rocuronium(1.2)

    # Paralysis is not analgosedation: no analgesia, no sedative drug signal,
    # no opioid/GABA/alpha-2/ketamine respiratory-depressant pathway.
    assert roc.get("analgesia_score") == 0.0
    assert roc.get("sedation_score") == 0.0
    assert roc.get("sed_resp_mod") == 1.0
    assert roc.get("sedation_non_gaba_resp_signal") == 0.0
    assert roc.get("drug_drive_mod") == 1.0


def test_v310_neuromuscular_blockade_abolishes_pmus_and_spontaneous_rr_in_assisted_mode():
    bus = PhysiologicalBus()
    bus.set("vent_mode", "PSV")
    bus.set("PaCO2", 55.0)
    bus.set("PaO2", 70.0)
    bus.set("RR", 28.0)
    bus.set("drug_NMB_frac", 0.98)
    bus.set("drug_drive_mod", 1.0)
    bus.set("sed_resp_mod", 1.0)

    ch = ChemoreflexModule({"phi": 0.0, "Pmus_baseline": 5.0, "tau_drive_s": 1.0})
    ch.initialize(bus)
    for _ in range(10):
        ch.step(bus, 1.0)

    assert bus.get("Pmus") < 0.35
    assert bus.get("drive_level") < 0.10
    assert bus.get("RR") < 5.0
    assert bus.get("neuromuscular_blockade_active") is True
    assert bus.get("nmb_trigger_block_active") is True


def test_v310_ventilator_blocks_patient_trigger_under_full_nmb():
    vent = VentilatorModule({"mode": "PSV", "trigger_thresh": 2.0})

    assert vent._patient_triggered(Pmus=6.0, NMB_frac=0.0) is True
    assert vent._patient_triggered(Pmus=6.0, NMB_frac=0.95) is False


def test_v310_source_contract_rocuronium_single_path_no_double_counting():
    ps_source = (ROOT / "modules" / "analgosedation" / "pain_stress_sedation.py").read_text(encoding="utf-8")
    ch_source = (ROOT / "modules" / "respiratory" / "chemoreflex.py").read_text(encoding="utf-8")
    pk_source = (ROOT / "modules" / "pharmacology" / "pk_pd.py").read_text(encoding="utf-8")

    assert "rocuronium is neuromuscular blockade, not respiratory" in ps_source
    assert "neuromuscular blockade is not sedation" in ps_source
    assert "drug_NMB_frac is the single" in ch_source
    assert "does not improve gas exchange by itself" in pk_source
