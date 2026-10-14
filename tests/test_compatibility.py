from __future__ import annotations

from cepio.compatibility import (
    MigrationDeclaration,
    MigrationManifest,
    analyze_snapshots,
    evaluate_compatibility,
)


def _snapshot(version: str = "0.1.0", *, relationship: bool = True, extra_class: bool = False):
    classes = ["urn:cepio:A"]
    if extra_class:
        classes.append("urn:cepio:B")
    return {
        "property_contract": "mappings/canonical_properties.yaml",
        "modules": {
            "x": {
                "version": version,
                "namespace": "urn:cepio:",
                "classes": classes,
                "relationships": ["urn:cepio:r"] if relationship else [],
                "datatype_properties": ["urn:cepio:p"],
                "parents": [],
                "domains": [["urn:cepio:r", "urn:cepio:A"]] if relationship else [],
                "ranges": [["urn:cepio:r", "urn:cepio:A"]] if relationship else [],
                "datatype_ranges": [["urn:cepio:p", "http://www.w3.org/2001/XMLSchema#string"]],
            }
        },
    }


def test_additive_change_passes_with_patch_version_bump():
    old = _snapshot()
    new = _snapshot("0.1.1", extra_class=True)
    report = evaluate_compatibility(
        old,
        new,
        baseline_ref="base",
        baseline_label="baseline",
    )
    assert report.compatible
    assert any(change.kind == "class_added" for change in report.additive)


def test_breaking_removal_fails_without_explicit_migration():
    old = _snapshot()
    new = _snapshot("0.2.0", relationship=False)
    report = evaluate_compatibility(
        old,
        new,
        baseline_ref="base",
        baseline_label="baseline",
    )
    assert not report.compatible
    assert any(change.kind == "relationship_removed" for change in report.undeclared_breaking)


def test_declared_breaking_change_passes_when_version_policy_is_satisfied():
    old = _snapshot()
    new = _snapshot("0.2.0", relationship=False)
    changes = analyze_snapshots(old, new)
    declarations = tuple(
        MigrationDeclaration(
            change=change.key,
            rationale="Relationship is replaced by a new operational contract.",
            strategy="rewrite",
            replacement="urn:cepio:r2",
        )
        for change in changes
        if change.breaking
    )
    migration = MigrationManifest(
        schema_version="1",
        migration_id="test-removal",
        from_ref="base",
        description="Intentional relationship contract replacement.",
        issue="#4",
        declarations=declarations,
    )
    report = evaluate_compatibility(
        old,
        new,
        baseline_ref="base",
        baseline_label="baseline",
        migrations=[migration],
    )
    assert report.compatible
    assert report.declared_breaking
    assert not report.undeclared_breaking


def test_migration_cannot_waive_required_semantic_version_bump():
    old = _snapshot()
    new = _snapshot("0.1.0", relationship=False)
    changes = analyze_snapshots(old, new)
    migration = MigrationManifest(
        schema_version="1",
        migration_id="bad-version",
        from_ref="base",
        description="Intentional break without version bump.",
        issue="#4",
        declarations=tuple(
            MigrationDeclaration(
                change=change.key,
                rationale="Test",
                strategy="manual",
            )
            for change in changes
            if change.breaking
        ),
    )
    report = evaluate_compatibility(
        old,
        new,
        baseline_ref="base",
        baseline_label="baseline",
        migrations=[migration],
    )
    assert not report.compatible
    assert any("does not satisfy required" in error for error in report.errors)


def test_stale_migration_declaration_fails_closed():
    old = _snapshot()
    new = _snapshot("0.1.1", extra_class=True)
    migration = MigrationManifest(
        schema_version="1",
        migration_id="stale",
        from_ref="base",
        description="Stale migration should not silently approve unrelated changes.",
        issue="#4",
        declarations=(
            MigrationDeclaration(
                change="class_removed:x:urn:cepio:Missing",
                rationale="Test",
                strategy="manual",
            ),
        ),
    )
    report = evaluate_compatibility(
        old,
        new,
        baseline_ref="base",
        baseline_label="baseline",
        migrations=[migration],
    )
    assert not report.compatible
    assert report.stale_declarations == ["class_removed:x:urn:cepio:Missing"]


def test_namespace_change_is_breaking():
    old = _snapshot()
    new = _snapshot("0.2.0")
    new["modules"]["x"]["namespace"] = "urn:cepio:v2:"
    changes = analyze_snapshots(old, new)
    assert any(change.kind == "namespace_changed" and change.breaking for change in changes)


def test_new_constraint_on_existing_relationship_is_breaking():
    old = _snapshot()
    old["modules"]["x"]["ranges"] = []
    new = _snapshot("0.2.0")
    changes = analyze_snapshots(old, new)
    assert any(change.kind == "range_constraint_added" and change.breaking for change in changes)
