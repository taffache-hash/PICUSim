# Step 5.0E — UI Human Factors Audit v2

Scope: static human-factors gate for the local training console before deeper validation.

This is **not** formal clinical validation and **not** observed usability testing.

Checks: **23**
Pass checks: **23**
Review findings: **0**
Critical findings: **0**
Gate passed: **True**

## Human-use interpretation

- Numeric vital signs remain the primary monitor surface.
- Waveforms are retained as supportive context and compressed to reduce dominance.
- All core session, monitor, quick-access and apparatus targets are present.
- Control density remains within the predefined pre-validation thresholds.

## Audit table

| Category | Check | Status | Severity | Detail |
|---|---|---|---|---|
| dom | unique ids | PASS | pass | 166 unique id targets |
| layout | class monitor-display-split | PASS | pass | present |
| layout | class side-vitals | PASS | pass | present |
| layout | class compact-waveforms | PASS | pass | present |
| layout | class control-dock | PASS | pass | present |
| layout | class apparatus-overlay | PASS | pass | present |
| layout | numeric column before waveforms | PASS | pass | side vitals precede compressed waveforms in DOM |
| targets | vital numeric ids | PASS | pass | all 8 targets present |
| targets | vital trend ids | PASS | pass | all 6 targets present |
| targets | waveform ids | PASS | pass | all 4 targets present |
| targets | quick monitor buttons | PASS | pass | all 5 targets present |
| targets | session buttons | PASS | pass | all 5 targets present |
| targets | apparatus panels | PASS | pass | all 11 targets present |
| navigation | dock/tab panel targets | PASS | pass | 11 panel targets resolve |
| accessibility | button visible labels | PASS | pass | 76 buttons have visible text |
| click_density | dock cards | PASS | pass | 11/14 |
| click_density | session buttons | PASS | pass | 5/6 |
| click_density | quick airway actions | PASS | pass | 4/5 |
| click_density | monitor header actions | PASS | pass | 5/6 |
| legibility | side vital numeric font | PASS | pass | minimum clamp 32px |
| layout | vitals column width | PASS | pass | minmax(210px, 260px) |
| layout | compact waveform height | PASS | pass | max clamp 106px |
| js_contract | core JS targets | PASS | pass | all core monitor/session JS targets resolve |
