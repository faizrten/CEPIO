"""Deterministic specialization for CEPIO Performance Contracts.

A resolved :class:`PerformanceContract` is complete and directly evaluable. Sparse
specialization overlays are deliberately separate types so a role or individual layer
can reference inherited subjects/nodes without being mistaken for standalone
enterprise truth.

v0.2 adds explicit field patches and suppressions while preserving the v0.1 whole-entry
overlay contract unchanged for stored-hash and payload compatibility.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .performance_contract import (
    PERFORMANCE_CONTRACT_VERSION,
    PerformanceAccountability,
    PerformanceContract,
    PerformanceContractLayer,
    PerformanceContribution,
    PerformanceNode,
    PerformanceResponseBinding,
    PerformanceSubject,
)


PERFORMANCE_OVERLAY_V2_VERSION: Literal["0.2.0"] = "0.2.0"

_PATCHABLE_FIELDS: dict[str, frozenset[str]] = {
    "subject": frozenset({"name", "parent_id"}),
    "node": frozenset(
        {
            "name",
            "description",
            "scope_subject_id",
            "unit",
            "definition",
            "formula_ref",
            "reference_node_id",
            "target",
            "thresholds",
            "max_observation_age_seconds",
            "valid_from",
            "valid_to",
        }
    ),
    "contribution": frozenset({"weight", "confidence", "rationale"}),
    "response_binding": frozenset({"statuses", "workflow_definition_id", "rationale"}),
}

_CLEARABLE_FIELDS: dict[str, frozenset[str]] = {
    "subject": frozenset({"parent_id"}),
    "node": frozenset(
        {
            "description",
            "unit",
            "definition",
            "formula_ref",
            "reference_node_id",
            "target",
            "thresholds",
            "max_observation_age_seconds",
            "valid_from",
            "valid_to",
        }
    ),
    "contribution": frozenset({"weight", "confidence", "rationale"}),
    "response_binding": frozenset({"rationale"}),
}

_CLEAR_VALUES: dict[tuple[str, str], Any] = {
    ("subject", "parent_id"): None,
    ("node", "description"): None,
    ("node", "unit"): None,
    ("node", "definition"): None,
    ("node", "formula_ref"): None,
    ("node", "reference_node_id"): None,
    ("node", "target"): None,
    ("node", "thresholds"): (),
    ("node", "max_observation_age_seconds"): None,
    ("node", "valid_from"): None,
    ("node", "valid_to"): None,
    ("contribution", "weight"): None,
    ("contribution", "confidence"): None,
    ("contribution", "rationale"): None,
    ("response_binding", "rationale"): None,
}


class PerformanceContractOverlay(BaseModel):
    """Sparse v0.1 child contract that becomes valid only after parent resolution.

    Entries are additive by default. Reusing a subject, node, contribution, or
    response-binding identity is an explicit whole-entry override. Deletion and
    field-level patch semantics are intentionally not part of v0.1 specialization.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: Literal["0.1.0"] = PERFORMANCE_CONTRACT_VERSION
    id: str
    version: str
    name: str
    layer: PerformanceContractLayer
    extends_contract_id: str
    organization_id: str | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    subjects: tuple[PerformanceSubject, ...] = ()
    nodes: tuple[PerformanceNode, ...] = ()
    accountabilities: tuple[PerformanceAccountability, ...] = ()
    contributions: tuple[PerformanceContribution, ...] = ()
    response_bindings: tuple[PerformanceResponseBinding, ...] = ()

    @model_validator(mode="after")
    def validate_overlay(self) -> "PerformanceContractOverlay":
        if self.effective_from and self.effective_to and self.effective_from >= self.effective_to:
            raise ValueError("effective_from must be before effective_to")
        if not self.extends_contract_id:
            raise ValueError("performance overlay requires extends_contract_id")
        if self.extends_contract_id == self.id:
            raise ValueError("performance overlay cannot extend itself")

        subject_ids = [subject.id for subject in self.subjects]
        node_ids = [node.id for node in self.nodes]
        binding_ids = [binding.id for binding in self.response_bindings]
        accountability_keys = [_accountability_key(item) for item in self.accountabilities]
        contribution_keys = [_contribution_key(item) for item in self.contributions]
        if len(subject_ids) != len(set(subject_ids)):
            raise ValueError("performance overlay subject ids must be unique")
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("performance overlay node ids must be unique")
        if len(binding_ids) != len(set(binding_ids)):
            raise ValueError("performance overlay response binding ids must be unique")
        if len(accountability_keys) != len(set(accountability_keys)):
            raise ValueError("performance overlay accountabilities must be unique")
        if len(contribution_keys) != len(set(contribution_keys)):
            raise ValueError("performance overlay contributions must be unique")
        return self


