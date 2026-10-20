"""Public contributor checks for the Labs ownership boundary; no corpus access."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_legacy_blind_ask_explains_migration_without_claiming_pass():
    result = subprocess.run(
        ["make", "blind-ask"], cwd=ROOT, text=True, capture_output=True, check=False
    )
    assert result.returncode != 0
    assert "CEPIO Labs" in result.stdout
    assert "docs/scenario-lab-migration.md" in result.stdout


def test_public_validation_has_no_private_corpus_dependency():
    result = subprocess.run(
        ["make", "-n", "validate"], cwd=ROOT, text=True, capture_output=True, check=True
    )
    assert "validate_shacl" in result.stdout
    assert "blind-ask" not in result.stdout
    assert "run_drilling_mvp" not in result.stdout
    assert "github.com" not in result.stdout


def test_migrated_drilling_corpus_is_not_packaged_in_public_checkout():
    for path in (
        "scripts/generate_drilling_mvp_dataset.py",
        "scripts/extend_drilling_mvp_multimodal_v02.py",
        "scripts/run_drilling_mvp_acceptance.py",
        "scripts/run_drilling_mvp_blind_ask.py",
        "scripts/report_drilling_mvp_blind_ask.py",
    ):
        assert not (ROOT / path).exists()
    for version in ("drilling-v0.1", "drilling-v0.2"):
        assert not any((ROOT / "mvp/datasets" / version).rglob("*.*"))
