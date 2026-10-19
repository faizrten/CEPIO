"""Enterprise performance contract primitives.

Performance Contracts model how an organization defines success without embedding
organization-specific formulas or targets into the CEPIO core ontology. They connect
strategy, OKRs, KPIs, metrics, accountabilities, contribution relationships, and
governed workflow response bindings.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


PERFORMANCE_CONTRACT_VERSION: Literal["0.1.0"] = "0.1.0"


class PerformanceNodeKind(str, Enum):
    objective = "objective"
    outcome = "outcome"
    key_result = "key_result"
    kpi = "kpi"
    metric = "metric"
    guardrail = "guardrail"


class PerformanceSubjectKind(str, Enum):
    enterprise = "enterprise"
    business_unit = "business_unit"
    function = "function"
    team = "team"
    role = "role"
    persona = "persona"
    individual = "individual"


class AccountabilityRelation(str, Enum):
    owns = "owns"
    accountable_for = "accountable_for"
    contributes_to = "contributes_to"
    influences = "influences"


class ContributionRelation(str, Enum):
    contributes_to = "contributes_to"
    depends_on = "depends_on"
    influences = "influences"
    constrains = "constrains"


class TargetOperator(str, Enum):
    gte = "gte"
    lte = "lte"
    eq = "eq"
    between = "between"


class PerformanceStatus(str, Enum):
    unknown = "unknown"
    not_evaluated = "not_evaluated"
    on_track = "on_track"
    watch = "watch"
    at_risk = "at_risk"
    off_track = "off_track"
    critical = "critical"


class PerformanceContractLayer(str, Enum):
    industry_reference = "industry_reference"
    organization = "organization"
    role = "role"
    individual = "individual"


class PerformanceTarget(BaseModel):
    """Numeric target/condition used by KPIs, KRs, metrics and guardrails."""

    model_config = ConfigDict(frozen=True)

    operator: TargetOperator
    value: float | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> "PerformanceTarget":
        if self.operator == TargetOperator.between:
            if self.lower_bound is None or self.upper_bound is None:
                raise ValueError("between target requires lower_bound and upper_bound")
            if self.lower_bound > self.upper_bound:
                raise ValueError("between target lower_bound must not exceed upper_bound")
            if self.value is not None:
                raise ValueError("between target must not set value")
        else:
            if self.value is None:
                raise ValueError(f"{self.operator.value} target requires value")
            if self.lower_bound is not None or self.upper_bound is not None:
                raise ValueError(f"{self.operator.value} target must not set bounds")
        return self


class PerformanceThreshold(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["watch", "off_track", "critical"]
    condition: PerformanceTarget
    reason: str | None = None


class PerformanceSubject(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    kind: PerformanceSubjectKind
    name: str
    parent_id: str | None = None


class PerformanceNode(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    kind: PerformanceNodeKind
    name: str
    description: str | None = None
    scope_subject_id: str
    unit: str | None = None
    definition: str | None = None
    formula_ref: str | None = None
    reference_node_id: str | None = None
    target: PerformanceTarget | None = None
    thresholds: tuple[PerformanceThreshold, ...] = ()
    max_observation_age_seconds: float | None = Field(default=None, ge=0)
    valid_from: datetime | None = None
    valid_to: datetime | None = None

    @model_validator(mode="after")
    def validate_validity(self) -> "PerformanceNode":
        if self.valid_from and self.valid_to and self.valid_from >= self.valid_to:
            raise ValueError("valid_from must be before valid_to")
        return self


class PerformanceAccountability(BaseModel):
    model_config = ConfigDict(frozen=True)

    subject_id: str
    node_id: str
    relation: AccountabilityRelation


class PerformanceContribution(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_node_id: str
    target_node_id: str
    relation: ContributionRelation
    weight: float | None = Field(default=None, ge=0, le=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    rationale: str | None = None

    @model_validator(mode="after")
    def validate_edge(self) -> "PerformanceContribution":
        if self.source_node_id == self.target_node_id:
            raise ValueError("performance contribution cannot be a self-edge")
        return self


class PerformanceResponseBinding(BaseModel):
    """Maps a performance deviation to a governed workflow candidate.

    The binding never grants execution authority. The workflow runtime and policy
    boundary remain responsible for authorization and any external side effect.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    node_id: str
    statuses: frozenset[Literal["watch", "at_risk", "off_track", "critical"]] = Field(min_length=1)
    workflow_definition_id: str
    rationale: str | None = None


