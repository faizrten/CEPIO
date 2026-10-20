"""Deterministic specialization for CEPIO Performance Contracts.

A resolved :class:`PerformanceContract` is complete and directly evaluable. Sparse
specialization overlays are deliberately a separate type so a role or individual
layer can reference inherited subjects/nodes without being mistaken for standalone
enterprise truth.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

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


class PerformanceContractOverlay(BaseModel):
    """Sparse child contract that becomes valid only after parent resolution.

    Entries are additive by default. Reusing a subject, node, contribution, or
    response-binding identity is an explicit whole-entry override. Deletion and
    tombstone semantics are intentionally not part of v0.1 specialization.
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


class ResolvedPerformanceContract(BaseModel):
    """Complete effective contract plus deterministic specialization provenance."""

    model_config = ConfigDict(frozen=True)

    contract: PerformanceContract
    source_contract_ids: tuple[str, ...]
    lineage: tuple[PerformanceResolutionLineage, ...]

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


PerformanceContractDefinition = PerformanceContract | PerformanceContractOverlay

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

        for child in chain[1:]:
            for subject in child.subjects:
                inherited_subject = subjects.get(subject.id)
                if inherited_subject is not None and inherited_subject.kind != subject.kind:
                    raise PerformanceContractResolutionError(
                        "SUBJECT_KIND_MUTATION",
                        f"Subject {subject.id} changes kind from "
                        f"{inherited_subject.kind.value} to {subject.kind.value}",
                    )
                subjects[subject.id] = subject
                self._record_lineage(lineage, "subject", subject.id, child)

            for node in child.nodes:
                inherited_node = nodes.get(node.id)
                if inherited_node is not None and inherited_node.kind != node.kind:
                    raise PerformanceContractResolutionError(
                        "NODE_KIND_MUTATION",
                        f"Performance node {node.id} changes kind from "
                        f"{inherited_node.kind.value} to {node.kind.value}",
                    )
                nodes[node.id] = node
                self._record_lineage(lineage, "node", node.id, child)

            for assignment in child.accountabilities:
                key = _accountability_key(assignment)
                accountabilities[key] = assignment
                self._record_lineage(lineage, "accountability", _render_key(key), child)

            for edge in child.contributions:
                key = _contribution_key(edge)
                contributions[key] = edge
                self._record_lineage(lineage, "contribution", _render_key(key), child)

            for binding in child.response_bindings:
                response_bindings[binding.id] = binding
                self._record_lineage(lineage, "response_binding", binding.id, child)

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


def _accountability_key(item: PerformanceAccountability) -> tuple[str, str, str]:
    return (item.subject_id, item.node_id, item.relation.value)


def _contribution_key(item: PerformanceContribution) -> tuple[str, str, str]:
    return (item.source_node_id, item.target_node_id, item.relation.value)


def _render_key(key: tuple[str, str, str]) -> str:
    return "|".join(key)
