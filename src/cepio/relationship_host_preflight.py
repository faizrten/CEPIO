"""Read-only cgroup-v2 resource ceiling inspection for relationship host planning.

This optional host-owned probe never installs limits, starts a worker, grants
source access, or qualifies a production deployment. A passing snapshot only
reports that configured kernel ceilings match a trusted local policy at that
instant. It must not be exposed as a user-selectable file path or remote API.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RelationshipHostCeilingPolicy(BaseModel):
    """Trusted operator limits; never accepted from an agent's query payload."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_memory_bytes: int = Field(gt=0)
    max_pids: int = Field(gt=0)
    max_cpu_cores: float = Field(gt=0, allow_inf_nan=False)


class RelationshipHostResourceEvidence(BaseModel):
    """Current local ceiling evidence; explicitly not production admission."""

    model_config = ConfigDict(frozen=True)

    bounded_candidate: bool
    findings: tuple[str, ...]
    memory_limit_bytes: int | None
    pids_limit: int | None
    cpu_limit_cores: float | None
    memory_used_bytes: int | None
    pids_used: int | None
    evidence_scope: Literal["local_read_only_cgroup_v2"] = "local_read_only_cgroup_v2"
    production_qualified: Literal[False] = False


def _read_small(directory: Path, name: str) -> str | None:
    """Bound local kernel-file reads and reject unavailable/non-ASCII values."""
    try:
        with (directory / name).open("rb") as handle:
            raw = handle.read(257)
        if len(raw) > 256:
            return None
        return raw.decode("ascii").strip()
    except (OSError, UnicodeDecodeError):
        return None


def _integer(text: str | None, *, allow_zero: bool = False) -> int | None:
    if text is None or not text.isascii() or not text.isdecimal():
        return None
    value = int(text)
    if value > (2**63 - 1) or (value < 0 if allow_zero else value <= 0):
        return None
    return value


def inspect_relationship_cgroup(
    cgroup_dir: Path,
    policy: RelationshipHostCeilingPolicy,
) -> RelationshipHostResourceEvidence:
    """Compare host-provided cgroup-v2 files to explicit ceilings without writes.

    This cannot validate identity, per-tenant isolation, active process membership,
    ancestor/host limits, disk I/O, fairness, launcher startup, future revocation,
    repeated health, or artifact integrity. A candidate is not production authority.
    """
    controllers = _read_small(cgroup_dir, "cgroup.controllers")
    memory_limit = _integer(_read_small(cgroup_dir, "memory.max"))
    pids_limit = _integer(_read_small(cgroup_dir, "pids.max"))
    memory_used = _integer(_read_small(cgroup_dir, "memory.current"), allow_zero=True)
    pids_used = _integer(_read_small(cgroup_dir, "pids.current"), allow_zero=True)
    cpu_parts = (_read_small(cgroup_dir, "cpu.max") or "").split()
    cpu_quota = _integer(cpu_parts[0]) if len(cpu_parts) == 2 else None
    cpu_period = _integer(cpu_parts[1]) if len(cpu_parts) == 2 else None
    cpu_cores = cpu_quota / cpu_period if cpu_quota is not None and cpu_period else None

    findings: list[str] = []
    if controllers is None or not {"cpu", "memory", "pids"}.issubset(controllers.split()):
        findings.append("cgroup_v2_controllers_unverified")
    if memory_limit is None or memory_limit > policy.max_memory_bytes:
        findings.append("memory_ceiling_missing_or_excessive")
    if pids_limit is None or pids_limit > policy.max_pids:
        findings.append("pid_ceiling_missing_or_excessive")
    if cpu_cores is None or cpu_cores > policy.max_cpu_cores:
        findings.append("cpu_quota_missing_or_excessive")
    if memory_used is None or memory_limit is None or memory_used >= memory_limit:
        findings.append("memory_usage_unverified_or_exhausted")
    if pids_used is None or pids_limit is None or pids_used >= pids_limit:
        findings.append("pid_usage_unverified_or_exhausted")

    return RelationshipHostResourceEvidence(
        bounded_candidate=not findings,
        findings=tuple(findings),
        memory_limit_bytes=memory_limit,
        pids_limit=pids_limit,
        cpu_limit_cores=cpu_cores,
        memory_used_bytes=memory_used,
        pids_used=pids_used,
    )
