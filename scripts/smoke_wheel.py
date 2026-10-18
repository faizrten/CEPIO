"""Smoke-test the built CEPIO wheel outside the repository checkout."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import tempfile
import venv


ROOT = Path(__file__).resolve().parents[1]


def find_wheel(dist: Path) -> Path:
    wheels = sorted(dist.glob("cepio-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"Expected exactly one CEPIO wheel in {dist}, found {len(wheels)}")
    return wheels[0].resolve()


def venv_python(environment: Path) -> Path:
    if os.name == "nt":
        return environment / "Scripts" / "python.exe"
    return environment / "bin" / "python"


def run_wheel_smoke(wheel: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="cepio-wheel-smoke-") as temp_dir:
        temp = Path(temp_dir)
        environment = temp / "venv"
        venv.EnvBuilder(with_pip=True, system_site_packages=True).create(environment)
        python = venv_python(environment)

        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-deps",
                "--force-reinstall",
                str(wheel),
            ],
            cwd=temp,
            check=True,
        )

        probe = """
import os
from pathlib import Path

import cepio
from cepio.bootstrap import build_runtime_from_settings
from cepio.resource_paths import resolve_resource_root

repo_root = Path(os.environ["CEPIO_REPO_ROOT"]).resolve()
module_path = Path(cepio.__file__).resolve()
root = resolve_resource_root().resolve()
assert not module_path.is_relative_to(repo_root), (module_path, repo_root)
assert not root.is_relative_to(repo_root), (root, repo_root)
assert cepio.__version__
assert (root / "ontology-modules.yaml").exists()
assert (root / "ontologies").is_dir()
assert (root / "profiles" / "satorp" / "profile.yaml").exists()
runtime = build_runtime_from_settings()
assert runtime.module_catalogue.modules
assert runtime.profile_versions == {"satorp": "0.1.0"}
assert runtime.type_registry.is_declared_type("https://cepio.org/profile/satorp#AmiralAsset")
print(f"CEPIO wheel smoke passed: {cepio.__version__} from {module_path}")
"""
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env.update(
            {
                "CEPIO_ENVIRONMENT": "test",
                "CEPIO_DB_URL": "memory://",
                "CEPIO_PROFILES": "satorp",
                "CEPIO_REPO_ROOT": str(ROOT),
            }
        )
        subprocess.run([str(python), "-c", probe], cwd=temp, env=env, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    run_wheel_smoke(find_wheel(args.dist))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
