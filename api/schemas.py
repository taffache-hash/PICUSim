"""Pydantic schemas for PDT v2.0 API."""
from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class LoadSessionRequest(BaseModel):
    scenario: str = Field(default="healthy_child_20kg", description="Scenario id or YAML path")
    dt: float = Field(default=0.2, ge=0.02, le=5.0)
    snapshot_interval_s: float = Field(default=1.0, ge=0.1, le=30.0)
    max_history_points: int = Field(default=1800, ge=10, le=20000)
    history_window_s: float = Field(default=1800.0, ge=60.0, le=21600.0)
    history_decimation_s: float = Field(default=1.0, ge=0.1, le=60.0)


class StartRequest(BaseModel):
    speed: float = Field(default=1.0, ge=0.1, le=100.0)


class StepRequest(BaseModel):
    seconds: float = Field(default=1.0, ge=0.0, le=120.0)


class ActionRequest(BaseModel):
    action: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class StateResponse(BaseModel):
    session_id: str
    scenario: str
    status: str
    time_s: float
    duration_s: float
    dt: float
    state: Dict[str, Any]


class InstructorNoteRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    kind: str = Field(default="note")
    pinned: bool = Field(default=False)


class InstructorVisibilityRequest(BaseModel):
    hide_diagnosis: bool = Field(default=True)


class SaveSessionRequest(BaseModel):
    basename: Optional[str] = Field(default=None, max_length=120)
    history_limit: int = Field(default=5000, ge=10, le=20000)


class LoadSavedSessionRequest(BaseModel):
    path: Optional[str] = Field(default=None, description="Relative or absolute path to saved session JSON")
    bundle: Optional[Dict[str, Any]] = Field(default=None, description="Saved session JSON object")
    replay_actions: bool = Field(default=True, description="Rebuild by replaying saved actions up to saved time")
    max_replay_seconds: float = Field(default=3600.0, ge=0.0, le=21600.0)


class ScenarioDraftRequest(BaseModel):
    template_id: str = Field(default="airway_deterioration", max_length=80)
    title: str = Field(default="Authored training scenario", min_length=3, max_length=120)
    description: str = Field(default="Educational authored scenario. Not for clinical use.", max_length=1000)
    category: Optional[str] = Field(default=None, max_length=80)
    focus: Optional[list[str]] = Field(default=None)
    age_y: Optional[float] = Field(default=None, ge=0.0, le=18.0)
    weight_kg: Optional[float] = Field(default=None, ge=1.0, le=120.0)
    sex: Optional[str] = Field(default=None, max_length=12)
    diagnosis: Optional[str] = Field(default=None, max_length=120)
    duration_s: Optional[float] = Field(default=None, ge=60.0, le=7200.0)
    severity: str = Field(default="moderate", pattern="^(mild|moderate|severe)$")
    debrief_questions: Optional[list[str]] = Field(default=None)
    custom_parameters: Dict[str, Any] = Field(default_factory=dict)


class ScenarioValidateRequest(BaseModel):
    yaml_text: Optional[str] = Field(default=None, max_length=100000)
    scenario: Optional[Dict[str, Any]] = Field(default=None)


class ScenarioSaveRequest(BaseModel):
    yaml_text: str = Field(min_length=10, max_length=100000)
    filename: Optional[str] = Field(default=None, max_length=120)
    overwrite: bool = Field(default=False)
    publish_to_scenarios: bool = Field(default=True)


class ReproducibilityPackRequest(BaseModel):
    basename: Optional[str] = None
    seed: Optional[int] = None
    history_limit: int = Field(default=20000, ge=10, le=50000)
