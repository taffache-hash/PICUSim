from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v324_drug_audit_panel_is_snapshot_only():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")

    assert 'id="drugAuditRefreshBtn"' in html
    assert 'id="drugAuditGrid"' in html
    assert "Aggiorna audit" in html
    assert "const DRUG_AUDIT_GROUPS" in js
    assert "function refreshDrugAudit" in js
    assert "profile=full" in js
    assert "drugAuditRefreshBtn" in js
    assert "setInterval(() => refreshDrugAudit" not in js
    assert ".drug-audit-grid" in css
    assert ".drug-audit-card.active" in css


def test_v324_drug_audit_covers_core_drug_classes():
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    for needle in [
        "Adrenaline",
        "Ketamine",
        "Morphine",
        "Rocuronium",
        "Salbutamol",
        "Hydrocortisone",
        "Insulin",
        "Furosemide",
        "Vancomycin",
        "Piperacillin-tazobactam",
        "C_furosemide_mg_L",
        "morphine_renal_accumulation_risk",
        "piperacillin_target_attainment",
    ]:
        assert needle in js