class PerformanceContract(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal["0.1.0"] = PERFORMANCE_CONTRACT_VERSION
    id: str
    version: str
    name: str
    layer: PerformanceContractLayer
    organization_id: str | None = None
    extends_contract_id: str | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    subjects: tuple[PerformanceSubject, ...]
    nodes: tuple[PerformanceNode, ...]
    accountabilities: tuple[PerformanceAccountability, ...] = ()
    contributions: tuple[PerformanceContribution, ...] = ()
    response_bindings: tuple[PerformanceResponseBinding, ...] = ()

    @model_validator(mode="after")
    def validate_references(self) -> "PerformanceContract":
        if self.effective_from and self.effective_to and self.effective_from >= self.effective_to:
            raise ValueError("effective_from must be before effective_to")

        subject_ids = [subject.id for subject in self.subjects]
        node_ids = [node.id for node in self.nodes]
        binding_ids = [binding.id for binding in self.response_bindings]
        if len(subject_ids) != len(set(subject_ids)):
            raise ValueError("performance subject ids must be unique")
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("performance node ids must be unique")
        if len(binding_ids) != len(set(binding_ids)):
            raise ValueError("performance response binding ids must be unique")

        subjects = set(subject_ids)
        nodes = set(node_ids)

        for subject in self.subjects:
            if subject.parent_id is not None and subject.parent_id not in subjects:
                raise ValueError(f"unknown parent subject: {subject.parent_id}")
            if subject.parent_id == subject.id:
                raise ValueError("performance subject cannot parent itself")

        for node in self.nodes:
            if node.scope_subject_id not in subjects:
                raise ValueError(f"unknown node scope subject: {node.scope_subject_id}")

        for assignment in self.accountabilities:
            if assignment.subject_id not in subjects:
                raise ValueError(f"unknown accountability subject: {assignment.subject_id}")
            if assignment.node_id not in nodes:
                raise ValueError(f"unknown accountability node: {assignment.node_id}")

        for edge in self.contributions:
            if edge.source_node_id not in nodes:
                raise ValueError(f"unknown contribution source: {edge.source_node_id}")
            if edge.target_node_id not in nodes:
                raise ValueError(f"unknown contribution target: {edge.target_node_id}")

        for binding in self.response_bindings:
            if binding.node_id not in nodes:
                raise ValueError(f"unknown response binding node: {binding.node_id}")

        self._validate_subject_cycles()
        self._validate_structural_contribution_cycles()
        return self

    def _validate_subject_cycles(self) -> None:
        parents = {subject.id: subject.parent_id for subject in self.subjects}
        for subject_id in parents:
            seen: set[str] = set()
            cursor: str | None = subject_id
            while cursor is not None:
                if cursor in seen:
                    raise ValueError("performance subject hierarchy must be acyclic")
                seen.add(cursor)
                cursor = parents.get(cursor)

    def _validate_structural_contribution_cycles(self) -> None:
        graph: dict[str, set[str]] = {node.id: set() for node in self.nodes}
        for edge in self.contributions:
            if edge.relation != ContributionRelation.influences:
                graph[edge.source_node_id].add(edge.target_node_id)

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visiting:
                raise ValueError("structural performance contribution graph must be acyclic")
            if node_id in visited:
                return
            visiting.add(node_id)
            for target_id in graph[node_id]:
                visit(target_id)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in graph:
            visit(node_id)
