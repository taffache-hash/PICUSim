# v2.7-alpha — Scenario authoring assistant

This release adds a lightweight scenario authoring assistant to the local API and web console.

It is designed for educational scenario drafting, not for clinical prediction. The assistant does not infer patient-specific physiology. It creates conservative YAML scenarios from curated templates, validates them with the existing scenario loader, and can save them as loadable training scenarios.

## API endpoints

```text
GET  /authoring/templates
POST /authoring/draft
POST /authoring/validate
POST /authoring/save
GET  /authoring/created
```

## Web console

Open:

```text
http://127.0.0.1:8000/monitor
```

Then use:

```text
Control dock → Author
```

The Author panel includes:

```text
template selection
severity selection
title / diagnosis / age / weight / duration
debrief questions
YAML draft editor
validate
save to scenarios
load saved scenario
```

## Design decision

The authoring assistant is intentionally template-based rather than free-form generative text. This keeps the output inspectable and testable. Users can edit YAML manually before validation and saving.

## Safety boundary

Generated scenarios are educational simulation content only. They are not treatment protocols, not a medical device function, and not validated for patient-specific prediction.
