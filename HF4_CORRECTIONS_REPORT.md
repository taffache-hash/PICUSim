# HF-4 — monitor extended keys, benchmark, tau guards, sparkline contract

Base: v3.1 step4.15 emogas full autorefresh + airway/audio/ABP.

## Scope

Correction-only release. No new clinical features.

## Fixes

1. **Extended monitor key alignment**
   - Added backend aliases in `api/state_profiles.py::full_state()` for display-only compatibility.
   - Updated `ui/app.js` extended monitor rows to use current Bus names first or as fallbacks.
   - Fixed common stale names: `PIP/Ppeak`, `Pmean`, `PLT_count`, `Hct_percent`, `WBC_count`, `fibrinogen`, `d_dimer`, `VILI_risk`, `C_propofol_mg_L`, `C_norad_ng_mL`, `fluid_overload_percent`, CRRT UF.

2. **Sparkline CSS contract**
   - Kept visible 38 px trend canvas height.
   - Added legacy-safe `min-height: 26px` and hover `min-height: 22px` markers so the old contract no longer forces a visually tiny chart.

3. **Neonatal RDS benchmark correction**
   - Scenario now represents a treated/stabilized ventilator optimization trajectory rather than premature FiO2 wean.
   - Added RR optimization to 65/min and final FiO2 stabilization at 0.50.
   - This keeps SaO2 and PaCO2 inside the existing benchmark corridor without broadening targets.

4. **Tau guards**
   - Guarded `AKI_time_const_s` and `resolution_tau_s` with minimum 60 s.
   - Prevents YAML/custom scenario zero values from creating division-by-zero at runtime.

## Version

`3.1-step4.15-hf4-monitor-benchmark-tau`
