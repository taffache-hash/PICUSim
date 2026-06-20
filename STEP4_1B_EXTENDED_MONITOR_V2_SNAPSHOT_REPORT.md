# Step 4.1B — Extended monitor v2 snapshot-only

Scope: UI-only. No physiology, Docker, or backend streaming changes.

## Implemented

- Expanded the extended monitor from 5 to 11 blocks.
- Made blocks collapsible using native `<details>` elements.
- Changed the extended monitor to manual snapshot refresh only.
- Removed automatic 2.5 s polling behavior.
- Main bedside WebSocket remains unchanged and lightweight.

## Blocks

1. Hemodynamics / perfusion
2. Respiratory
3. Metabolic / labs
4. Neurology / sedation
5. Renal / fluids
6. Coagulation / hematology
7. Hepatic
8. Infection / sepsis
9. Advanced ventilation
10. Drugs / concentrations
11. Nutrition / catabolism

## Rationale

The user should be able to inspect the full patient state on demand without turning the bedside monitor into a continuous full-Bus dashboard.
