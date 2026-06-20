# Step 5.1B — Methods appendix generator

Adds an automatic methods-appendix generator for the PDT v3.1 research-alpha simulator.

## Purpose

The generator creates a deterministic Markdown appendix that can be reused for:

- manuscript supplementary methods;
- internal technical review;
- reproducibility handoff;
- transparent disclosure of model assumptions and limitations.

## Outputs

Generated under `outputs/methods_appendix_v5.1B/`:

- `methods_appendix_v51B.md`
- `methods_appendix_metadata_v51B.json`

## Content

The appendix includes:

- intended-use and safety scope;
- active model components;
- major modelling assumptions;
- validation and audit artifacts from 5.0A–5.0E;
- scenario coverage metadata;
- reproducibility controls from 5.1A;
- known limitations;
- traceability file list.

## Safety boundary

The appendix explicitly states that the simulator is educational/research alpha only and that these audits do not constitute clinical validation.
