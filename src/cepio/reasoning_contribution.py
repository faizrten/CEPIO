"""Reusable contract for domain-aware Industry IQ reasoning contributions.

Reasoning contributions enrich an already-governed decision context with evidence-backed
hypotheses, uncertainty, information-gain suggestions and recommend-only intervention
options. They do not own performance truth, persist Decisions, start workflows or execute
Actions.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import Enum
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .application_contract import EvidenceReference
from .model import ObjectRef, OntologyObject


class ReasoningContributionError(ValueError):
    """Fail-closed reasoning contribution composition error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ConfidenceBand(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class UncertaintyBand(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class ReasoningEvidence(BaseModel):
    """Small, explicit evidence projection used by one reasoning contribution."""

    model_config = ConfigDict(frozen=True)

    id: str
    reference: EvidenceReference
    summary: str = Field(min_length=1)


class ReasoningHypothesis(BaseModel):
    """Evidence-backed hypothesis; never promoted to causal truth by this contract."""

    model_config = ConfigDict(frozen=True)

    id: str
    statement: str = Field(min_length=1)
    confidence: ConfidenceBand | None = None
    supporting_evidence_ids: tuple[str, ...] = ()
    contradicting_evidence_ids: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    claim_status: Literal["hypothesis_only"] = "hypothesis_only"


class ReasoningUncertainty(BaseModel):
    """Explicit uncertainty that remains after the contribution has reasoned."""

    model_config = ConfigDict(frozen=True)

    id: str
    description: str = Field(min_length=1)
    level: UncertaintyBand
    related_hypothesis_ids: tuple[str, ...] = ()


class InformationGainCandidate(BaseModel):
    """A next check that could reduce material decision uncertainty."""

    model_config = ConfigDict(frozen=True)

    id: str
    question: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    evidence_needed: tuple[str, ...] = ()
    priority: Literal["low", "medium", "high"] = "medium"


class ReasoningInterventionOption(BaseModel):
    """Recommend-only intervention option with no execution authority."""

    model_config = ConfigDict(frozen=True)

    id: str
    title: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    constraints: tuple[str, ...] = ()
    authority: Literal["recommend_only"] = "recommend_only"
    policy_required: Literal[True] = True


class ReasoningContribution(BaseModel):
    """One bounded domain contribution to a broader Industry IQ assessment."""

    model_config = ConfigDict(frozen=True)

    contributor_id: str
    contributor_version: str
    domain: str
    subject: ObjectRef
    evidence: tuple[ReasoningEvidence, ...] = ()
    hypotheses: tuple[ReasoningHypothesis, ...] = ()
    uncertainties: tuple[ReasoningUncertainty, ...] = ()
    information_gain: tuple[InformationGainCandidate, ...] = ()
    intervention_options: tuple[ReasoningInterventionOption, ...] = ()
    messages: tuple[str, ...] = ()
    causal_claim_made: Literal[False] = False
    authority: Literal["recommend_only"] = "recommend_only"

    @model_validator(mode="after")
    def validate_internal_references(self) -> "ReasoningContribution":
        evidence_ids = [item.id for item in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("Reasoning evidence IDs must be unique within a contribution")

        hypothesis_ids = [item.id for item in self.hypotheses]
        if len(hypothesis_ids) != len(set(hypothesis_ids)):
            raise ValueError("Reasoning hypothesis IDs must be unique within a contribution")

        known_evidence = set(evidence_ids)
        for hypothesis in self.hypotheses:
            referenced = set(hypothesis.supporting_evidence_ids).union(
                hypothesis.contradicting_evidence_ids
            )
            missing = sorted(referenced.difference(known_evidence))
            if missing:
                raise ValueError(
                    f"Hypothesis {hypothesis.id!r} references unknown evidence IDs: {missing}"
                )

        known_hypotheses = set(hypothesis_ids)
        for uncertainty in self.uncertainties:
            missing = sorted(set(uncertainty.related_hypothesis_ids).difference(known_hypotheses))
            if missing:
                raise ValueError(
                    f"Uncertainty {uncertainty.id!r} references unknown hypothesis IDs: {missing}"
                )
        return self


class ReasoningContributionRequest(BaseModel):
    """Protocol-neutral context passed to each domain reasoning contributor."""

    model_config = ConfigDict(frozen=True)

    subject: ObjectRef
    problem: str = Field(min_length=1)
    performance_node_id: str
    performance_status: str
    performance_evidence_refs: tuple[str, ...] = ()
    context_object_refs: tuple[ObjectRef, ...] = ()


class ReasoningContributionHost(Protocol):
    """Restricted read-only host surface available to reasoning contributors."""

    def read_object(self, reference: ObjectRef) -> OntologyObject: ...


class ReasoningContributor(Protocol):
    """Domain extension that emits a bounded ReasoningContribution."""

    contributor_id: str
    version: str
    domain: str
    required_pack_id: str | None

    def contribute(
        self,
        request: ReasoningContributionRequest,
        host: ReasoningContributionHost,
    ) -> ReasoningContribution: ...


class BoundedReasoningHost:
    """Read-only host that exposes only objects pre-authorized by the caller boundary."""

    def __init__(self, objects: Iterable[OntologyObject]) -> None:
        self._objects: dict[str, OntologyObject] = {}
        for obj in objects:
            prior = self._objects.get(obj.id)
            if prior is not None and prior.type != obj.type:
                raise ReasoningContributionError(
                    "CONTEXT_IDENTITY_COLLISION",
                    f"Reasoning context object {obj.id!r} has conflicting types",
                )
            self._objects[obj.id] = obj

    def read_object(self, reference: ObjectRef) -> OntologyObject:
        try:
            obj = self._objects[reference.id]
        except KeyError as exc:
            raise ReasoningContributionError(
                "CONTEXT_OBJECT_NOT_AUTHORIZED",
                f"Reasoning contributor requested object outside its authorized context: {reference.id}",
            ) from exc
        if obj.type != reference.type:
            raise ReasoningContributionError(
                "CONTEXT_OBJECT_TYPE_MISMATCH",
                f"Reasoning context type {reference.type!r} does not match object type {obj.type!r}",
            )
        return obj


class ReasoningContributionEngine:
    """Deterministic composition engine for zero or more domain contributors."""

    def __init__(self, contributors: Iterable[ReasoningContributor] = ()) -> None:
        self._contributors: dict[str, ReasoningContributor] = {}
        for contributor in contributors:
            self.register(contributor)

    def register(self, contributor: ReasoningContributor) -> None:
        if contributor.contributor_id in self._contributors:
            raise ReasoningContributionError(
                "CONTRIBUTOR_ALREADY_REGISTERED",
                f"Reasoning contributor already registered: {contributor.contributor_id}",
            )
        self._contributors[contributor.contributor_id] = contributor

    def evaluate(
        self,
        request: ReasoningContributionRequest,
        host: ReasoningContributionHost,
        *,
        installed_packs: Mapping[str, str] | None = None,
    ) -> tuple[ReasoningContribution, ...]:
        installed = installed_packs or {}
        contributions: list[ReasoningContribution] = []
        for contributor_id in sorted(self._contributors):
            contributor = self._contributors[contributor_id]
            if (
                contributor.required_pack_id is not None
                and contributor.required_pack_id not in installed
            ):
                raise ReasoningContributionError(
                    "REASONING_PACK_NOT_INSTALLED",
                    f"Reasoning contributor {contributor_id} requires installed Industry IQ pack "
                    f"{contributor.required_pack_id}",
                )
            contribution = contributor.contribute(request, host)
            if contribution.contributor_id != contributor.contributor_id:
                raise ReasoningContributionError(
                    "CONTRIBUTOR_IDENTITY_MISMATCH",
                    f"Contributor {contributor_id} returned contribution identity "
                    f"{contribution.contributor_id}",
                )
            if contribution.contributor_version != contributor.version:
                raise ReasoningContributionError(
                    "CONTRIBUTOR_VERSION_MISMATCH",
                    f"Contributor {contributor_id} returned version "
                    f"{contribution.contributor_version}; expected {contributor.version}",
                )
            if contribution.domain != contributor.domain:
                raise ReasoningContributionError(
                    "CONTRIBUTOR_DOMAIN_MISMATCH",
                    f"Contributor {contributor_id} returned domain {contribution.domain!r}; "
                    f"expected {contributor.domain!r}",
                )
            if contribution.subject != request.subject:
                raise ReasoningContributionError(
                    "CONTRIBUTION_SUBJECT_MISMATCH",
                    f"Contributor {contributor_id} returned a different reasoning subject",
                )
            contributions.append(contribution)
        return tuple(contributions)
