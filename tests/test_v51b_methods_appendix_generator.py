from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.methods_appendix import collect_methods_metadata, render_methods_appendix, save_methods_appendix


def test_methods_metadata_contains_core_reporting_fields():
    meta = collect_methods_metadata()
    assert meta["schema"] == "pdt-methods-appendix-v5.1B"
    assert len(meta["core_modules"]) >= 8
    assert len(meta["major_assumptions"]) >= 6
    assert len(meta["limitations"]) >= 6
    assert "Educational" in meta["safety_scope"]


def test_methods_appendix_renders_required_sections():
    md = render_methods_appendix(collect_methods_metadata())
    for heading in [
        "## Scope and intended use",
        "## Active model components",
        "## Major modelling assumptions",
        "## Validation and audit artifacts",
        "## Known limitations",
        "## Safety statement",
    ]:
        assert heading in md
    assert "not clinical validation" in md.lower()


def test_methods_appendix_saves_outputs(tmp_path: Path):
    result = save_methods_appendix(output_dir=tmp_path)
    assert result["status"] == "saved"
    assert (tmp_path / "methods_appendix_v51B.md").exists()
    assert (tmp_path / "methods_appendix_metadata_v51B.json").exists()
