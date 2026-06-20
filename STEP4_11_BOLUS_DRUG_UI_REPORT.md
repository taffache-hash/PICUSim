# Step 4.11 - Bolus Drug UI

Added a dedicated bolus/rescue-dose surface inside the Drugs panel.

Most drugs in the current model are PK infusions, not native bolus events. For those drugs, the UI sends a short equivalent infusion and automatically resets it to zero after the configured duration. Furosemide uses the existing native bolus-equivalent Bus counter.

This is an educational UI affordance, not a clinical dose calculator.
