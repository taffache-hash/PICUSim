# Step 5.6A - Crystalloid infusion controls

Date: 2026-06-20
Status: completed as a roadmap deviation after Zenodo preparation.
Clinical status: not for clinical use.

## Reason for deviation

The release candidate had vasoactive, sedative, respiratory, renal/metabolic and antimicrobial infusion controls, but no bedside fluid infusion control. That left a major resuscitation action missing from both the engine and main UI.

## Added controls

Four crystalloid/fluid options are now exposed as user-controlled infusions in mL/h:

- Soluzione fisiologica 0.9% (`normal_saline`)
- Ringer lattato (`ringer_lactate`)
- Sterofundin (`sterofundin`)
- Glucosata 5% (`dextrose_5`)

The main monitor page now includes a compact `Flebo` panel with fluid type, rate, response marker, MAP support marker, urine rate and fluid balance. The same controls are also present inside the Drugs / infusions apparatus panel under `Fluids / crystalloids`.

## Engine behavior

The crystalloid rate is routed through `FluidBalanceModule` as volume input, not through pharmacokinetic drug concentration logic.

Expected qualitative effects are bounded and conditional:

- cumulative fluid input and cumulative crystalloid input increase according to mL/h and timestep;
- MAP/CO support appears only when fluid responsiveness, preload reserve or hypovolemia signals allow it;
- capillary leak, positive fluid balance and overload reduce response;
- urine output may rise if renal perfusion improves;
- saline exposes a chloride-load audit marker;
- balanced crystalloids expose a balanced-fluid marker;
- glucosata 5% contributes an approximate GIR signal.

## API and UI actions

- `set_crystalloid_type` -> `crystalloid_type`
- `set_crystalloid_rate` -> `crystalloid_rate_mL_h`

The API control state mirrors these fields so pending/confirmed UI feedback can clear correctly.

## Important release note

The Step 5.6 Zenodo candidate archive was created before this deviation. It is now stale and must not be uploaded as the final package unless regenerated after this Step 5.6A change. Final archive/manifest regeneration remains a later release step.

## Test coverage

- `tests/test_v56a_crystalloid_fluids_contract.py`

The contract verifies API round-trip, FluidBalance integration, glucosata-to-GIR mapping, UI exposure on the main page and panel exposure in the infusion surface.
