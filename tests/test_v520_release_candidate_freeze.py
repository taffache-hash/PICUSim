from pathlib import Path
import yaml


def test_release_candidate_manifest_exists_and_is_frozen():
    path = Path('data/release_candidate_manifest_v5.2.yaml')
    assert path.exists()
    data = yaml.safe_load(path.read_text())
    assert data['status'] == 'release_candidate_freeze'
    assert data['not_for_clinical_use'] is True
    assert data['freeze_rules']['no_model_changes_after_freeze_without_new_step'] is True
    assert data['file_count'] > 100


def test_release_candidate_docs_exist():
    assert Path('docs/RELEASE_CANDIDATE_FREEZE_v5.2.md').exists()
    assert Path('docs/CODEX_HANDOFF_v5.2_to_next.md').exists()
