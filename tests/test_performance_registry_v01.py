from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cepio.performance_contract import (
    PerformanceContract,
    PerformanceNode,
    PerformanceSubject,
    PerformanceTarget,
)
from cepio.performance_registry import (
    InMemoryPerformanceContractStore,
    PerformanceContractLifecycle,
    PerformanceContractRegistry,
    PerformanceContractRegistryError,
    PerformanceContractRevision,
    PerformanceContractRevisionRef,
    SQLitePerformanceContractStore,
)
from cepio.performance_resolution import PerformanceContractOverlay

NOW = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)


def industry(version: str = "1.0.0", *, target: float = 0.95) -> PerformanceContract:
    return PerformanceContract(
        id="process-industry",
        version=version,
        name=f"Process industry {version}",
        layer="industry_reference",
        subjects=(PerformanceSubject(id="industry", kind="enterprise", name="Industry"),),
        nodes=(
            PerformanceNode(
                id="availability",
                kind="kpi",
                name="Availability",
                scope_subject_id="industry",
                target=PerformanceTarget(operator="gte", value=target),
            ),
        ),
    )


def organization(version: str = "1.0.0") -> PerformanceContractOverlay:
    return PerformanceContractOverlay(
        id="refinery-co",
        version=version,
        name=f"Refinery Co {version}",
        layer="organization",
        organization_id="refinery-co",
        extends_contract_id="process-industry",
        subjects=(
            PerformanceSubject(id="refinery", kind="enterprise", name="Refinery Co"),
        ),
    )


def role(version: str = "1.0.0") -> PerformanceContractOverlay:
    return PerformanceContractOverlay(
        id="reliability-role",
        version=version,
        name=f"Reliability role {version}",
        layer="role",
        extends_contract_id="refinery-co",
        subjects=(
            PerformanceSubject(
                id="reliability-engineer",
                kind="persona",
                name="Reliability Engineer",
                parent_id="refinery",
            ),
        ),
    )


def individual(version: str = "1.0.0") -> PerformanceContractOverlay:
    return PerformanceContractOverlay(
        id="engineer-42",
        version=version,
        name=f"Engineer 42 {version}",
        layer="individual",
        extends_contract_id="reliability-role",
        subjects=(
            PerformanceSubject(
                id="engineer-42-person",
                kind="individual",
                name="Engineer 42",
                parent_id="reliability-engineer",
            ),
        ),
    )


def revision(definition, *, lifecycle="draft", parent=None, org=None):
    return PerformanceContractRevision(
        contract_id=definition.id,
        version=definition.version,
        definition=definition,
        definition_hash=f"hash-{definition.id}-{definition.version}",
        lifecycle=lifecycle,
        parent_revision=parent,
        effective_organization_id=org,
        created_at=NOW,
    )


def test_registry_pins_parent_versions_and_historical_resolution_does_not_drift():
    registry = PerformanceContractRegistry()
    first = registry.register(industry(), activate=True, created_at=NOW)
    org = registry.register(organization(), activate=True, created_at=NOW)
    role_revision = registry.register(role(), activate=True, created_at=NOW)
    person = registry.register(individual(), activate=True, created_at=NOW)

    assert first.lifecycle == PerformanceContractLifecycle.active
    assert org.parent_revision == first.ref
    assert role_revision.parent_revision == org.ref
    assert person.parent_revision == role_revision.ref
    assert person.effective_organization_id == "refinery-co"

    second = registry.register(industry("2.0.0", target=0.97), created_at=LATER)
    registry.activate(second.contract_id, second.version, activated_at=LATER)

    assert registry.get("process-industry", "1.0.0").lifecycle == PerformanceContractLifecycle.retired
    assert registry.get_active("process-industry").version == "2.0.0"

    resolved = registry.resolve("engineer-42")
    assert [item.version for item in resolved.source_revisions] == [
        "1.0.0",
        "1.0.0",
        "1.0.0",
        "1.0.0",
    ]
    availability = next(
        node for node in resolved.resolved.contract.nodes if node.id == "availability"
    )
    assert availability.target is not None
    assert availability.target.value == 0.95


def test_registry_explicit_parent_version_and_organization_listing():
    registry = PerformanceContractRegistry()
    registry.register(industry(), activate=True, created_at=NOW)
    registry.register(industry("2.0.0"), activate=True, created_at=LATER)

    org = registry.register(organization(), parent_version="1.0.0", created_at=LATER)
    registry.activate(org.contract_id, org.version, activated_at=LATER)
    registry.register(role(), activate=True, created_at=LATER)

    scoped = registry.list_for_organization("refinery-co")
    assert {item.contract_id for item in scoped} == {"refinery-co", "reliability-role"}
    with_reference = registry.list_for_organization(
        "refinery-co", include_industry_reference=True
    )
    assert {item.contract_id for item in with_reference} == {
        "process-industry",
        "refinery-co",
        "reliability-role",
    }
    assert len(registry.list_versions("process-industry")) == 2
    assert registry.resolve("refinery-co", "1.0.0", organization_id="refinery-co")


