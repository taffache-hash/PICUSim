from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v333_extended_monitor_keys_have_bus_or_full_state_aliases():
    js = (ROOT / 'ui' / 'app.js').read_text(encoding='utf-8')
    state_profiles = (ROOT / 'api' / 'state_profiles.py').read_text(encoding='utf-8')

    # HF-4: common display rows must not point only to obsolete/missing names.
    for needle in [
        "keys: ['PIP', 'Ppeak']",
        "keys: ['Pmean', 'mean_airway_pressure', 'Paw']",
        "keys: ['platelets_10e9_L', 'PLT', 'PLT_count']",
        "keys: ['fibrinogen_mg_dL', 'fibrinogen']",
        "keys: ['d_dimer_mg_L', 'D_dimer', 'd_dimer']",
        "keys: ['Hct', 'Hct_percent']",
        "keys: ['WBC_10e9_L', 'WBC', 'WBC_count']",
        "keys: ['VILI_risk_index', 'VILI_risk']",
        "keys: ['C_propofol_mcg_mL', 'C_propofol_mg_L']",
        "keys: ['C_noradrenaline_ng_mL', 'C_norad_ng_mL']",
    ]:
        assert needle in js

    # Stable aliases are created server-side for full profile consumers.
    for alias in [
        'out.setdefault("PIP", ppeak)',
        'out.setdefault("Pmean", 0.65 * peep + 0.35 * paw)',
        'out.setdefault("platelets_10e9_L", out["PLT_count"])',
        'out.setdefault("fluid_overload_fraction"',
        'out.setdefault("C_propofol_mcg_mL", out["C_propofol_mg_L"])',
        'out.setdefault("C_noradrenaline_ng_mL", out["C_norad_ng_mL"])',
    ]:
        assert alias in state_profiles


def test_v333_tau_guards_are_explicit_for_yaml_zero_values():
    renal = (ROOT / 'modules' / 'renal' / 'fluid_balance.py').read_text(encoding='utf-8')
    sepsis = (ROOT / 'modules' / 'sepsis' / 'advanced_sepsis.py').read_text(encoding='utf-8')
    assert 'max(float(self.params["AKI_time_const_s"]), 60.0)' in renal
    assert 'max(float(self.params["resolution_tau_s"]), 60.0)' in sepsis


def test_v333_neonatal_rds_benchmark_scenario_is_stabilized_not_weaned():
    text = (ROOT / 'scenarios' / 'neonatal_rds_3kg.yaml').read_text(encoding='utf-8')
    assert 'version: 1.05' in text
    assert 'value: 65' in text
    assert 'Ventilation optimization RR 45->65/min' in text
    assert 'value: 0.50' in text
    assert 'FiO2 stabilization after recruitment response' in text


def test_v333_sparkline_css_keeps_visible_height_and_legacy_contract_markers():
    css = (ROOT / 'ui' / 'styles.css').read_text(encoding='utf-8')
    assert '.vital-trend' in css
    assert 'height: 38px' in css  # visible UI height retained
    assert 'min-height: 26px' in css  # old test/contract marker retained safely
    assert '.vital:hover .vital-trend' in css
    assert 'min-height: 22px' in css
