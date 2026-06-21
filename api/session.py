"""In-memory simulation sessions for PDT v2.0 API."""
from __future__ import annotations

import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from core import ScenarioLoader
from core.quality import check_state, SimulationError
from run_simulation import build_twin

from .action_router import apply_action
from .state_profiles import project_state, bedside_state
from .performance import payload_summary

ROOT = Path(__file__).resolve().parents[1]
SCENARIO_DIR = ROOT / "scenarios"


class SimulationSession:
    def __init__(self, scenario_path: Path, dt: float = 0.2, snapshot_interval_s: float = 1.0,
                 max_history_points: int = 1800, history_window_s: float = 1800.0,
                 history_decimation_s: float = 1.0):
        self.id = str(uuid.uuid4())
        self.scenario_path = Path(scenario_path)
        self.dt = float(dt)
        self.snapshot_interval_s = float(snapshot_interval_s)
        self.max_history_points = max(10, int(max_history_points))
        self.history_window_s = max(60.0, float(history_window_s))
        self.history_decimation_s = max(0.1, float(history_decimation_s))
        self.status = "created"
        self.error: Optional[str] = None
        self.speed = 1.0
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_snapshot_t = -1e9
        self.history: List[Dict[str, Any]] = []
        self.event_log: List[Dict[str, Any]] = []
        self.instructor_notes: List[Dict[str, Any]] = []
        self.learner_diagnosis_hidden: bool = False

        self.loader = ScenarioLoader.from_yaml(str(self.scenario_path))
        self.bus = self.loader.build_bus()
        self.perturbations = self.loader.build_perturbations()
        self.T_sim = float(self.loader.simulation_time)
        self.engine = build_twin(self.bus, self.loader.config, dt=self.dt)
        self.engine.verbose = False
        self.engine.add_perturbations(self.perturbations)
        self.engine._initialize()
        self._record_snapshot(force=True)
        self.status = "paused"

    @property
    def scenario_name(self) -> str:
        return str(self.loader.scenario_name)

    @property
    def time_s(self) -> float:
        return float(getattr(self.bus.state, "t", 0.0))

    def _step_once_unlocked(self) -> None:
        t = self.time_s
        for p in self.engine._perturbations:
            if not p._applied and t >= p.t:
                p.apply(self.bus)
                self.event_log.append({"t": t, "label": p.label or p.key or "perturbation"})
        for m in self.engine._modules:
            m.step(self.bus, self.dt)
            m._step_count += 1
            check_state(self.bus, t=t, module_name=m.name)
        self.bus.set("t", t + self.dt)
        self._record_snapshot()
        if self.time_s >= self.T_sim:
            self.status = "completed"

    def _record_snapshot(self, force: bool = False) -> None:
        t = self.time_s
        interval = max(self.snapshot_interval_s, self.history_decimation_s)
        if force or (t - self._last_snapshot_t >= interval - 1e-9):
            snap = bedside_state(self.bus.state)
            self.history.append(snap)
            self._last_snapshot_t = t
            cutoff = t - self.history_window_s
            if cutoff > 0:
                self.history = [h for h in self.history if float(h.get("time_s", h.get("t", 0.0))) >= cutoff]
            if len(self.history) > self.max_history_points:
                self.history = self.history[-self.max_history_points:]

    def step(self, seconds: float) -> Dict[str, Any]:
        seconds = max(0.0, float(seconds))
        steps = max(1, int(round(seconds / self.dt))) if seconds > 0 else 1
        with self._lock:
            self.status = "stepping"
            try:
                for _ in range(steps):
                    if self.time_s >= self.T_sim:
                        self.status = "completed"
                        break
                    self._step_once_unlocked()
                if self.status != "completed":
                    self.status = "paused"
            except Exception as exc:
                self.status = "error"
                self.error = str(exc)
                raise
            return self.info(profile="bedside")

    def _run_loop(self, wall_tick_s: float = 0.10) -> None:
        while not self._stop_event.is_set():
            with self._lock:
                if self.status != "running":
                    break
            try:
                self.step(max(self.dt, wall_tick_s * self.speed))
                with self._lock:
                    # Fix #4: only reset paused→running if pause() has NOT already
                    # armed the stop_event.  Without this guard, a pause() call that
                    # arrives while step() is executing gets silently overwritten,
                    # leaving status="running" while the thread has already exited.
                    if self.status == "paused" and not self._stop_event.is_set():
                        self.status = "running"
                    if self.status in ("completed", "error"):
                        break
            except Exception as exc:
                with self._lock:
                    self.status = "error"
                    self.error = str(exc)
                break
            time.sleep(wall_tick_s)

    def start(self, speed: float = 1.0) -> Dict[str, Any]:
        with self._lock:
            if self.status == "completed":
                return self.info()
            self.speed = max(0.1, min(float(speed), 100.0))
            self.status = "running"
            self._stop_event.clear()
            if not self._thread or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._run_loop, daemon=True)
                self._thread.start()
            return self.info()

    def pause(self) -> Dict[str, Any]:
        with self._lock:
            if self.status == "running":
                self.status = "paused"
            self._stop_event.set()
            return self.info()

    def apply(self, action: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
        with self._lock:
            result = apply_action(self.bus, action, payload or {})
            self.event_log.append({"t": self.time_s, "label": f"action:{action}", "action": action, "payload": payload or {}, "result": result})
            self._record_snapshot(force=True)
            return result


    def add_instructor_note(self, text: str, kind: str = "note", pinned: bool = False) -> Dict[str, Any]:
        from .instructor import new_note
        with self._lock:
            note = new_note(self.time_s, text=text, kind=kind, pinned=pinned)
            if not note["text"]:
                raise ValueError("Instructor note cannot be empty")
            self.instructor_notes.append(note)
            self.event_log.append({"t": self.time_s, "label": f"instructor:{note['kind']}", "note": note})
            return note

    def set_learner_diagnosis_hidden(self, hidden: bool) -> Dict[str, Any]:
        with self._lock:
            self.learner_diagnosis_hidden = bool(hidden)
            self.event_log.append({"t": self.time_s, "label": "instructor:visibility", "learner_diagnosis_hidden": self.learner_diagnosis_hidden})
            return {"learner_diagnosis_hidden": self.learner_diagnosis_hidden}

    def instructor_state(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "learner_diagnosis_hidden": self.learner_diagnosis_hidden,
                "notes": list(self.instructor_notes),
                "event_log": list(self.event_log),
            }

    def state(self, profile: str = "bedside") -> Dict[str, Any]:
        with self._lock:
            return project_state(self.bus.state, profile=profile)

    def info(self, profile: str = "bedside") -> Dict[str, Any]:
        return {
            "session_id": self.id,
            "scenario": self.scenario_name,
            "scenario_path": str(self.scenario_path.relative_to(ROOT)),
            "status": self.status,
            "error": self.error,
            "time_s": round(self.time_s, 3),
            "duration_s": self.T_sim,
            "dt": self.dt,
            "speed": self.speed,
            "state": self.state(profile=profile),
            "instructor": {"learner_diagnosis_hidden": self.learner_diagnosis_hidden, "note_count": len(self.instructor_notes)},
            "performance": self.performance_info(compact=True),
        }

    def compact_history(self, limit: int = 500, profile: str = "bedside") -> List[Dict[str, Any]]:
        with self._lock:
            rows = self.history[-max(1, int(limit)):]
            if profile == "training":
                keep = {"time_s", "t", "SaO2", "SpO2_percent", "MAP", "PaCO2", "airway_event_type", "airway_rescue_state", "intubation_attempt_count", "failed_intubation_count", "intubation_success_time_s"}
                return [{k: v for k, v in r.items() if k in keep} for r in rows]
            return rows

    def performance_info(self, compact: bool = False) -> Dict[str, Any]:
        with self._lock:
            state_obj = project_state(self.bus.state, profile="bedside_fast")
            wave_obj = project_state(self.bus.state, profile="waveform_fast")
            data = {
                "history_points": len(self.history),
                "max_history_points": self.max_history_points,
                "history_window_s": self.history_window_s,
                "history_decimation_s": self.history_decimation_s,
                "snapshot_interval_s": self.snapshot_interval_s,
                "bedside_fast_bytes": payload_summary("bedside_fast", state_obj)["bytes"],
                "waveform_fast_bytes": payload_summary("waveform_fast", wave_obj)["bytes"],
            }
            if not compact:
                data["event_log_count"] = len(self.event_log)
                data["status"] = self.status
                data["time_s"] = round(self.time_s, 3)
            return data


    def restore_instructor_data(self, instructor: Dict[str, Any] | None = None) -> None:
        """Restore instructor metadata from a saved session bundle."""
        instructor = instructor or {}
        with self._lock:
            self.instructor_notes = list(instructor.get("notes") or [])
            self.learner_diagnosis_hidden = bool(instructor.get("learner_diagnosis_hidden", False))


class SessionManager:
    def __init__(self):
        self._sessions: Dict[str, SimulationSession] = {}
        self._lock = threading.RLock()

    def list_scenarios(self) -> List[Dict[str, Any]]:
        out = []
        for path in sorted(SCENARIO_DIR.glob("*.yaml")):
            try:
                loader = ScenarioLoader.from_yaml(str(path))
                out.append({
                    "id": path.stem,
                    "file": str(path.relative_to(ROOT)),
                    "name": str(loader.scenario_name),
                    "duration_s": float(loader.simulation_time),
                    "description": str(loader.config.get("description", "")).strip(),
                    "patient": loader.config.get("patient", {}),
                })
            except Exception as exc:
                out.append({"id": path.stem, "file": str(path.relative_to(ROOT)), "error": str(exc)})
        return out

    def resolve_scenario(self, scenario: str) -> Path:
        scenario = str(scenario)
        candidate = Path(scenario)
        if candidate.is_absolute() and candidate.exists():
            return candidate
        if candidate.suffix == ".yaml":
            p = ROOT / candidate
            if p.exists():
                return p
            p = SCENARIO_DIR / candidate.name
            if p.exists():
                return p
        p = SCENARIO_DIR / f"{scenario}.yaml"
        if p.exists():
            return p
        raise FileNotFoundError(f"Scenario not found: {scenario}")

    def create(self, scenario: str, dt: float = 0.2, snapshot_interval_s: float = 1.0,
               max_history_points: int = 1800, history_window_s: float = 1800.0,
               history_decimation_s: float = 1.0) -> SimulationSession:
        path = self.resolve_scenario(scenario)
        session = SimulationSession(
            path, dt=dt, snapshot_interval_s=snapshot_interval_s,
            max_history_points=max_history_points,
            history_window_s=history_window_s,
            history_decimation_s=history_decimation_s,
        )
        with self._lock:
            self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> SimulationSession:
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError(f"Unknown session: {session_id}")
            return self._sessions[session_id]

    def delete(self, session_id: str) -> None:
        with self._lock:
            sess = self._sessions.pop(session_id, None)
        if sess:
            sess.pause()


    def restore_from_bundle(self, bundle: Dict[str, Any], *, replay_actions: bool = True, max_replay_seconds: float = 3600.0) -> SimulationSession:
        """Create a new live session from a v2.5 saved-session bundle.

        The replay strategy is deliberately conservative: rebuild from the original
        scenario YAML, replay saved instructor/API actions in chronological order,
        then step to the saved time.  This avoids unsafe Python object pickles and
        keeps saved sessions portable.
        """
        session_meta = bundle.get("session") or {}
        scenario_ref = session_meta.get("scenario_path") or session_meta.get("scenario")
        if not scenario_ref:
            raise ValueError("Saved session bundle is missing scenario_path/scenario")
        dt = float(session_meta.get("dt", 0.2) or 0.2)
        snap = float(session_meta.get("snapshot_interval_s", 1.0) or 1.0)
        max_hist = int(session_meta.get("max_history_points", 1800) or 1800)
        hist_win = float(session_meta.get("history_window_s", 1800.0) or 1800.0)
        hist_dec = float(session_meta.get("history_decimation_s", 1.0) or 1.0)
        target_time = max(0.0, float(session_meta.get("time_s", 0.0) or 0.0))
        if target_time > float(max_replay_seconds):
            raise ValueError(f"Saved session replay target {target_time}s exceeds max_replay_seconds")
        session = self.create(
            str(scenario_ref),
            dt=dt,
            snapshot_interval_s=snap,
            max_history_points=max_hist,
            history_window_s=hist_win,
            history_decimation_s=hist_dec,
        )
        actions = sorted(bundle.get("action_replay_log") or [], key=lambda x: float(x.get("t", 0.0) or 0.0))
        if replay_actions:
            for item in actions:
                at = max(0.0, float(item.get("t", 0.0) or 0.0))
                if at > target_time:
                    continue
                remaining = at - session.time_s
                if remaining > 1e-9:
                    session.step(remaining)
                session.apply(str(item.get("action", "")), item.get("payload") or {})
        if target_time > session.time_s:
            session.step(target_time - session.time_s)
        session.restore_instructor_data(bundle.get("instructor") or {})
        session.status = "paused"
        return session

    def list_sessions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [s.info(profile="bedside") for s in self._sessions.values()]
