"""Methods appendix generator for PDT v5.1B.

Generates a deterministic, publication-oriented methods appendix from the
repository registry files and currently available validation artifacts. The
output is intentionally conservative: it documents model scope, active modules,
assumptions, validation gates and limitations without claiming clinical
validation.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs" / "methods_appendix_v5.1B"
SCHEMA = "pdt-methods-appendix-v5.1B"

CORE_MODULES = [
    "pediatric profile scaling",
    "respiratory mechanics and gas-exchange surrogate",
    "shock engine",
    "advanced vasoactive engine",
    "intubation physiology",
    "organ perfusion model",
    "failure-to-rescue clock",
    "adaptive deterioration / recovery logic",
    "EPALS-like decision support layer",
    "scenario engine v2",
    "export and reproducibility pack",
]

SAFETY_SCOPE = (
    "Educational and research-alpha simulator only; not a medical device, not a "
    "bedside decision tool and not validated for clinical diagnosis or treatment."
)

VALIDATION_ARTIFACTS = [
    "outputs/literature_benchmark_v5.0A/literature_benchmark_summary_v50A.json",
    "outputs/monte_carlo_v5.0B/monte_carlo_summary_v50B.json",
    "outputs/plausibility_guardrails_v5.0C/plausibility_guardrails_summary_v50C.json",
    "outputs/scenario_solvability_v5.0D/scenario_solvability_summary_v50D.json",
    "outputs/ui_human_factors_v5.0E/ui_human_factors_summary_v50E.json",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_yaml(path: Path) -> Any:
    if not path.exists() or yaml is None:
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _short_file_list(patterns: Iterable[str], limit: int = 80) -> List[str]:
    files: List[str] = []
    for pat in patterns:
        files.extend(str(p.relative_to(ROOT)) for p in ROOT.glob(pat) if p.is_file())
    return sorted(set(files))[:limit]


def collect_methods_metadata() -> Dict[str, Any]:
    model_registry = _read_yaml(ROOT / "data" / "model_registry.yaml")
    pediatric_profiles = _read_yaml(ROOT / "data" / "pediatric_profiles.yaml")
    scenario_manifest = _read_yaml(ROOT / "data" / "scenario_engine_v2_step4.44.yaml")
    guardrails = _read_yaml(ROOT / "data" / "plausibility_guardrails_v5.0C.yaml")

    validation_summaries: Dict[str, Any] = {}
    for rel in VALIDATION_ARTIFACTS:
        data = _read_json(ROOT / rel)
        validation_summaries[Path(rel).parent.name] = data if data is not None else {"status": "missing"}

    tests = _short_file_list(["tests/test_v5*.py", "tests/test_v4*.py"], limit=120)
    docs = _short_file_list(["docs/*v5*.md", "docs/*step4*.md"], limit=120)

    return {
        "schema": SCHEMA,
        "created_utc": _utc_now(),
        "safety_scope": SAFETY_SCOPE,
        "core_modules": CORE_MODULES,
        "model_registry_present": model_registry is not None,
        "pediatric_profiles_present": pediatric_profiles is not None,
        "scenario_manifest_present": scenario_manifest is not None,
        "guardrails_present": guardrails is not None,
        "scenario_count": _count_scenarios(scenario_manifest),
        "validation_summaries": validation_summaries,
        "test_files": tests,
        "documentation_files": docs,
        "major_assumptions": build_major_assumptions(model_registry, guardrails),
        "limitations": build_limitations(),
    }


def _count_scenarios(manifest: Any) -> int:
    if isinstance(manifest, dict):
        for key in ("scenarios", "scenario_pack", "cases"):
            val = manifest.get(key)
            if isinstance(val, list):
                return len(val)
            if isinstance(val, dict):
                return len(val)
    return 0


def build_major_assumptions(model_registry: Any, guardrails: Any) -> List[str]:
    assumptions = [
        "The model uses surrogate physiology rather than patient-specific mechanistic equations.",
        "Age/weight phenotype scaling is approximate and intended for training plausibility.",
        "Drug and vasoactive responses are directional and receptor-weighted, not individual PK/PD predictions.",
        "Critical-event timing is scenario-authored and designed for educational tempo.",
        "Recovery and deterioration are rule-based and constrained by plausibility guardrails.",
        "Displayed laboratory values are simulated trend surrogates, not diagnostic calculations.",
    ]
    if isinstance(guardrails, dict):
        assumptions.append("Biological extrema are clamped by an explicit v5.0C plausibility guardrail registry.")
    if isinstance(model_registry, dict):
        assumptions.append("Active model components are traceable to the repository model registry where present.")
    return assumptions


def build_limitations() -> List[str]:
    return [
        "Not calibrated against individual patient data.",
        "Not externally validated as a clinical predictor.",
        "Not intended for dosing, diagnosis, triage or therapeutic decision-making.",
        "Literature benchmarks define broad corridors, not high-fidelity validation targets.",
        "User-interface audits are static/human-factors checks, not formal usability trials.",
        "Monte Carlo runs are robustness tests of simulated behavior, not evidence of clinical accuracy.",
    ]


def render_methods_appendix(metadata: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines += [
        "# Methods Appendix — Pediatric Critical Care Simulator v3.1",
        "",
        f"Generated: `{metadata['created_utc']}`",
        "",
        "## Scope and intended use",
        metadata["safety_scope"],
        "",
        "## Active model components",
    ]
    for m in metadata["core_modules"]:
        lines.append(f"- {m}")
    lines += ["", "## Major modelling assumptions"]
    for a in metadata["major_assumptions"]:
        lines.append(f"- {a}")
    lines += ["", "## Validation and audit artifacts"]
    for name, summary in metadata["validation_summaries"].items():
        if isinstance(summary, dict) and summary.get("status") == "missing":
            lines.append(f"- `{name}`: missing in current checkout")
        else:
            compact = _compact_summary(summary)
            lines.append(f"- `{name}`: {compact}")
    lines += ["", "## Scenario coverage"]
    lines.append(f"- Scenario manifest present: {metadata['scenario_manifest_present']}")
    lines.append(f"- Scenario count detected: {metadata['scenario_count']}")
    lines += ["", "## Reproducibility controls"]
    lines += [
        "- Deterministic export bundle available from v5.1A.",
        "- Session JSON, timeline CSV, intervention CSV, manifest hashes and structured Markdown are exportable.",
        "- Seed metadata are recorded when supplied by the caller.",
    ]
    lines += ["", "## Known limitations"]
    for l in metadata["limitations"]:
        lines.append(f"- {l}")
    lines += ["", "## Traceability files"]
    lines.append("### Tests")
    for t in metadata["test_files"][:60]:
        lines.append(f"- `{t}`")
    lines.append("")
    lines.append("### Documentation")
    for d in metadata["documentation_files"][:60]:
        lines.append(f"- `{d}`")
    lines.append("")
    lines.append("## Safety statement")
    lines.append("This appendix supports transparent reporting of a research-alpha educational simulator. This is not clinical validation and must not be interpreted as clinical validation.")
    return "\n".join(lines)


def _compact_summary(summary: Any) -> str:
    if not isinstance(summary, dict):
        return "present"
    keys = ["checks", "pass", "passed", "review", "critical", "critical_findings", "review_findings", "runs", "stable_runs", "flagged_runs", "scenarios", "playable", "recoverable"]
    parts = []
    for k in keys:
        if k in summary:
            parts.append(f"{k}={summary[k]}")
    return ", ".join(parts) if parts else "present"


def save_methods_appendix(output_dir: Path | None = None) -> Dict[str, Any]:
    out = output_dir or OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    metadata = collect_methods_metadata()
    md = render_methods_appendix(metadata)
    md_path = out / "methods_appendix_v51B.md"
    json_path = out / "methods_appendix_metadata_v51B.json"
    md_path.write_text(md, encoding="utf-8")
    json_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    def _display_path(path: Path) -> str:
        try:
            return str(path.relative_to(ROOT))
        except ValueError:
            return str(path)

    return {
        "status": "saved",
        "schema": SCHEMA,
        "files": {
            "methods_appendix_md": _display_path(md_path),
            "metadata_json": _display_path(json_path),
        },
        "core_modules": len(metadata["core_modules"]),
        "assumptions": len(metadata["major_assumptions"]),
        "limitations": len(metadata["limitations"]),
    }


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(save_methods_appendix(), indent=2))
