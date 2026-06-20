from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from api.server import app


def test_v327_flow_volume_loop_contract_and_waveform_fast_payload():
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    assert "id: 'flow_volume'" in js
    assert "Flow-volume loop" in js
    assert "function pushWaveformTrend" in js
    assert "flow_L_s" in js
    assert "volume_mL" in js
    assert "drawRespLoop(ctx, width, height, ratio, msg, def.type)" in js

    client = TestClient(app)
    r = client.post('/session/load', json={'scenario': 'healthy_child_20kg', 'dt': 0.2})
    assert r.status_code == 200, r.text
    sid = r.json()['session_id']
    client.post(f'/session/{sid}/step', json={'seconds': 1.0})
    wf = client.get(f'/session/{sid}/state?profile=waveform_fast').json()['state']
    assert 'Vt' in wf
    assert 'Flow_current_mL_s' in wf
    assert 'flow_L_s' in wf