class PerformanceFieldSet(BaseModel):
    """One explicit field assignment inside a v0.2 element patch."""

    model_config = ConfigDict(frozen=True)

    field: str = Field(min_length=1)
    value: Any


class PerformanceElementPatch(BaseModel):
    """Field-level refinement of one inherited effective graph element."""

    model_config = ConfigDict(frozen=True)

    element_type: Literal["subject", "node", "contribution", "response_binding"]
    element_key: str = Field(min_length=1)
    set_fields: tuple[PerformanceFieldSet, ...] = ()
    clear_fields: frozenset[str] = frozenset()
    reason: str | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> "PerformanceElementPatch":
        names = [item.field for item in self.set_fields]
        if len(names) != len(set(names)):
            raise ValueError("performance patch set fields must be unique")
        if not names and not self.clear_fields:
            raise ValueError("performance patch must set or clear at least one field")
        overlap = set(names) & set(self.clear_fields)
        if overlap:
            raise ValueError(
                "performance patch cannot set and clear the same field: "
                + ", ".join(sorted(overlap))
            )

        allowed = _PATCHABLE_FIELDS[self.element_type]
        unknown = (set(names) | set(self.clear_fields)) - set(allowed)
        if unknown:
            raise ValueError(
                f"performance {self.element_type} patch cannot modify fields: "
                + ", ".join(sorted(unknown))
            )

        non_clearable = set(self.clear_fields) - set(_CLEARABLE_FIELDS[self.element_type])
        if non_clearable:
            raise ValueError(
                f"performance {self.element_type} patch cannot clear fields: "
                + ", ".join(sorted(non_clearable))
            )
        return self


class PerformanceElementSuppression(BaseModel):
    """Explicit removal of one inherited element from the effective child graph.

    Suppression never cascades. Dependent references must also be explicitly suppressed
    or refined, otherwise final strict contract validation fails closed.
    """

    model_config = ConfigDict(frozen=True)

    element_type: Literal[
        "subject",
        "node",
        "accountability",
        "contribution",
        "response_binding",
    ]
    element_key: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class PerformanceContractOverlayV2(PerformanceContractOverlay):
    """v0.2 sparse overlay with explicit field patches and suppressions."""

    schema_version: Literal["0.2.0"] = PERFORMANCE_OVERLAY_V2_VERSION
    patches: tuple[PerformanceElementPatch, ...] = ()
    suppressions: tuple[PerformanceElementSuppression, ...] = ()

    @model_validator(mode="after")
    def validate_v2_operations(self) -> "PerformanceContractOverlayV2":
        patch_keys = [(item.element_type, item.element_key) for item in self.patches]
        suppression_keys = [
            (item.element_type, item.element_key) for item in self.suppressions
        ]
        if len(patch_keys) != len(set(patch_keys)):
            raise ValueError("performance overlay v0.2 patches must target unique elements")
        if len(suppression_keys) != len(set(suppression_keys)):
            raise ValueError(
                "performance overlay v0.2 suppressions must target unique elements"
            )

        conflicts = set(patch_keys) & set(suppression_keys)
        if conflicts:
            rendered = ", ".join(
                f"{element_type}:{element_key}"
                for element_type, element_key in sorted(conflicts)
            )
            raise ValueError(
                "performance overlay v0.2 cannot patch and suppress the same element: "
                + rendered
            )

        whole_entry_keys: set[tuple[str, str]] = {
            *[("subject", item.id) for item in self.subjects],
            *[("node", item.id) for item in self.nodes],
            *[
                ("accountability", _render_key(_accountability_key(item)))
                for item in self.accountabilities
            ],
            *[
                ("contribution", _render_key(_contribution_key(item)))
                for item in self.contributions
            ],
            *[("response_binding", item.id) for item in self.response_bindings],
        }
        operation_conflicts = (set(patch_keys) | set(suppression_keys)) & whole_entry_keys
        if operation_conflicts:
            rendered = ", ".join(
                f"{element_type}:{element_key}"
                for element_type, element_key in sorted(operation_conflicts)
            )
            raise ValueError(
                "performance overlay v0.2 operation conflicts with a whole-entry "
                "definition in the same overlay: "
                + rendered
            )
        return self


