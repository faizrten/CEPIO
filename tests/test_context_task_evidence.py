from datetime import datetime, timezone

import pytest

from cepio.memory import (
    ContextAssembler, ContextBudget, ContextCandidate, MemoryProvenance, MemoryRecord,
)


def record(tenant="sample", expired=False):
    return ContextCandidate(
        record=MemoryRecord(
            id="e", kind="SEMANTIC", scope="TENANT", summary="sample",
            provenance=MemoryProvenance(source_kind="synthetic"), tenant_id=tenant,
            created_at=datetime(2019, 1, 1, tzinfo=timezone.utc),
            expires_at=datetime(2020, 1, 1, tzinfo=timezone.utc) if expired else None,
        ),
        estimated_tokens=2,
    )


@pytest.mark.parametrize("rows,budget,expected", [
    ([], 8, "BLOCKED"),
    ([record("other")], 8, "BLOCKED"),
    ([record(expired=True)], 8, "BLOCKED"),
    ([record(), record()], 8, "BLOCKED"),
    ([record()], 1, "BLOCKED"),
    ([record()], 8, "READY"),
])
def test_task_requires_visible_current_unambiguous_evidence(rows, budget, expected):
    result = ContextAssembler().assemble_for_task(
        rows, required_ids=frozenset(["e"]), tenant_id="sample",
        budget=ContextBudget(max_tokens=budget),
        at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert result.status == expected
    assert [candidate.record.id for candidate in result.selected] == (
        ["e"] if expected == "READY" else []
    )
