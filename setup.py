from __future__ import annotations

import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py


ROOT = Path(__file__).parent
RESOURCE_DIRS = ("ontologies", "mappings", "shapes", "actions", "policies", "profiles")
RESOURCE_FILES = ("ontology-modules.yaml",)


class build_py(_build_py):
    def run(self):
        super().run()
        destination = Path(self.build_lib) / "cepio" / "resources"
        destination.mkdir(parents=True, exist_ok=True)
        for directory in RESOURCE_DIRS:
            source = ROOT / directory
            if source.exists():
                shutil.copytree(source, destination / directory, dirs_exist_ok=True)
        for filename in RESOURCE_FILES:
            source = ROOT / filename
            if source.exists():
                shutil.copy2(source, destination / filename)


setup(cmdclass={"build_py": build_py})
