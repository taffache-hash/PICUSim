"""Minimal optional Streamlit interface for the alpha simulator.

Run from the repository root with:

    streamlit run apps/streamlit_app.py

Streamlit is intentionally optional and is not required for CLI use or tests.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import streamlit as st
except Exception as exc:  # pragma: no cover - only used in optional UI runtime
    raise SystemExit(
        "Streamlit is optional and not installed. Install it with: pip install streamlit"
    ) from exc

from core import ScenarioLoader
from core.scenario_timing import scenario_timing_metadata, make_stable_start_config
from core.failure_to_rescue import failure_to_rescue_metadata, with_failure_to_rescue
from run_simulation import build_twin


DEFAULT_OUTPUTS = [
    "SaO2", "PaO2", "PaCO2", "pH_a", "MAP", "HR", "CO", "Vt", "Paw", "EELV", "recruited_frac", "MP"
]


def available_scenarios() -> list[Path]:
    return sorted((ROOT / "scenarios").glob("*.yaml"))


@st.cache_data(show_spinner=False)
def load_scenario_text(path_str: str) -> str:
    return Path(path_str).read_text(encoding="utf-8")


def run_scenario(path: Path, dt: float, *, stable_start: bool = False, trigger_at_s: float = 60.0, enable_ftr: bool = True):
    loader = ScenarioLoader.from_yaml(path)
    if stable_start and path.name != "healthy_child_20kg.yaml":
        healthy_loader = ScenarioLoader.from_yaml(ROOT / "scenarios" / "healthy_child_20kg.yaml")
        config = make_stable_start_config(loader.config, healthy_loader.config, trigger_at_s=trigger_at_s)
        if enable_ftr:
            config = with_failure_to_rescue(config)
        loader = ScenarioLoader.from_dict(config)
    bus = loader.build_bus()
    engine = build_twin(bus, loader.config, dt=dt)
    engine.add_perturbations(loader.build_perturbations())
    df = engine.run(T=loader.simulation_time)
    return loader, df


def main() -> None:
    st.set_page_config(page_title="PICU physiology sim", layout="wide")
    st.title("Pediatric Critical Care Physiology Simulation Framework")
    st.caption("Educational/research alpha only. Not for clinical use. Not a medical device.")

    scenarios = available_scenarios()
    scenario_names = [p.name for p in scenarios]

    with st.sidebar:
        st.header("Scenario")
        selected = st.selectbox("Choose scenario", scenario_names, index=scenario_names.index("healthy_child_20kg.yaml") if "healthy_child_20kg.yaml" in scenario_names else 0)
        dt = st.slider("dt [s]", min_value=0.2, max_value=5.0, value=1.0, step=0.1)
        stable_start = st.checkbox("Start from stable child", value=True)
        trigger_at_s = st.slider("Critical event trigger [real seconds at 1x]", min_value=0, max_value=300, value=60, step=5)
        enable_ftr = st.checkbox("Show failure-to-rescue clock", value=True)
        run_button = st.button("Run / trigger critical event", type="primary")
        show_yaml = st.checkbox("Show YAML", value=False)

    scenario_path = ROOT / "scenarios" / selected

    preview_loader = ScenarioLoader.from_yaml(scenario_path)
    preview_config = preview_loader.config
    if stable_start and scenario_path.name != "healthy_child_20kg.yaml":
        healthy_preview = ScenarioLoader.from_yaml(ROOT / "scenarios" / "healthy_child_20kg.yaml")
        preview_config = make_stable_start_config(preview_config, healthy_preview.config, trigger_at_s=float(trigger_at_s))
    if enable_ftr:
        preview_config = with_failure_to_rescue(preview_config)
    timing = scenario_timing_metadata(preview_config)
    st.warning(
        f"Nominal scenario duration at 1x real time: {timing['real_duration_mmss']} "
        f"({timing['real_duration_s']:.0f} s). Critical event trigger: "
        f"{timing['critical_event_trigger_mmss']}. Acceleration changes wall-clock runtime, not this clinical timeline."
    )
    if enable_ftr:
        ftr = failure_to_rescue_metadata(preview_config)
        st.error(
            f"Failure-to-rescue clock: phenotype {ftr['phenotype']}; golden window "
            f"{ftr['critical_window_mmss']} after trigger; window closes at "
            f"{ftr['critical_window_end_mmss']}; reversibility threshold "
            f"{ftr['reversibility_threshold_mmss']}; point-of-no-return "
            f"{ftr['point_of_no_return_mmss']}."
        )

    if show_yaml:
        st.code(load_scenario_text(str(scenario_path)), language="yaml")

    if run_button:
        with st.spinner("Running simulation..."):
            loader, df = run_scenario(scenario_path, dt, stable_start=stable_start, trigger_at_s=float(trigger_at_s), enable_ftr=enable_ftr)

        st.subheader(loader.scenario_name)
        st.write(loader.config.get("description", ""))

        cols = [c for c in DEFAULT_OUTPUTS if c in df.columns]
        if cols:
            st.line_chart(df[cols])

        final = df.iloc[-1]
        metric_cols = st.columns(4)
        for i, key in enumerate(["SaO2", "PaCO2", "MAP", "HR"]):
            if key in final.index:
                val = final[key]
                if key == "SaO2":
                    metric_cols[i].metric(key, f"{float(val) * 100:.1f}%")
                else:
                    metric_cols[i].metric(key, f"{float(val):.1f}")

        st.dataframe(df.tail(20), use_container_width=True)
        st.download_button(
            "Download CSV",
            data=df.to_csv().encode("utf-8"),
            file_name=f"{scenario_path.stem}_simulation.csv",
            mime="text/csv",
        )
    else:
        st.info("Select a scenario and run the simulation. Use CLI or notebooks for reproducible validation workflows.")


if __name__ == "__main__":
    main()
