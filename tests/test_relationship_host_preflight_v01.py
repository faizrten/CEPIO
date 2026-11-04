"""Offline fail-closed cgroup resource inspection; no host configuration changes."""

import pytest
from pydantic import ValidationError

from cepio.relationship_host_preflight import (
    RelationshipHostCeilingPolicy,
    _integer,
    _read_small,
    inspect_relationship_cgroup,
)


@pytest.fixture
def limits(tmp_path):
    values = {
        "cgroup.type": "domain",
        "memory.max": "268435456",
        "memory.current": "1048576",
        "pids.max": "16",
        "pids.current": "2",
        "cpu.max": "50000 100000",
    }
    for name, content in values.items():
        (tmp_path / name).write_text(content, encoding="ascii")
    policy = RelationshipHostCeilingPolicy(
        max_memory_bytes=268435456, max_pids=16, max_cpu_cores=0.5
    )
    return tmp_path, policy


def test_bounded_snapshot_is_explicitly_not_production_authority(limits):
    directory, policy = limits
    result = inspect_relationship_cgroup(directory, policy)
    assert result.bounded_candidate is True
    assert result.findings == ()
    assert result.memory_limit_bytes == 268435456
    assert result.cpu_limit_cores == 0.5
    assert result.pids_limit == 16
    assert result.memory_used_bytes == 1048576
    assert result.pids_used == 2
    assert result.evidence_scope == "local_read_only_cgroup_v2"
    assert result.production_qualified is False
    assert result.model_dump()["production_qualified"] is False
    assert (directory / "memory.max").read_text() == "268435456"


@pytest.mark.parametrize(
    ("name", "value", "problem"),
    [
        ("cgroup.type", "domain invalid", "cgroup_v2_membership_unverified"),
        ("memory.max", "max", "memory_ceiling_missing_or_excessive"),
        ("memory.max", "536870912", "memory_ceiling_missing_or_excessive"),
        ("pids.max", "max", "pid_ceiling_missing_or_excessive"),
        ("pids.max", "17", "pid_ceiling_missing_or_excessive"),
        ("cpu.max", "max 100000", "cpu_quota_missing_or_excessive"),
        ("cpu.max", "100000 100000", "cpu_quota_missing_or_excessive"),
        ("cpu.max", "broken", "cpu_quota_missing_or_excessive"),
        ("memory.current", "268435456", "memory_usage_unverified_or_exhausted"),
        ("pids.current", "16", "pid_usage_unverified_or_exhausted"),
        ("pids.current", "missing", "pid_usage_unverified_or_exhausted"),
    ],
)
def test_misconfigured_or_exhausted_limit_fails_closed(limits, name, value, problem):
    directory, policy = limits
    (directory / name).write_text(value, encoding="ascii")
    result = inspect_relationship_cgroup(directory, policy)
    assert result.bounded_candidate is False
    assert problem in result.findings
    assert result.production_qualified is False


def test_missing_files_are_not_mistaken_for_unbounded_access(limits):
    directory, policy = limits
    for name in (
        "cgroup.type",
        "memory.max",
        "pids.max",
        "cpu.max",
        "memory.current",
        "pids.current",
    ):
        (directory / name).unlink()
    result = inspect_relationship_cgroup(directory, policy)
    assert not result.bounded_candidate
    assert len(result.findings) == 6
    assert result.memory_limit_bytes is None
    assert result.pids_limit is None
    assert result.cpu_limit_cores is None


def test_cgroup_read_is_bounded_and_rejects_non_ascii(limits):
    directory, _ = limits
    (directory / "memory.max").write_bytes(b"7" * 257)
    assert _read_small(directory, "memory.max") is None
    (directory / "memory.max").write_bytes(b"\xff")
    assert _read_small(directory, "memory.max") is None
    assert _read_small(directory, "does-not-exist") is None
    (directory / "memory.max").write_text("42\n")
    assert _read_small(directory, "memory.max") == "42"


@pytest.mark.parametrize(
    ("value", "allow_zero", "expected"),
    [
        (None, False, None),
        ("", False, None),
        ("-1", False, None),
        ("max", False, None),
        ("0", False, None),
        ("0", True, 0),
        ("42", False, 42),
        (str(2**63), False, None),
        ("not-number", False, None),
    ],
)
def test_integer_parser_rejects_unbounded_and_invalid_values(value, allow_zero, expected):
    assert _integer(value, allow_zero=allow_zero) == expected


def test_policy_rejects_unbounded_or_invalid_host_ceiling():
    for kwargs in (
        {"max_memory_bytes": 0, "max_pids": 16, "max_cpu_cores": 1.0},
        {"max_memory_bytes": 256, "max_pids": 0, "max_cpu_cores": 1.0},
        {"max_memory_bytes": 256, "max_pids": 16, "max_cpu_cores": float("inf")},
    ):
        with pytest.raises(ValidationError):
            RelationshipHostCeilingPolicy(**kwargs)
