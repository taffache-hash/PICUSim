from __future__ import annotations
from pathlib import Path
import yaml

_DATA = Path(__file__).resolve().parents[1] / 'data' / 'pediatric_profiles.yaml'

def load_profiles() -> dict:
    with open(_DATA, 'r') as f:
        return yaml.safe_load(f)['profiles']

def nearest_profile(weight_kg: float) -> str:
    profiles = load_profiles()
    return min(profiles, key=lambda k: abs(float(profiles[k]['weight_kg']) - weight_kg))

def get_profile(name: str | None = None, weight_kg: float | None = None) -> tuple[str, dict]:
    profiles = load_profiles()
    if name and name in profiles:
        return name, dict(profiles[name])
    if weight_kg is not None:
        key = nearest_profile(float(weight_kg))
        return key, dict(profiles[key])
    key = 'child_20kg'
    return key, dict(profiles[key])
