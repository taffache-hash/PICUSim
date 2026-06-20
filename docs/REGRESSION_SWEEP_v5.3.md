# PCCSim v3.1 - Step 5.3 release candidate regression sweep

Status: completed - targeted sweep passed after CLI portability hotfix.

Date: 2026-06-20

Release candidate under test:

- archive: `pediatric_critical_care_sim_v3.1_step5.2_publication_freeze_rc.zip`
- extracted inspection folder: `_inspect_step5_2_publication_freeze_rc`
- manifest release: `v3.1-step5.2-release-candidate`
- manifest status: `release_candidate_freeze`
- package `VERSION` observed during sweep: `3.1-step4.50-full-prevalidation-audit`

Environment:

- OS: Windows 11
- Python: 3.14.5
- Python executable: `C:\Users\taffa\AppData\Local\Python\pythoncore-3.14-64\python.exe`
- pytest availability: not installed in this Python environment
- Node: bundled runtime used for JS syntax check

## Executive summary

The first regression sweep is broadly positive. Core API/UI contracts, RCP/arrhythmia scenarios, advanced Step 4.39-4.51 engines, and the Step 5.0A-5.1D validation pack all passed under a manual contract runner.

One reproducibility/portability issue was found: `test_public_smoke.py::test_healthy_child_smoke` fails on the default Windows cp1252 console because `run_simulation.py` prints Unicode symbols such as `✓`. The same simulation command passes when `PYTHONIOENCODING=utf-8` is set, so this is classified as a Windows CLI encoding portability issue rather than a physiological/model failure.

## Results

| Suite | Result |
| --- | ---: |
| Initial public/API/UI/RC smoke subset | 11 passed, 0 failed after hotfix |
| Step 5 validation pack 5.0A-5.1D | 19 passed, 0 failed |
| Advanced engines 4.39-4.51 | 35 passed, 0 failed |
| UI/API/RCP/arrhythmia regression | 61 passed, 0 failed |
| JS syntax check `ui/app.js` | passed |

Total executed contract checks in this sweep: 126.

Passed after hotfix: 126.

Failed after hotfix: 0.

## Fixed failure detail

### Public smoke CLI encoding failure

Test:

- `tests/test_public_smoke.py::test_healthy_child_smoke`

Original observed failure:

- `UnicodeEncodeError: 'charmap' codec can't encode character '\u2713'`
- trigger: `core/engine.py` prints `✓` during module initialization
- environment: default Windows console encoding cp1252

Recheck:

- The same `run_simulation.py` command passed when executed with `PYTHONIOENCODING=utf-8`.

Classification:

- portability/reproducibility issue
- not a model physiology failure
- should be fixed or documented before final public release

Fix applied:

- `core/engine.py` module initialization now prints `[ok]` instead of a Unicode checkmark.
- CLI separator lines now use `-` instead of Unicode box drawing.
- `test_public_smoke.py::test_healthy_child_smoke` passes on the default Windows console after the fix.

## Validation pack details

Step 5.0A literature benchmark engine:

- source matrix and summary generation passed
- traceable core benchmark scenario spec passed
- targeted evaluation for healthy child and bronchiolitis passed

Step 5.0B Monte Carlo runner:

- core scenario/bounds spec passed
- short Monte Carlo output generation passed
- flag recording test passed

Step 5.0C plausibility guardrails:

- critical/logical rule spec passed
- impossible-state detection passed
- current Monte Carlo output guardrail check passed

Step 5.0D scenario solvability:

- 8 scenarios audited
- 8 playable
- 8 recoverable
- 8 fail-able
- 8 non-deterministic/playable
- 0 critical findings

Step 5.0E UI human factors audit:

- 23 checks
- 23 pass
- 0 review
- 0 critical
- gate passed

Step 5.1A reproducibility pack:

- JSON pack export passed
- timeline CSV export passed
- intervention CSV export passed
- Markdown export passed
- save endpoint passed

Step 5.1B methods appendix:

- metadata collection passed
- required section rendering passed
- save outputs passed

Step 5.1D sensitivity maps:

- 5 scenarios
- 6 parameters
- 4 outcomes
- 840 map rows
- 120 ranking rows
- status pass

## Advanced engine regression details

The following Step 4.39-4.51 contract groups passed:

- shock engine
- EPALS decision engine
- intubation physiology
- organ perfusion
- advanced vasoactive engine
- scenario engine v2
- scenario timing and trigger
- failure-to-rescue clock
- recovery engine
- full prevalidation audit contracts
- monitor layout compression

Result: 35 passed, 0 failed.

## UI/API/RCP regression details

The following contract groups passed:

- live controls
- bidirectional backend control sync
- extended drug controls
- pending/confirmed UI feedback
- bolus UI
- airway action state
- emogas panel
- airway/audio/ABP fixes
- session button state
- human-pass UI checks
- drug panel navigation
- static/dynamic encoding checks
- cardiac rhythm taxonomy
- RCP panel, CPR, defibrillation, synchronized cardioversion
- RCP drug boluses
- PEA respiratory-arrest scenario
- post-ROSC care
- shockable VF scenario
- unstable VT with pulse scenario
- unstable bradycardia with pulse scenario
- vasoactive infusion pending-feedback hotfix

Result: 61 passed, 0 failed.

## Additional release-coherence findings

These are not test failures, but should be handled in Step 5.4:

1. `VERSION` still reads `3.1-step4.50-full-prevalidation-audit`, while the release manifest declares `v3.1-step5.2-release-candidate`.
2. `README_FIRST_START_HERE.txt` still references an older Step 4.13 build and outdated first-start instructions.
3. `pyproject.toml` still reports `version = "3.0.0a0"`.
4. The manuscript files contain metadata placeholders and version drift that should be reconciled before submission.

## Current recommendation

Step 5.3 targeted regression sweep is green after the ASCII-safe CLI hotfix. Proceed to Step 5.4 documentation/version coherence cleanup. The release manifest must be regenerated during the next rebuild because `core/engine.py`, this report and the regression summary changed after the v5.2 freeze manifest.
