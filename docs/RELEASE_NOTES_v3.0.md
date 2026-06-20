# Release notes — v3.0-alpha

## Release type

Packaging, documentation and distribution-hardening release.

## Added

- Dockerfile for local containerized deployment.
- docker-compose.yml with persistent output mounts.
- .dockerignore for smaller, cleaner images.
- Docker quickstart documentation.
- Installation guide.
- Distribution checklist.

## Changed

- Version metadata updated to v3.0-alpha.
- README rewritten for public distribution.
- API metadata now reads the package version from the `VERSION` file.
- Console launcher display string now reads the package version from the `VERSION` file.
- License status text updated from legacy v1.0 wording to v3.0-alpha wording.

## Cleaned

- Removed generated `__pycache__` directories.
- Removed pytest cache artifacts.

## Preserved

- Existing v2.7 scenario-authoring assistant.
- Existing local web monitor and instructor/debrief features.
- Historical changelog fragments for traceability.

## Known limitations

- The software remains exploratory alpha software.
- The model is not clinically validated.
- Docker build could not be executed in every restricted environment where Docker Engine is unavailable.
- Historical internal version labels remain in module names, scenario names and legacy documentation where they refer to the feature version that introduced that component.
