from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from .runtime import CEPIORuntime


class IndustryIQPack(Protocol):
    """Runtime extension contract for domain/industry intelligence.

    CEPIO Core owns the governed runtime mechanics. Industry IQ packs register
    domain-specific functions, decisions and actions without making them permanent
    Core capabilities.
    """

    pack_id: str
    version: str

    def install(self, runtime: CEPIORuntime) -> None: ...


def install_industry_iq_packs(
    runtime: CEPIORuntime, packs: Iterable[IndustryIQPack]
) -> dict[str, str]:
    """Install Industry IQ packs exactly once and expose deterministic metadata."""

    installed = dict(runtime.industry_iq_packs)
    for pack in packs:
        if pack.pack_id in installed:
            raise ValueError(f"Industry IQ pack already installed: {pack.pack_id}")
        pack.install(runtime)
        installed[pack.pack_id] = pack.version

    installed = dict(sorted(installed.items()))
    runtime.industry_iq_packs = installed
    return installed