class PerformanceResolutionLineage(BaseModel):
    """Source contract that supplied one effective resolved graph element."""

    model_config = ConfigDict(frozen=True)

    element_type: Literal[
        "subject",
        "node",
        "accountability",
        "contribution",
        "response_binding",
    ]
    element_key: str
    source_contract_id: str
    source_contract_version: str
    source_layer: PerformanceContractLayer


class PerformanceResolutionOperation(BaseModel):
    """Auditable specialization operation contributed by one child layer."""

    model_config = ConfigDict(frozen=True)

    operation: Literal["add", "override", "patch", "suppress"]
    element_type: Literal[
        "subject",
        "node",
        "accountability",
        "contribution",
        "response_binding",
    ]
    element_key: str
    source_contract_id: str
    source_contract_version: str
    source_layer: PerformanceContractLayer
    changed_fields: tuple[str, ...] = ()
    reason: str | None = None


class ResolvedPerformanceContract(BaseModel):
    """Complete effective contract plus deterministic specialization provenance."""

    model_config = ConfigDict(frozen=True)

    contract: PerformanceContract
    source_contract_ids: tuple[str, ...]
    lineage: tuple[PerformanceResolutionLineage, ...]
    operations: tuple[PerformanceResolutionOperation, ...] = ()

    def source_for(self, element_type: str, element_key: str) -> PerformanceResolutionLineage:
        for item in self.lineage:
            if item.element_type == element_type and item.element_key == element_key:
                return item
        raise KeyError((element_type, element_key))


