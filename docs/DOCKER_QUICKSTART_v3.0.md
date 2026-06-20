# Docker quickstart — v3.0-alpha

This guide is for users who want to run the Pediatric Critical Care Physiology Simulation Framework without installing Python packages manually.

## Requirements

Install Docker Desktop or Docker Engine with Docker Compose support.

## Start the console

From the project folder:

```bash
docker compose up --build
```

Open:

```text
http://localhost:8000/monitor
```

API documentation:

```text
http://localhost:8000/docs
```

Health check:

```text
http://localhost:8000/health
```

## Stop the console

Press `Ctrl+C` in the terminal, then run:

```bash
docker compose down
```

## Build and run without Compose

```bash
docker build -t pediatric-critical-care-sim:3.0-alpha .
docker run --rm -p 8000:8000 pediatric-critical-care-sim:3.0-alpha
```

## Persistent output folders

The Compose file mounts these local folders into the container:

```text
./outputs              -> /app/outputs
./authored_scenarios   -> /app/authored_scenarios
```

This preserves exported sessions, reports and authored scenarios outside the container.

## Updating after code changes

```bash
docker compose down
docker compose up --build
```

## Common problems

### Port 8000 is already in use

Change the left side of the port mapping in `docker-compose.yml`:

```yaml
ports:
  - "8001:8000"
```

Then open:

```text
http://localhost:8001/monitor
```

### Browser cannot connect

Check that the container is running:

```bash
docker compose ps
```

Check logs:

```bash
docker compose logs -f
```

### Clinical-use warning

This Docker package does not make the software clinically validated. It remains exploratory alpha software, not for clinical use, not a medical device and not a patient-specific digital twin.
