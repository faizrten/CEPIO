"""Host-local, read-only professional work projection; no operational authority.

The host authenticates and authorizes every load, including referenced sources.
This module is not an authentication provider or a public transport endpoint.
"""

from datetime import datetime
from typing import Literal, Protocol

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from .accc_host_admission import HostPrincipal


Stage = Literal["understand", "assess", "work", "learn"]


class Contract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class WorkContextRequest(Contract):
    work_id: str = Field(min_length=1)
    expected_revision: int = Field(ge=1)


class EvidenceReceipt(Contract):
    """Host-verified source version and applicability, never model assertions."""

    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    observed_at: AwareDatetime
    valid_until: AwareDatetime
    applicable: bool
    conflict: bool = False

    @model_validator(mode="after")
    def valid_interval(self) -> "EvidenceReceipt":
        if self.valid_until <= self.observed_at:
            raise ValueError("evidence validity interval must be positive")
        return self


class WorkQuestion(Contract):
    id: str = Field(min_length=1)
    stage: Stage
    text: str = Field(min_length=1)
    required_evidence_ids: frozenset[str] = Field(min_length=1)
    capability_admission: Literal["ready", "blocked", "unknown"] = "unknown"


class WorkSnapshot(Contract):
    """Trusted application projection, not a canonical object or memory ledger."""

    work_id: str = Field(min_length=1)
    revision: int = Field(ge=1)
    tenant_id: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    subject_refs: tuple[str, ...] = ()
    decision_refs: tuple[str, ...] = ()
    outcome_refs: tuple[str, ...] = ()
    questions: tuple[WorkQuestion, ...] = ()
    evidence: tuple[EvidenceReceipt, ...] = ()
    selected_evidence_ids: frozenset[str] = frozenset()

    @model_validator(mode="after")
    def unique_ids(self) -> "WorkSnapshot":
        for items in (self.questions, self.evidence):
            ids = [item.id for item in items]
            if len(ids) != len(set(ids)):
                raise ValueError("duplicate question or evidence ID")
        return self


class EvidenceGap(Contract):
    evidence_id: str
    source_version: str | None = None
    reason: str
    next_check: str


class QuestionReadiness(Contract):
    question_id: str
    stage: Stage
    text: str
    capability_admission: Literal["ready", "blocked", "unknown"]
    evidence_completeness: Literal["complete", "incomplete"]
    assistance_state: Literal["ready_for_assessment", "unresolved"]
    blockers: tuple[str, ...]
    evidence_gaps: tuple[EvidenceGap, ...] = ()
    evidence_refs: tuple[EvidenceReceipt, ...] = ()
    guidance: str = "Assessment not performed."


class WorkContextView(Contract):
    schema_version: Literal["0.1.0"] = "0.1.0"
    work_id: str
    revision: int
    objective: str
    subject_refs: tuple[str, ...]
    decision_refs: tuple[str, ...]
    outcome_refs: tuple[str, ...]
    evidence: tuple[EvidenceReceipt, ...]
    questions: tuple[QuestionReadiness, ...]
    read_only: Literal[True] = True
    job_readiness: Literal["not_assessed"] = "not_assessed"
    action_authority: Literal["not_granted"] = "not_granted"


class WorkContextHost(Protocol):
    def authenticated_principal(self) -> HostPrincipal: ...

    def load_authorized_snapshot(self, work_id: str, principal: HostPrincipal) -> WorkSnapshot:
        """Enforce current work AND all referenced source permissions, or deny.

        Re-resolve rights, evidence applicability, capability admission and bounded
        selection on every request. Never deserialize this from client arguments.
        """
        ...


def read_work_context(
    request: WorkContextRequest, host: WorkContextHost, *, at: datetime
) -> WorkContextView:
    """Project one authorized revision; READY never means safe or authorized work."""
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("evaluation time must be timezone aware")
    principal = host.authenticated_principal()
    if not isinstance(principal, HostPrincipal) or not (
        principal.actor_id and principal.tenant_id and principal.roles
    ):
        raise PermissionError("work context unavailable")
    snapshot = host.load_authorized_snapshot(request.work_id, principal)
    if snapshot.tenant_id != principal.tenant_id or snapshot.work_id != request.work_id:
        raise PermissionError("work context unavailable")
    if snapshot.revision != request.expected_revision:
        raise ValueError("work context revision changed; reload required")
    evidence = {item.id: item for item in snapshot.evidence}
    questions = []
    for question in snapshot.questions:
        blockers = []
        gaps = []

        def gap(evidence_id: str, version: str | None, reason: str, next_check: str) -> None:
            blockers.append(reason)
            gaps.append(
                EvidenceGap(
                    evidence_id=evidence_id,
                    source_version=version,
                    reason=reason,
                    next_check=next_check,
                )
            )

        for evidence_id in sorted(question.required_evidence_ids):
            item = evidence.get(evidence_id)
            if item is None:
                gap(
                    evidence_id,
                    None,
                    "MISSING_EVIDENCE",
                    "Obtain this required evidence through an authorized source.",
                )
                continue
            if not item.observed_at <= at < item.valid_until:
                gap(
                    evidence_id,
                    item.version,
                    "EVIDENCE_NOT_CURRENT",
                    "Obtain a current observation and verify its timestamp and validity window.",
                )
            if not item.applicable:
                gap(
                    evidence_id,
                    item.version,
                    "EVIDENCE_NOT_APPLICABLE",
                    "Verify that this source applies to the task, asset and operating conditions.",
                )
            if item.conflict:
                gap(
                    evidence_id,
                    item.version,
                    "EVIDENCE_CONFLICT",
                    "Reconcile conflicting sources with the responsible technical authority.",
                )
            if evidence_id not in snapshot.selected_evidence_ids:
                gap(
                    evidence_id,
                    item.version,
                    "REQUIRED_EVIDENCE_NOT_SELECTED",
                    "Restore required evidence to the authorized working context before assessment.",
                )
        complete = not blockers
        if question.capability_admission != "ready":
            blockers.append("CAPABILITY_NOT_READY")
        questions.append(
            QuestionReadiness(
                question_id=question.id,
                stage=question.stage,
                text=question.text,
                capability_admission=question.capability_admission,
                evidence_completeness="complete" if complete else "incomplete",
                assistance_state="unresolved" if blockers else "ready_for_assessment",
                blockers=tuple(sorted(set(blockers))),
                evidence_gaps=tuple(gaps),
                evidence_refs=tuple(
                    evidence[key]
                    for key in sorted(question.required_evidence_ids)
                    if key in evidence
                ),
                guidance=(
                    "Resolve the listed evidence gaps before assessing this question."
                    if not complete
                    else "Evidence checks passed, but an admitted capability is still needed."
                    if question.capability_admission != "ready"
                    else "Declared evidence checks passed. Use the admitted capability to assess "
                    "the question; no technical conclusion or work permission is established."
                ),
            )
        )
    return WorkContextView(
        work_id=snapshot.work_id,
        revision=snapshot.revision,
        objective=snapshot.objective,
        subject_refs=snapshot.subject_refs,
        decision_refs=snapshot.decision_refs,
        outcome_refs=snapshot.outcome_refs,
        evidence=snapshot.evidence,
        questions=tuple(questions),
    )
