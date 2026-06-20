# Installation guide — v3.0-alpha

## Recommended path

Use Docker unless you need to modify the source code directly.

```bash
docker compose up --build
```

Open `http://localhost:8000/monitor`.

## Developer path

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -m pytest -q tests/test_public_smoke.py
python start_pdt_console.py
```

## Supported Python version

The source package declares Python `>=3.9`. The Docker image uses Python 3.11.

## Expected runtime services

- Web console: `/monitor`
- API docs: `/docs`
- Health check: `/health`

## Distribution warning

A final open-source license has not been selected. Do not redistribute as open source until a license is explicitly added.
