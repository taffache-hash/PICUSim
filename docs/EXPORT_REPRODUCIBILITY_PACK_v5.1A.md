# Step 5.1A — Export & reproducibility pack

Purpose: provide deterministic, portable exports for training replay, audit trails, supplementary methods material, and scenario debugging.

Educational/research alpha only. Not for clinical use. Not a medical device.

## Added exports

- complete session JSON bundle
- physiological timeline CSV
- intervention/action log CSV
- structured Markdown report suitable for PDF conversion outside the app
- manifest JSON with SHA-256 hashes
- optional seed metadata

## API endpoints

- `GET /session/{session_id}/reproducibility?format=json`
- `GET /session/{session_id}/reproducibility?format=manifest`
- `GET /session/{session_id}/reproducibility?format=timeline_csv`
- `GET /session/{session_id}/reproducibility?format=interventions_csv`
- `GET /session/{session_id}/reproducibility?format=md`
- `POST /session/{session_id}/reproducibility/save`

## Design constraints

The pack is deterministic at export level: object hashes use canonical sorted JSON. The pack does not serialize Python objects or unsafe runtime state. Scenario file SHA-256, final-state SHA-256, and session-bundle SHA-256 are stored for traceability.

## Output directory

`outputs/reproducibility_pack_v5.1A/`
