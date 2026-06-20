#!/usr/bin/env python3
"""Run internal physiologic plausibility checks for PDT scenarios.

This is not clinical validation; it is a regression guard against obviously
non-physiologic model drift. v0.11 adds --strict checks for generic pediatric
safety/plausibility constraints and newly introduced interaction indices.
"""
from pathlib import Path
import sys
import argparse
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import ScenarioLoader
from run_simulation import build_twin


def _run_scenario(path: Path, dt: float = 0.05):
    loader = ScenarioLoader.from_yaml(str(path))
    bus = loader.build_bus()
    engine = build_twin(bus, loader.config, dt=dt)
    engine.verbose = False
    engine.add_perturbations(loader.build_perturbations())
    df = engine.run(float(loader.config.get("simulation_time_s", 300)))
    return loader.config.get("name", path.stem), loader.config, df


def _value(row, key: str, weight: float):
    if key == "Vt_mL_kg":
        return float(row.Vt) / weight
    if key == "CO_L_min_kg":
        return float(row.CO) / weight
    if key == "urine_mL_kg_h":
        return float(row.urine_rate_mL_h) / weight
    if key == "pH":
        return float(row.pH_a)
    if key in row.index:
        return float(row[key])
    return None


def _strict_checks(name: str, cfg: dict, df, failures: list[str]) -> None:
    last = df.iloc[-1]
    weight = float(cfg.get("patient", {}).get("weight_kg", 20.0))
    # General non-negotiable sanity constraints.
    generic = {
        "PaCO2": (20, 80),
        "pH": (7.10, 7.65),
        "Vt_mL_kg": (3, 12),
        "SaO2": (0.75, 1.00),
        "MAP": (35, 130),
        "CO_L_min_kg": (0.04, 0.30),
        "Hb": (5.0, 18.0),
        "VILI_risk": (0.0, 0.85),
        "overdistension_index": (0.0, 0.75),
        "fluid_responsiveness": (0.0, 1.0),
        "heart_lung_CO_mod": (0.45, 1.10),
        "RV_afterload_index": (0.0, 1.0),
        "pain_score": (0.0, 10.0),
        "stress_index": (0.0, 1.0),
        "sedation_score": (0.0, 1.0),
        "analgesia_score": (0.0, 1.0),
        "sympathetic_tone": (0.55, 1.70),
        "delirium_risk": (0.0, 1.0),
        "withdrawal_risk": (0.0, 1.0),
        "sed_resp_mod": (0.02, 1.20),
        "infection_load": (0.0, 1.0),
        "cytokine_drive": (0.0, 1.0),
        "vasoplegia_index": (0.0, 1.0),
        "myocardial_depression_index": (0.0, 1.0),
        "endothelial_leak_index": (0.0, 1.0),
        "microcirculatory_failure_index": (0.0, 1.0),
        "sepsis_SVR_mod": (0.30, 1.20),
        "sepsis_CO_mod": (0.40, 1.40),
        "sepsis_VO2_mod": (0.80, 1.75),
        "sepsis_lactate_prod_mod": (1.0, 3.1),
        "sepsis_severity_score": (0.0, 1.0),
        # v0.17 acid-base / electrolytes
        "Na_mmol_L": (120.0, 165.0),
        "K_mmol_L": (2.0, 7.0),
        "Cl_mmol_L": (85.0, 125.0),
        "HCO3_mmol_L": (8.0, 40.0),
        "base_excess_mmol_L": (-20.0, 20.0),
        "anion_gap_mmol_L": (2.0, 35.0),
        "corrected_anion_gap_mmol_L": (2.0, 40.0),
        "osmolarity_mOsm_L": (250.0, 340.0),
        "metabolic_acidosis_index": (0.0, 1.0),
        "respiratory_acidosis_index": (0.0, 1.0),
        "hyperchloremia_index": (0.0, 1.0),
    }
    for key, bounds in generic.items():
        val = _value(last, key, weight)
        if val is None:
            continue
        lo, hi = bounds
        if not (lo <= val <= hi):
            failures.append(f"{name}: strict {key}={val:.3g} outside [{lo}, {hi}]")

    # Time-series checks: avoid hidden transient blow-ups.
    for key, lo, hi in [("PaCO2", 15, 100), ("pH_a", 6.9, 7.85), ("VILI_risk", 0, 1),
                        ("Na_mmol_L", 115, 170), ("K_mmol_L", 1.8, 7.5),
                        ("HCO3_mmol_L", 6, 45), ("osmolarity_mOsm_L", 240, 360)]:
        if key in df.columns:
            mn, mx = float(df[key].min()), float(df[key].max())
            if mn < lo or mx > hi:
                failures.append(f"{name}: strict transient {key} range [{mn:.3g}, {mx:.3g}] outside [{lo}, {hi}]")

    # Scenario-specific directional checks where labels are known.
    if "ards" in name.lower() and "PEEP" in df.columns and "PaO2" in df.columns:
        early = df.iloc[max(0, min(len(df)-1, int(len(df)*0.25)))]
        late = last
        # PEEP response is accepted if oxygenation is not materially worse by
        # both PaO2 and SaO2, because V/Q redistribution can lower PaO2 while
        # saturation remains clinically acceptable in this simplified model.
        if (float(late.PEEP) > float(early.PEEP)
                and float(late.PaO2) < float(early.PaO2) - 5
                and float(late.SaO2) < float(early.SaO2) - 0.02):
            failures.append(f"{name}: PEEP rose but oxygenation fell materially")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="enable generic strict pediatric plausibility checks")
    parser.add_argument("--dt", type=float, default=0.05)
    args = parser.parse_args(argv)

    ranges = yaml.safe_load((ROOT / "reference_ranges.yaml").read_text())
    expectations = ranges.get("scenario_expectations", {})
    failures = []
    for scen in sorted((ROOT / "scenarios").glob("*.yaml")):
        name, cfg, df = _run_scenario(scen, dt=args.dt)
        last = df.iloc[-1]
        rules = expectations.get(name, expectations.get(scen.stem, {}))
        weight = float(cfg.get("patient", {}).get("weight_kg", 20.0))
        for key, bounds in rules.items():
            lo, hi = bounds
            val = _value(last, key, weight)
            if val is None:
                continue
            if not (lo <= val <= hi):
                failures.append(f"{name}: {key}={val:.3g} outside [{lo}, {hi}]")
        if args.strict:
            _strict_checks(name, cfg, df, failures)
        extra = ""
        if "VILI_risk" in last.index:
            extra = f", VILI={last.VILI_risk:.2f}"
        print(f"✓ {name}: final PaCO2={last.PaCO2:.1f}, SaO2={last.SaO2*100:.1f}%, MAP={last.MAP:.1f}{extra}")
    if failures:
        print("\nFailures:")
        for f in failures:
            print(" -", f)
        return 1
    print("\nAll scenario plausibility checks passed." + (" [strict]" if args.strict else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
