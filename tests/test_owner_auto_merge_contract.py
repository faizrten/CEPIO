"""Exercise owner-only merge eligibility without requiring GitHub credentials."""

import shutil
import subprocess
from pathlib import Path

import pytest


def test_owner_only_auto_merge_admission():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is not available in this environment")
    scenario = Path(__file__).with_name("owner_auto_merge_admission.test.cjs")
    result = subprocess.run(
        [node, str(scenario)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS: 16 founder-only automation cases" in result.stdout
