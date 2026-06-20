# v2.6-alpha — Tablet-friendly clean UI and apparatus pop-ups

This release reorganizes the web monitor into a cleaner training-console layout.

## Design intent

Earlier versions placed session controls, emergency training, instructor controls, airway controls, drugs, timeline and debriefing panels on the same screen. That made the interface dense and harder to use during simulation.

v2.6 keeps the bedside monitor as the primary visual surface and moves secondary controls into apparatus pop-ups.

## Main layout changes

- Persistent top bar with connection status and learner/instructor view switch.
- Compact session strip for scenario selection and run controls.
- Large central bedside monitor with vital signs and Canvas waveforms.
- Right-side control dock with high-level apparatus buttons.
- Airway status kept visible without expanding all airway controls.
- Recent event mini-timeline in the dock.

## Apparatus pop-ups

The following control groups are now shown as modal apparatus windows:

- Session / files
- Airway / ventilation
- Drugs / infusions
- Emergency training
- Instructor mode
- Emergency debrief
- Timeline

Only one apparatus panel is visible at a time. Closing the window returns to the clean monitor view.

## Tablet and large-screen behavior

The layout uses responsive breakpoints:

- Desktop: monitor + right control dock.
- Medium screen/tablet: monitor first, dock below with grid buttons.
- Small screen: stacked cards and full-width apparatus windows.

Buttons and form controls are larger than in the previous MVP to improve touch usability.

## Clinical-simulation scope

No physiological model changes were made. This is a UI/UX and layout release only.

The simulator remains an educational research tool, not for clinical use, not a medical device, and not a validated patient-specific digital twin.