def test_registry_fail_closed_errors():
    registry = PerformanceContractRegistry()

    with pytest.raises(PerformanceContractRegistryError) as exc:
        registry.get("missing", "1")
    assert exc.value.code == "REVISION_NOT_FOUND"

    with pytest.raises(PerformanceContractRegistryError) as exc:
        registry.get_active("missing")
    assert exc.value.code == "ACTIVE_REVISION_NOT_FOUND"

    with pytest.raises(PerformanceContractRegistryError) as exc:
        registry.register(industry(), parent_version="1")
    assert exc.value.code == "UNEXPECTED_PARENT_VERSION"

    with pytest.raises(PerformanceContractRegistryError) as exc:
        registry.register(organization())
    assert exc.value.code == "ACTIVE_PARENT_NOT_FOUND"

    with pytest.raises(PerformanceContractRegistryError) as exc:
        registry.register(organization(), parent_version="missing")
    assert exc.value.code == "PARENT_REVISION_NOT_FOUND"

    registry.register(industry(), activate=True, created_at=NOW)
    with pytest.raises(PerformanceContractRegistryError) as exc:
        registry.register(industry())
    assert exc.value.code == "REVISION_ALREADY_EXISTS"

    org = registry.register(organization(), activate=True, created_at=NOW)
    with pytest.raises(PerformanceContractRegistryError) as exc:
        registry.resolve(org.contract_id, organization_id="another-refinery")
    assert exc.value.code == "ORGANIZATION_SCOPE_MISMATCH"

    registry.retire(org.contract_id, org.version, retired_at=LATER)
    with pytest.raises(PerformanceContractRegistryError) as exc:
        registry.activate(org.contract_id, org.version, activated_at=LATER)
    assert exc.value.code == "REVISION_RETIRED"


def test_registry_translates_resolution_error_on_invalid_layer_order():
    registry = PerformanceContractRegistry()
    registry.register(industry(), activate=True, created_at=NOW)
    invalid = PerformanceContractOverlay(
        id="bad-industry-child",
        version="1.0.0",
        name="Bad",
        layer="industry_reference",
        extends_contract_id="process-industry",
    )
    with pytest.raises(PerformanceContractRegistryError) as exc:
        registry.register(invalid)
    assert exc.value.code == "INVALID_LAYER_ORDER"


def test_registry_detects_missing_pinned_parent_hash_change_and_cycle():
    store = InMemoryPerformanceContractStore()
    registry = PerformanceContractRegistry(store)
    root = registry.register(industry(), activate=True, created_at=NOW)
    child = registry.register(organization(), created_at=NOW)

    del store._revisions[(root.contract_id, root.version)]
    with pytest.raises(PerformanceContractRegistryError) as exc:
        registry.resolve(child.contract_id, child.version)
    assert exc.value.code == "PINNED_PARENT_NOT_FOUND"

    store.create(root)
    key = (root.contract_id, root.version)
    store._revisions[key] = root.model_copy(update={"definition_hash": "tampered"})
    with pytest.raises(PerformanceContractRegistryError) as exc:
        registry.resolve(child.contract_id, child.version)
    assert exc.value.code == "PINNED_PARENT_HASH_MISMATCH"

    a_definition = PerformanceContractOverlay(
        id="a",
        version="1",
        name="A",
        layer="role",
        extends_contract_id="b",
    )
    b_definition = PerformanceContractOverlay(
        id="b",
        version="1",
        name="B",
        layer="organization",
        organization_id="refinery-co",
        extends_contract_id="a",
    )
    a_ref = PerformanceContractRevisionRef(contract_id="a", version="1", definition_hash="a")
    b_ref = PerformanceContractRevisionRef(contract_id="b", version="1", definition_hash="b")
    a = PerformanceContractRevision(
        contract_id="a",
        version="1",
        definition=a_definition,
        definition_hash="a",
        parent_revision=b_ref,
        created_at=NOW,
    )
    b = PerformanceContractRevision(
        contract_id="b",
        version="1",
        definition=b_definition,
        definition_hash="b",
        parent_revision=a_ref,
        created_at=NOW,
    )
    cycle_store = InMemoryPerformanceContractStore()
    cycle_store.create(a)
    cycle_store.create(b)
    with pytest.raises(PerformanceContractRegistryError) as exc:
        PerformanceContractRegistry(cycle_store).resolve("a", "1")
    assert exc.value.code == "INHERITANCE_CYCLE"


