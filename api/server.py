"""PDT v2.0 API server.

Run from repository root:
    uvicorn api.server:app --reload --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from .schemas import LoadSessionRequest, StartRequest, StepRequest, ActionRequest, InstructorNoteRequest, InstructorVisibilityRequest, SaveSessionRequest, LoadSavedSessionRequest, ScenarioDraftRequest, ScenarioValidateRequest, ScenarioSaveRequest, ReproducibilityPackRequest
from .session import SessionManager
from .debrief import emergency_metrics
from .training import emergency_scenarios
from .instructor import instructor_presets, export_instructor_report, report_to_markdown
from .performance import DEFAULT_BEDSIDE_HZ, DEFAULT_WAVEFORM_HZ, MAX_BEDSIDE_HZ, MAX_WAVEFORM_HZ, clamp_hz, payload_summary
from .session_io import build_session_bundle, bundle_to_markdown, save_bundle_files, read_bundle_from_path, validate_bundle
from .scenario_authoring import list_templates, build_scenario_draft, validate_payload, save_authored_scenario, list_authored_scenarios
from .reproducibility import build_reproducibility_bundle, save_reproducibility_pack, rows_to_csv, TIMELINE_COLUMNS, ACTION_COLUMNS

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text().strip() if (ROOT / "VERSION").exists() else "unknown"
UI_DIR = ROOT / "ui"

app = FastAPI(
    title="PDT Clinical Training API",
    version=VERSION,
    description="Local API and lightweight web monitor for the Pediatric Critical Care Physiology Simulation Framework. Not for clinical use.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = SessionManager()


if UI_DIR.exists():
    app.mount("/ui", StaticFiles(directory=str(UI_DIR)), name="ui")


@app.get("/", include_in_schema=False)
def web_monitor():
    index = UI_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="UI not installed")
    return FileResponse(index)


@app.get("/monitor", include_in_schema=False)
def web_monitor_alias():
    return web_monitor()


@app.get("/health")
def health():
    return {"status": "ok", "api_version": VERSION, "pdt_version": VERSION, "ui": UI_DIR.exists(), "training_mode": True, "instructor_mode": True, "performance_mode": True, "session_io_mode": True, "scenario_authoring_mode": True}


@app.get("/scenarios")
def scenarios():
    return {"scenarios": manager.list_scenarios()}


@app.get("/sessions")
def sessions():
    return {"sessions": manager.list_sessions()}


@app.get("/authoring/templates")
def authoring_templates():
    return {"templates": list_templates()}


@app.post("/authoring/draft")
def authoring_draft(req: ScenarioDraftRequest):
    try:
        return build_scenario_draft(req)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/authoring/validate")
def authoring_validate(req: ScenarioValidateRequest):
    try:
        return validate_payload(req)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/authoring/save")
def authoring_save(req: ScenarioSaveRequest):
    try:
        return save_authored_scenario(req.yaml_text, filename=req.filename, overwrite=req.overwrite, publish_to_scenarios=req.publish_to_scenarios)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/authoring/created")
def authoring_created():
    return {"scenarios": list_authored_scenarios()}


@app.get("/training/scenarios")
def training_scenarios():
    return {"scenarios": emergency_scenarios()}


@app.get("/instructor/presets")
def instructor_action_presets():
    return {"presets": instructor_presets()}


@app.get("/session/{session_id}/instructor")
def instructor_session_state(session_id: str):
    try:
        sess = manager.get(session_id)
        return {"session_id": session_id, "scenario": sess.scenario_name, "instructor": sess.instructor_state()}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/session/{session_id}/instructor/note")
def instructor_note(session_id: str, req: InstructorNoteRequest):
    try:
        sess = manager.get(session_id)
        return {"session_id": session_id, "note": sess.add_instructor_note(req.text, kind=req.kind, pinned=req.pinned)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/session/{session_id}/instructor/visibility")
def instructor_visibility(session_id: str, req: InstructorVisibilityRequest):
    try:
        sess = manager.get(session_id)
        return {"session_id": session_id, **sess.set_learner_diagnosis_hidden(req.hide_diagnosis)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/session/{session_id}/instructor/report")
def instructor_report(session_id: str, format: str = Query(default="json", pattern="^(json|md)$")):
    try:
        sess = manager.get(session_id)
        debrief_obj = emergency_metrics(sess.compact_history(limit=5000), sess.event_log)
        report = export_instructor_report(sess, debrief=debrief_obj)
        if format == "md":
            return PlainTextResponse(report_to_markdown(report), media_type="text/markdown")
        return {"session_id": session_id, "report": report}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/session/{session_id}/debrief")
def debrief(session_id: str, limit: int = Query(default=5000, ge=1, le=5000)):
    try:
        sess = manager.get(session_id)
        return {
            "session_id": session_id,
            "scenario": sess.scenario_name,
            "time_s": round(sess.time_s, 3),
            "debrief": emergency_metrics(sess.compact_history(limit=limit), sess.event_log),
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/session/load")
def load_session(req: LoadSessionRequest):
    try:
        sess = manager.create(req.scenario, dt=req.dt, snapshot_interval_s=req.snapshot_interval_s, max_history_points=req.max_history_points, history_window_s=req.history_window_s, history_decimation_s=req.history_decimation_s)
        return sess.info(profile="bedside")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/session/{session_id}/start")
def start_session(session_id: str, req: StartRequest = StartRequest()):
    try:
        return manager.get(session_id).start(speed=req.speed)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/session/{session_id}/pause")
def pause_session(session_id: str):
    try:
        return manager.get(session_id).pause()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/session/{session_id}/step")
def step_session(session_id: str, req: StepRequest = StepRequest()):
    try:
        return manager.get(session_id).step(seconds=req.seconds)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/session/{session_id}/state")
def get_state(session_id: str, profile: str = Query(default="bedside", pattern="^(bedside|bedside_fast|waveform|waveform_fast|training|controls|debug|full)$")):
    try:
        sess = manager.get(session_id)
        return sess.info(profile=profile)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/session/{session_id}/action")
def action(session_id: str, req: ActionRequest):
    try:
        sess = manager.get(session_id)
        result = sess.apply(req.action, req.payload)
        return {"result": result, "session": sess.info(profile="bedside")}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/session/{session_id}/history")
def history(session_id: str, limit: int = Query(default=500, ge=1, le=5000), profile: str = Query(default="bedside", pattern="^(bedside|training)$")):
    try:
        sess = manager.get(session_id)
        return {"session_id": session_id, "profile": profile, "history": sess.compact_history(limit=limit, profile=profile)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/session/{session_id}/export")
def export_session(session_id: str, format: str = Query(default="json", pattern="^(json|md)$"), history_limit: int = Query(default=5000, ge=10, le=20000)):
    try:
        sess = manager.get(session_id)
        bundle = build_session_bundle(sess, history_limit=history_limit)
        if format == "md":
            return PlainTextResponse(bundle_to_markdown(bundle), media_type="text/markdown")
        return JSONResponse(bundle)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))




@app.get("/session/{session_id}/reproducibility")
def export_reproducibility(session_id: str, format: str = Query(default="json", pattern="^(json|manifest|timeline_csv|interventions_csv|md)$"), seed: Optional[int] = Query(default=None), history_limit: int = Query(default=20000, ge=10, le=50000)):
    try:
        sess = manager.get(session_id)
        pack = build_reproducibility_bundle(sess, seed=seed, history_limit=history_limit)
        if format == "manifest":
            return JSONResponse(pack["manifest"])
        if format == "timeline_csv":
            return PlainTextResponse(rows_to_csv(pack["timeline_rows"], TIMELINE_COLUMNS), media_type="text/csv")
        if format == "interventions_csv":
            return PlainTextResponse(rows_to_csv(pack["action_rows"], ACTION_COLUMNS), media_type="text/csv")
        if format == "md":
            return PlainTextResponse(pack["structured_report_md"], media_type="text/markdown")
        return JSONResponse(pack)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/session/{session_id}/reproducibility/save")
def save_reproducibility(session_id: str, req: ReproducibilityPackRequest = ReproducibilityPackRequest()):
    try:
        sess = manager.get(session_id)
        saved = save_reproducibility_pack(sess, basename=req.basename, seed=req.seed, history_limit=req.history_limit)
        return {"session_id": session_id, "saved": saved}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/session/{session_id}/save")
def save_session(session_id: str, req: SaveSessionRequest = SaveSessionRequest()):
    try:
        sess = manager.get(session_id)
        bundle = build_session_bundle(sess, history_limit=req.history_limit)
        saved = save_bundle_files(bundle, basename=req.basename)
        return {"session_id": session_id, "saved": saved, "bundle_summary": bundle.get("session", {})}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/session/load_saved")
def load_saved_session(req: LoadSavedSessionRequest):
    try:
        if req.bundle is not None:
            bundle = req.bundle
            validate_bundle(bundle)
        elif req.path:
            bundle = read_bundle_from_path(req.path)
        else:
            raise ValueError("Provide either path or bundle")
        sess = manager.restore_from_bundle(bundle, replay_actions=req.replay_actions, max_replay_seconds=req.max_replay_seconds)
        return sess.info(profile="bedside")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/session/{session_id}/reset")
def reset_session(session_id: str):
    try:
        old = manager.get(session_id)
        scenario_ref = str(old.scenario_path.relative_to(ROOT))
        dt = old.dt
        manager.delete(session_id)
        new_session = manager.create(scenario_ref, dt=dt)
        return new_session.info(profile="bedside")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/session/{session_id}/events")
def events(session_id: str):
    try:
        sess = manager.get(session_id)
        return {"session_id": session_id, "events": list(sess.event_log)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    manager.delete(session_id)
    return {"status": "deleted", "session_id": session_id}




@app.get("/performance/config")
def performance_config():
    return {
        "api_version": VERSION,
        "bedside_default_hz": DEFAULT_BEDSIDE_HZ,
        "waveform_default_hz": DEFAULT_WAVEFORM_HZ,
        "bedside_max_hz": MAX_BEDSIDE_HZ,
        "waveform_max_hz": MAX_WAVEFORM_HZ,
        "profiles": ["bedside_fast", "waveform_fast", "training", "controls", "debug", "full"],
    }


@app.get("/session/{session_id}/performance")
def session_performance(session_id: str):
    try:
        sess = manager.get(session_id)
        return {"session_id": session_id, "performance": sess.performance_info(compact=False)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

@app.websocket("/ws/session/{session_id}/bedside")
async def ws_bedside(websocket: WebSocket, session_id: str, hz: float = DEFAULT_BEDSIDE_HZ):
    await websocket.accept()
    hz = clamp_hz(hz, default=DEFAULT_BEDSIDE_HZ, max_hz=MAX_BEDSIDE_HZ)
    interval = 1.0 / hz
    try:
        sess = manager.get(session_id)
    except KeyError:
        await websocket.send_json({"error": "unknown session"})
        await websocket.close()
        return
    try:
        while True:
            await websocket.send_json(sess.info(profile="bedside_fast"))
            await asyncio.sleep(interval)
    except WebSocketDisconnect:
        return


@app.websocket("/ws/session/{session_id}/waveform")
async def ws_waveform(websocket: WebSocket, session_id: str, hz: float = DEFAULT_WAVEFORM_HZ):
    await websocket.accept()
    hz = clamp_hz(hz, default=DEFAULT_WAVEFORM_HZ, max_hz=MAX_WAVEFORM_HZ)
    interval = 1.0 / hz
    try:
        sess = manager.get(session_id)
    except KeyError:
        await websocket.send_json({"error": "unknown session"})
        await websocket.close()
        return
    try:
        while True:
            await websocket.send_json(sess.info(profile="waveform_fast"))
            await asyncio.sleep(interval)
    except WebSocketDisconnect:
        return
