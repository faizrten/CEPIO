from pathlib import Path
from runpy import run_path

import pytest


SMOKE = run_path(str(Path(__file__).resolve().parents[1] / "scripts" / "smoke_wheel.py"))
find_wheel = SMOKE["find_wheel"]


def test_find_wheel_requires_exactly_one_cepio_artifact(tmp_path):
    with pytest.raises(RuntimeError, match="Expected exactly one CEPIO wheel"):
        find_wheel(tmp_path)

    wheel = tmp_path / "cepio-0.4.0-py3-none-any.whl"
    wheel.write_bytes(b"wheel")
    assert find_wheel(tmp_path) == wheel.resolve()

    (tmp_path / "cepio-0.4.1-py3-none-any.whl").write_bytes(b"wheel")
    with pytest.raises(RuntimeError, match="found 2"):
        find_wheel(tmp_path)
