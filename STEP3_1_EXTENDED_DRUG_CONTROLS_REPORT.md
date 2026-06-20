# Step 3.1 — Extended drug control surface

Scope: expose drug/intervention controls already present in the Bus and used by scenarios, without changing the mathematical physiology engine.

## Changed

- `api/action_router.py`
  - Added explicit mappings for vasoactive, sedative/analgesic/paralytic, respiratory, steroid/metabolic, renal and antimicrobial controls.
  - Aligned the API router more closely with scenario timeline action names.

- `api/state_profiles.py`
  - Added the same extended control fields to `CONTROL_KEYS`.
  - The `controls` state profile now round-trips the newly exposed controls.

- `ui/app.js`
  - Extended `DRUG_CONTROL_BINDINGS` so backend values can resynchronise all newly exposed inputs.

- `ui/index.html`
  - Expanded the Drugs panel into sections:
    - Vasoactive / cardiac
    - Analgesia / sedation / paralysis
    - Respiratory drugs
    - Endocrine / renal / antimicrobials

- `tests/test_v303_drug_control_surface.py`
  - Added regression coverage for action acceptance, controls profile coverage and UI binding coverage.

## Added action mappings

| Action | Bus key |
|---|---|
| `set_dopamine` | `dopamine_mcg_kg_min` |
| `set_vasopressin` | `vasopressin_mU_kg_min` |
| `set_milrinone` | `milrinone_mcg_kg_min` |
| `set_ketamine` | `ketamine_mg_kg_h` |
| `set_remifentanil` | `remifentanil_mcg_kg_min` |
| `set_dexmedetomidine` | `dexmedetomidine_mcg_kg_h` |
| `set_clonidine` | `clonidine_mcg_kg_h` |
| `set_salbutamol` | `salbutamol_mcg_kg_min` |
| `set_ipratropium` | `ipratropium_mcg_kg_h` |
| `set_magnesium` | `magnesium_mg_kg_h` |
| `set_nebulized_epinephrine` | `nebulized_epinephrine_mcg_kg_min` |
| `set_ino_ppm` | `ino_ppm` |
| `set_hydrocortisone` | `hydrocortisone_mg_kg_h` |
| `set_dexamethasone` | `dexamethasone_mcg_kg_h` |
| `set_insulin` | `insulin_UI_h` |
| `set_furosemide` | `furosemide_mg_kg` |
| `set_furosemide_infusion` | `furosemide_mg_kg_h` |
| `set_vancomycin` | `vancomycin_mg_kg_h` |
| `set_piperacillin` | `piperacillin_mg_kg_h` |

## Not changed in this step

- No cardiovascular model correction.
- No `drug_MAP_mod` correction.
- No arterial waveform correction.
- No PEEP zero correction.
- No dose-response retuning.

This step only makes the control surface complete enough to test whether a drug command is received and echoed back by the backend.
