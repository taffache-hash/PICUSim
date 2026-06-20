"""Acute Event System v0.43.

Reusable named acute events mapped to standard SimulationEngine perturbations.
Definitions live in events/acute_events_v0.43.yaml. The mapping is heuristic
and intended for educational/in-silico stress testing, not clinical prediction.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Iterable, List
import yaml
from .engine import Perturbation
from .bus import PhysiologicalBus

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVENT_SPEC = ROOT / 'events' / 'acute_events_v0.43.yaml'


def load_event_spec(path: str | Path | None = None) -> Dict[str, Any]:
    with open(Path(path) if path else DEFAULT_EVENT_SPEC, 'r') as f:
        return yaml.safe_load(f)


def _clamp(x: float, lo: float, hi: float) -> float:
    return float(max(lo, min(hi, x)))


def _add(bus: PhysiologicalBus, key: str, delta: float, lo=None, hi=None):
    val = float(bus.get(key)) + float(delta)
    if lo is not None or hi is not None:
        val = _clamp(val, -1e12 if lo is None else lo, 1e12 if hi is None else hi)
    bus.set(key, val)


def _mul(bus: PhysiologicalBus, key: str, factor: float, lo=None, hi=None):
    val = float(bus.get(key)) * float(factor)
    if lo is not None or hi is not None:
        val = _clamp(val, -1e12 if lo is None else lo, 1e12 if hi is None else hi)
    bus.set(key, val)


def apply_event_effects(bus: PhysiologicalBus, effects: Dict[str, Any]) -> None:
    """Apply compact event effects from events/acute_events_v0.43.yaml."""
    if 'C_rs_factor' in effects: _mul(bus, 'C_rs', effects['C_rs_factor'], 1, 200)
    if 'R_rs_add' in effects: _add(bus, 'R_rs', effects['R_rs_add'], 1, 140)
    if 'Vt_factor' in effects:
        _mul(bus, 'Vt', effects['Vt_factor'], 2, 1000)
        _mul(bus, 'Vt_set_mL', effects['Vt_factor'], 2, 1000)
    if 'Paw_factor' in effects: _mul(bus, 'Paw', effects['Paw_factor'], 0, 80)
    if 'PEEP_set' in effects: bus.set('PEEP', float(effects['PEEP_set']))
    if 'SaO2_sub' in effects: _add(bus, 'SaO2', -float(effects['SaO2_sub']), 0.30, 1.0)
    if 'PaCO2_add' in effects: _add(bus, 'PaCO2', effects['PaCO2_add'], 10, 150)
    if 'shunt_add' in effects: _add(bus, 'airway_shunt_add', effects['shunt_add'], 0, 0.80)
    if 'bronchospasm_add' in effects: _add(bus, 'bronchospasm_index', effects['bronchospasm_add'], 0, 1)
    if 'auto_PEEP_add' in effects:
        _add(bus, 'auto_PEEP_obstructive', effects['auto_PEEP_add'], 0, 25)
        _add(bus, 'auto_PEEP', effects['auto_PEEP_add'], 0, 25)
        _add(bus, 'air_trapping_index', float(effects['auto_PEEP_add']) / 10.0, 0, 1)
    if 'airway_obstruction_add' in effects: _add(bus, 'airway_obstruction_index', effects['airway_obstruction_add'], 0, 1)
    if 'PVR_factor' in effects: _mul(bus, 'PVR', effects['PVR_factor'], 10, 1000)
    if 'MAP_factor' in effects: _mul(bus, 'MAP', effects['MAP_factor'], 15, 140)
    if 'CO_factor' in effects: _mul(bus, 'CO', effects['CO_factor'], 0.3, 20)
    if 'HR_add' in effects: _add(bus, 'HR', effects['HR_add'], 30, 240)
    if 'CVP_add' in effects: _add(bus, 'CVP', effects['CVP_add'], 0, 35)
    if 'RV_afterload_add' in effects: _add(bus, 'RV_afterload_index', effects['RV_afterload_add'], 0, 1)
    if 'Hb_sub' in effects: _add(bus, 'Hb', -float(effects['Hb_sub']), 2, 25)
    if 'blood_loss_mL' in effects:
        _add(bus, 'fluid_balance', -float(effects['blood_loss_mL']), -5000, 10000)
        _add(bus, 'bleeding_rate_mL_h', float(effects['blood_loss_mL']), 0, 3000)
    if 'hemolysis_add' in effects: _add(bus, 'hemolysis_index', effects['hemolysis_add'], 0, 1)
    if 'bilirubin_indirect_add' in effects: _add(bus, 'bilirubin_indirect_mg_dL', effects['bilirubin_indirect_add'], 0, 30)
    if 'VO2_factor' in effects: _mul(bus, 'VO2', effects['VO2_factor'], 10, 1000)
    if 'lactate_add' in effects: _add(bus, 'lactate', effects['lactate_add'], 0.2, 30)
    if 'T_add' in effects: _add(bus, 'T_core', effects['T_add'], 30, 43.5)
    if 'glucose_set' in effects: bus.set('glucose_mmol_L', float(effects['glucose_set']))
    if 'GIR_set' in effects: bus.set('GIR_mg_kg_min', float(effects['GIR_set']))
    if 'insulin_set' in effects: bus.set('insulin_UI_h', float(effects['insulin_set']))
    if 'K_add' in effects: _add(bus, 'K_mmol_L', effects['K_add'], 1.5, 9)
    if 'seizure_risk_add' in effects: _add(bus, 'seizure_risk_index', effects['seizure_risk_add'], 0, 1)
    if 'GCS_sub' in effects: _add(bus, 'GCS_proxy', -float(effects['GCS_sub']), 3, 15)
    if 'catecholamine_add' in effects: _add(bus, 'catecholamine_tone', effects['catecholamine_add'], 0, 3)
    if 'sedation_add' in effects: _add(bus, 'sedation_score', effects['sedation_add'], 0, 1)
    if 'sed_resp_factor' in effects: _mul(bus, 'sed_resp_mod', effects['sed_resp_factor'], 0.05, 1.5)
    if 'midazolam_set' in effects: bus.set('midazolam_mcg_kg_h', float(effects['midazolam_set']))
    if 'fentanyl_set' in effects: bus.set('fentanyl_mcg_kg_h', float(effects['fentanyl_set']))
    if 'inflammatory_add' in effects:
        _add(bus, 'infection_load', effects['inflammatory_add'], 0, 1)
        _add(bus, 'sepsis_severity_score', effects['inflammatory_add'], 0, 1)
    if 'alarm_flag' in effects: bus.set('alarm_active', bool(effects['alarm_flag']))


def event_to_perturbation(item: Dict[str, Any], spec: Dict[str, Any] | None = None) -> Perturbation:
    spec = spec or load_event_spec()
    name = str(item.get('name') or item.get('event'))
    severity = str(item.get('severity', 'moderate'))
    t_event = float(item.get('t', item.get('time', 0)))
    events = spec.get('events', {})
    if name not in events:
        raise ValueError(f'Unknown acute event: {name}')
    severities = events[name].get('severities', {})
    if severity not in severities:
        raise ValueError(f"Unknown severity '{severity}' for event '{name}'")
    effects = dict(severities[severity])
    label = str(item.get('label', f'acute_event:{name}:{severity}'))
    return Perturbation(t=t_event, callback=lambda bus, eff=effects: apply_event_effects(bus, eff), label=label)


def build_event_perturbations(items: Iterable[Dict[str, Any]], spec_path: str | Path | None = None) -> List[Perturbation]:
    spec = load_event_spec(spec_path)
    return sorted([event_to_perturbation(item, spec) for item in items], key=lambda p: p.t)


class AcuteEventLibrary:
    """Convenience wrapper for discovery/validation and ScenarioLoader use."""
    def __init__(self, spec_path: str | Path | None = None):
        self.spec_path = spec_path
        self.spec = load_event_spec(spec_path)
        self.events = self.spec.get('events', {})

    def names(self) -> List[str]:
        return sorted(self.events.keys())

    def severities(self, name: str) -> List[str]:
        if name not in self.events:
            raise KeyError(f'Unknown acute event: {name}')
        return sorted(self.events[name].get('severities', {}).keys())

    def get(self, name: str, severity: str = 'moderate') -> Dict[str, Any]:
        if name not in self.events:
            raise KeyError(f'Unknown acute event: {name}')
        sev = self.events[name].get('severities', {})
        if severity not in sev:
            raise KeyError(f"Unknown severity '{severity}' for event '{name}'")
        return {
            'name': name,
            'severity': severity,
            'description': self.events[name].get('description', ''),
            'effects': dict(sev[severity]),
        }

    def to_perturbation(self, t: float, name: str, severity: str = 'moderate', label: str | None = None) -> Perturbation:
        item = {'t': t, 'name': name, 'severity': severity}
        if label:
            item['label'] = label
        return event_to_perturbation(item, self.spec)