class PerformanceContractResolutionError(ValueError):
    """Fail-closed performance-contract composition failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


PerformanceContractDefinition = (
    PerformanceContract | PerformanceContractOverlayV2 | PerformanceContractOverlay
)

_LAYER_ORDER = {
    PerformanceContractLayer.industry_reference: 0,
    PerformanceContractLayer.organization: 1,
    PerformanceContractLayer.role: 2,
    PerformanceContractLayer.individual: 3,
}


class PerformanceContractResolver:
    """Register and resolve explicit Performance Contract specialization chains."""

    def __init__(self, contracts: Iterable[PerformanceContractDefinition] = ()) -> None:
        self._contracts: dict[str, PerformanceContractDefinition] = {}
        for contract in contracts:
            self.register(contract)

    def register(self, contract: PerformanceContractDefinition) -> None:
        if contract.id in self._contracts:
            raise PerformanceContractResolutionError(
                "CONTRACT_ALREADY_REGISTERED",
                f"Performance contract already registered: {contract.id}",
            )
        self._contracts[contract.id] = contract

    def resolve(self, contract_id: str) -> ResolvedPerformanceContract:
        chain = self._inheritance_chain(contract_id)
        self._validate_chain(chain)

        root = chain[0]
        if not isinstance(root, PerformanceContract):
            raise PerformanceContractResolutionError(
                "ROOT_MUST_BE_COMPLETE",
                f"Performance specialization root must be a complete contract: {root.id}",
            )

        subjects = {item.id: item for item in root.subjects}
        nodes = {item.id: item for item in root.nodes}
        accountabilities = {_accountability_key(item): item for item in root.accountabilities}
        contributions = {_contribution_key(item): item for item in root.contributions}
        response_bindings = {item.id: item for item in root.response_bindings}

        lineage: dict[tuple[str, str], PerformanceResolutionLineage] = {}
        self._record_contract_lineage(root, lineage)
        operations: list[PerformanceResolutionOperation] = []

        for child in chain[1:]:
            if isinstance(child, PerformanceContractOverlayV2):
                for suppression in child.suppressions:
                    self._apply_suppression(
                        child,
                        suppression,
                        subjects,
                        nodes,
                        accountabilities,
                        contributions,
                        response_bindings,
                        lineage,
                        operations,
                    )
                for patch in child.patches:
                    self._apply_patch(
                        child,
                        patch,
                        subjects,
                        nodes,
                        contributions,
                        response_bindings,
                        lineage,
                        operations,
                    )

            for subject in child.subjects:
                inherited_subject = subjects.get(subject.id)
                if inherited_subject is not None and inherited_subject.kind != subject.kind:
                    raise PerformanceContractResolutionError(
                        "SUBJECT_KIND_MUTATION",
                        f"Subject {subject.id} changes kind from "
                        f"{inherited_subject.kind.value} to {subject.kind.value}",
                    )
                operation = "override" if inherited_subject is not None else "add"
                subjects[subject.id] = subject
                self._record_lineage(lineage, "subject", subject.id, child)
                self._record_operation(operations, operation, "subject", subject.id, child)

            for node in child.nodes:
                inherited_node = nodes.get(node.id)
                if inherited_node is not None and inherited_node.kind != node.kind:
                    raise PerformanceContractResolutionError(
                        "NODE_KIND_MUTATION",
                        f"Performance node {node.id} changes kind from "
                        f"{inherited_node.kind.value} to {node.kind.value}",
                    )
                operation = "override" if inherited_node is not None else "add"
                nodes[node.id] = node
                self._record_lineage(lineage, "node", node.id, child)
                self._record_operation(operations, operation, "node", node.id, child)

            for assignment in child.accountabilities:
                key = _accountability_key(assignment)
                operation = "override" if key in accountabilities else "add"
                accountabilities[key] = assignment
                rendered = _render_key(key)
                self._record_lineage(lineage, "accountability", rendered, child)
                self._record_operation(
                    operations, operation, "accountability", rendered, child
                )

            for edge in child.contributions:
                key = _contribution_key(edge)
                operation = "override" if key in contributions else "add"
                contributions[key] = edge
                rendered = _render_key(key)
                self._record_lineage(lineage, "contribution", rendered, child)
                self._record_operation(
                    operations, operation, "contribution", rendered, child
                )

            for binding in child.response_bindings:
                operation = "override" if binding.id in response_bindings else "add"
                response_bindings[binding.id] = binding
                self._record_lineage(lineage, "response_binding", binding.id, child)
                self._record_operation(
                    operations,
                    operation,
                    "response_binding",
                    binding.id,
                    child,
                )

        leaf = chain[-1]
        organization_id = self._effective_organization_id(chain)
        effective_from, effective_to = self._effective_window(chain)

        try:
            resolved = PerformanceContract(
                id=leaf.id,
                version=leaf.version,
                name=leaf.name,
                layer=leaf.layer,
                organization_id=organization_id,
                effective_from=effective_from,
                effective_to=effective_to,
                subjects=tuple(subjects[key] for key in sorted(subjects)),
                nodes=tuple(nodes[key] for key in sorted(nodes)),
                accountabilities=tuple(accountabilities[key] for key in sorted(accountabilities)),
                contributions=tuple(contributions[key] for key in sorted(contributions)),
                response_bindings=tuple(
                    response_bindings[key] for key in sorted(response_bindings)
                ),
            )
        except ValueError as exc:
            raise PerformanceContractResolutionError(
                "INVALID_RESOLVED_CONTRACT",
                f"Resolved performance contract {leaf.id} is invalid: {exc}",
            ) from exc

        return ResolvedPerformanceContract(
            contract=resolved,
            source_contract_ids=tuple(item.id for item in chain),
            lineage=tuple(
                lineage[key] for key in sorted(lineage, key=lambda item: (item[0], item[1]))
            ),
            operations=tuple(operations),
        )

    def _apply_suppression(
        self,
        source: PerformanceContractOverlayV2,
        suppression: PerformanceElementSuppression,
        subjects: dict[str, PerformanceSubject],
        nodes: dict[str, PerformanceNode],
        accountabilities: dict[tuple[str, str, str], PerformanceAccountability],
        contributions: dict[tuple[str, str, str], PerformanceContribution],
        response_bindings: dict[str, PerformanceResponseBinding],
        lineage: dict[tuple[str, str], PerformanceResolutionLineage],
        operations: list[PerformanceResolutionOperation],
    ) -> None:
        element_type = suppression.element_type
        element_key = suppression.element_key

        removed = False
        if element_type == "subject":
            removed = subjects.pop(element_key, None) is not None
        elif element_type == "node":
            removed = nodes.pop(element_key, None) is not None
        elif element_type == "response_binding":
            removed = response_bindings.pop(element_key, None) is not None
        elif element_type == "accountability":
            key = _find_rendered_key(accountabilities, element_key)
            if key is not None:
                del accountabilities[key]
                removed = True
        else:
            key = _find_rendered_key(contributions, element_key)
            if key is not None:
                del contributions[key]
                removed = True

        if not removed:
            raise PerformanceContractResolutionError(
                "SUPPRESSION_TARGET_NOT_FOUND",
                f"Performance suppression target is not inherited: "
                f"{element_type}:{element_key}",
            )

        lineage.pop((element_type, element_key), None)
        self._record_operation(
            operations,
            "suppress",
            element_type,
            element_key,
            source,
            reason=suppression.reason,
        )

    def _apply_patch(
        self,
        source: PerformanceContractOverlayV2,
        patch: PerformanceElementPatch,
        subjects: dict[str, PerformanceSubject],
        nodes: dict[str, PerformanceNode],
        contributions: dict[tuple[str, str, str], PerformanceContribution],
        response_bindings: dict[str, PerformanceResponseBinding],
        lineage: dict[tuple[str, str], PerformanceResolutionLineage],
        operations: list[PerformanceResolutionOperation],
    ) -> None:
        element_type = patch.element_type
        element_key = patch.element_key

        if element_type == "subject":
            current: BaseModel | None = subjects.get(element_key)
            model_type: type[BaseModel] = PerformanceSubject
        elif element_type == "node":
            current = nodes.get(element_key)
            model_type = PerformanceNode
        elif element_type == "response_binding":
            current = response_bindings.get(element_key)
            model_type = PerformanceResponseBinding
        else:
            key = _find_rendered_key(contributions, element_key)
            current = contributions.get(key) if key is not None else None
            model_type = PerformanceContribution

        if current is None:
            raise PerformanceContractResolutionError(
                "PATCH_TARGET_NOT_FOUND",
                f"Performance patch target is not inherited: "
                f"{element_type}:{element_key}",
            )

        payload = current.model_dump(mode="python")
        for field_name in patch.clear_fields:
            payload[field_name] = _CLEAR_VALUES[(element_type, field_name)]
        for field_set in patch.set_fields:
            payload[field_set.field] = field_set.value

        try:
            patched = model_type.model_validate(payload)
        except ValueError as exc:
            raise PerformanceContractResolutionError(
                "INVALID_PATCH",
                f"Performance patch produced invalid {element_type} "
                f"{element_key}: {exc}",
            ) from exc

        if element_type == "subject":
            assert isinstance(patched, PerformanceSubject)
            subjects[element_key] = patched
        elif element_type == "node":
            assert isinstance(patched, PerformanceNode)
            nodes[element_key] = patched
        elif element_type == "response_binding":
            assert isinstance(patched, PerformanceResponseBinding)
            response_bindings[element_key] = patched
        else:
            assert isinstance(patched, PerformanceContribution)
            key = _find_rendered_key(contributions, element_key)
            assert key is not None
            contributions[key] = patched

        self._record_lineage(lineage, element_type, element_key, source)
        changed_fields = tuple(
            sorted({item.field for item in patch.set_fields} | set(patch.clear_fields))
        )
        self._record_operation(
            operations,
            "patch",
            element_type,
            element_key,
            source,
            changed_fields=changed_fields,
            reason=patch.reason,
        )

    def _inheritance_chain(self, contract_id: str) -> list[PerformanceContractDefinition]:
        chain: list[PerformanceContractDefinition] = []
        visiting: list[str] = []
        cursor = contract_id

        while True:
            if cursor in visiting:
                cycle = visiting[visiting.index(cursor) :] + [cursor]
                raise PerformanceContractResolutionError(
                    "INHERITANCE_CYCLE",
                    "Performance contract inheritance cycle: " + " -> ".join(cycle),
                )
            contract = self._contracts.get(cursor)
            if contract is None:
                raise PerformanceContractResolutionError(
                    "CONTRACT_NOT_FOUND",
                    f"Performance contract is not registered: {cursor}",
                )
            visiting.append(cursor)
            chain.append(contract)
            parent_id = contract.extends_contract_id
            if parent_id is None:
                break
            cursor = parent_id

        chain.reverse()
        return chain

    def _validate_chain(self, chain: list[PerformanceContractDefinition]) -> None:
        root = chain[0]
        if root.layer == PerformanceContractLayer.industry_reference and root.organization_id:
            raise PerformanceContractResolutionError(
                "INDUSTRY_REFERENCE_TENANT_BOUND",
                "Industry-reference performance contracts must be organization-neutral",
            )

        prior: PerformanceContractDefinition = root
        for child in chain[1:]:
            if _LAYER_ORDER[child.layer] <= _LAYER_ORDER[prior.layer]:
                raise PerformanceContractResolutionError(
                    "INVALID_LAYER_ORDER",
                    f"Performance layer must specialize toward the individual: "
                    f"{prior.layer.value} -> {child.layer.value}",
                )
            prior = child

        for item in chain:
            if item.layer == PerformanceContractLayer.organization and not item.organization_id:
                raise PerformanceContractResolutionError(
                    "ORGANIZATION_ID_REQUIRED",
                    f"Organization performance contract requires organization_id: {item.id}",
                )
        self._effective_organization_id(chain)
        self._effective_window(chain)

    def _effective_organization_id(self, chain: list[PerformanceContractDefinition]) -> str | None:
        organization_id: str | None = None
        for item in chain:
            if item.organization_id is None:
                continue
            if organization_id is None:
                organization_id = item.organization_id
                continue
            if item.organization_id != organization_id:
                raise PerformanceContractResolutionError(
                    "ORGANIZATION_BOUNDARY_VIOLATION",
                    f"Performance specialization crosses organization boundary: "
                    f"{organization_id} -> {item.organization_id}",
                )
        return organization_id

    def _effective_window(
        self, chain: list[PerformanceContractDefinition]
    ) -> tuple[datetime | None, datetime | None]:
        starts = [item.effective_from for item in chain if item.effective_from is not None]
        ends = [item.effective_to for item in chain if item.effective_to is not None]
        effective_from = max(starts) if starts else None
        effective_to = min(ends) if ends else None
        if effective_from and effective_to and effective_from >= effective_to:
            raise PerformanceContractResolutionError(
                "EMPTY_EFFECTIVE_WINDOW",
                "Performance specialization layers have no overlapping effective window",
            )
        return effective_from, effective_to

    def _record_contract_lineage(
        self,
        contract: PerformanceContractDefinition,
        lineage: dict[tuple[str, str], PerformanceResolutionLineage],
    ) -> None:
        for subject in contract.subjects:
            self._record_lineage(lineage, "subject", subject.id, contract)
        for node in contract.nodes:
            self._record_lineage(lineage, "node", node.id, contract)
        for assignment in contract.accountabilities:
            self._record_lineage(
                lineage,
                "accountability",
                _render_key(_accountability_key(assignment)),
                contract,
            )
        for edge in contract.contributions:
            self._record_lineage(
                lineage,
                "contribution",
                _render_key(_contribution_key(edge)),
                contract,
            )
        for binding in contract.response_bindings:
            self._record_lineage(lineage, "response_binding", binding.id, contract)

    @staticmethod
    def _record_lineage(
        lineage: dict[tuple[str, str], PerformanceResolutionLineage],
        element_type: Literal[
            "subject", "node", "accountability", "contribution", "response_binding"
        ],
        element_key: str,
        source: PerformanceContractDefinition,
    ) -> None:
        lineage[(element_type, element_key)] = PerformanceResolutionLineage(
            element_type=element_type,
            element_key=element_key,
            source_contract_id=source.id,
            source_contract_version=source.version,
            source_layer=source.layer,
        )

    @staticmethod
    def _record_operation(
        operations: list[PerformanceResolutionOperation],
        operation: Literal["add", "override", "patch", "suppress"],
        element_type: Literal[
            "subject", "node", "accountability", "contribution", "response_binding"
        ],
        element_key: str,
        source: PerformanceContractDefinition,
        *,
        changed_fields: tuple[str, ...] = (),
        reason: str | None = None,
    ) -> None:
        operations.append(
            PerformanceResolutionOperation(
                operation=operation,
                element_type=element_type,
                element_key=element_key,
                source_contract_id=source.id,
                source_contract_version=source.version,
                source_layer=source.layer,
                changed_fields=changed_fields,
                reason=reason,
            )
        )


def _accountability_key(item: PerformanceAccountability) -> tuple[str, str, str]:
    return (item.subject_id, item.node_id, item.relation.value)


def _contribution_key(item: PerformanceContribution) -> tuple[str, str, str]:
    return (item.source_node_id, item.target_node_id, item.relation.value)


def _render_key(key: tuple[str, str, str]) -> str:
    return "|".join(key)


def _find_rendered_key(
    items: dict[tuple[str, str, str], Any], rendered: str
) -> tuple[str, str, str] | None:
    for key in items:
        if _render_key(key) == rendered:
            return key
    return None