def test_in_memory_store_lifecycle_and_copy_semantics():
    store = InMemoryPerformanceContractStore()
    first = revision(industry())
    second = revision(industry("2.0.0"))

    assert store.get("missing", "1") is None
    assert store.get_active("process-industry") is None
    store.create(first)
    with pytest.raises(ValueError):
        store.create(first)
    store.create(second)
    assert [item.version for item in store.list("process-industry")] == ["1.0.0", "2.0.0"]
    assert len(store.list()) == 2

    with pytest.raises(KeyError):
        store.activate("missing", "1", activated_at=NOW)
    active_first = store.activate("process-industry", "1.0.0", activated_at=NOW)
    assert active_first.lifecycle == PerformanceContractLifecycle.active
    assert store.activate("process-industry", "1.0.0", activated_at=LATER).activated_at == NOW

    active_second = store.activate("process-industry", "2.0.0", activated_at=LATER)
    assert active_second.lifecycle == PerformanceContractLifecycle.active
    assert store.get("process-industry", "1.0.0").lifecycle == PerformanceContractLifecycle.retired

    with pytest.raises(ValueError):
        store.activate("process-industry", "1.0.0", activated_at=LATER)
    with pytest.raises(KeyError):
        store.retire("missing", "1", retired_at=LATER)
    retired = store.retire("process-industry", "2.0.0", retired_at=LATER)
    assert retired.lifecycle == PerformanceContractLifecycle.retired
    assert store.retire("process-industry", "2.0.0", retired_at=LATER) == retired


def test_sqlite_store_round_trip_lifecycle_overlay_and_errors(tmp_path):
    store = SQLitePerformanceContractStore(tmp_path / "performance.db")
    first = revision(industry())
    second = revision(industry("2.0.0"))
    parent_ref = first.ref
    overlay = revision(organization(), parent=parent_ref, org="refinery-co")

    assert store.get("missing", "1") is None
    assert store.get_active("process-industry") is None
    store.create(first)
    store.create(second)
    store.create(overlay)
    with pytest.raises(ValueError):
        store.create(first)

    loaded_overlay = store.get("refinery-co", "1.0.0")
    assert loaded_overlay is not None
    assert isinstance(loaded_overlay.definition, PerformanceContractOverlay)
    assert loaded_overlay.parent_revision == parent_ref
    assert loaded_overlay.effective_organization_id == "refinery-co"
    assert len(store.list()) == 3
    assert [item.version for item in store.list("process-industry")] == ["1.0.0", "2.0.0"]

    with pytest.raises(KeyError):
        store.activate("missing", "1", activated_at=NOW)
    active_first = store.activate("process-industry", "1.0.0", activated_at=NOW)
    assert active_first.lifecycle == PerformanceContractLifecycle.active
    assert store.get_active("process-industry").version == "1.0.0"
    assert store.activate("process-industry", "1.0.0", activated_at=LATER).activated_at == NOW

    store.activate("process-industry", "2.0.0", activated_at=LATER)
    assert store.get("process-industry", "1.0.0").lifecycle == PerformanceContractLifecycle.retired
    with pytest.raises(ValueError):
        store.activate("process-industry", "1.0.0", activated_at=LATER)

    with pytest.raises(KeyError):
        store.retire("missing", "1", retired_at=LATER)
    retired = store.retire("refinery-co", "1.0.0", retired_at=LATER)
    assert retired.lifecycle == PerformanceContractLifecycle.retired
    assert store.retire("refinery-co", "1.0.0", retired_at=LATER) == retired
    store.close()


def test_registry_with_sqlite_store_resolves_after_reopen(tmp_path):
    path = tmp_path / "registry.db"
    first_store = SQLitePerformanceContractStore(path)
    registry = PerformanceContractRegistry(first_store)
    registry.register(industry(), activate=True, created_at=NOW)
    registry.register(organization(), activate=True, created_at=NOW)
    first_store.close()

    second_store = SQLitePerformanceContractStore(path)
    reopened = PerformanceContractRegistry(second_store)
    result = reopened.resolve("refinery-co", organization_id="refinery-co")
    assert result.resolved.contract.organization_id == "refinery-co"
    assert [ref.contract_id for ref in result.source_revisions] == [
        "process-industry",
        "refinery-co",
    ]
    second_store.close()
