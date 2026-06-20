"""
Pediatric Digital Twin (PDT) — Core package
"""
from .bus import PhysiologicalBus
from .base_module import BaseModule
from .engine import SimulationEngine
from .scenario import ScenarioLoader

__all__ = ["PhysiologicalBus", "BaseModule", "SimulationEngine", "ScenarioLoader"]

try:
    from .airway_events import AirwayEventLibrary, build_airway_event_perturbations
except Exception:  # optional public-clean import guard
    pass
