"""Fail-closed operational-assurance gates for advanced CEPIO qualification.

These gates are intentionally industry-neutral. Domain qualification suites provide the
fixtures; the gates enforce that predictions remain time-bounded inference, agent
recommendations cite enterprise evidence, operational-plan revisions have current
scoped authority, and outcome/value claims retain KPI, risk and provenance evidence.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from .model import OntologyObject
from .operational_assurance import EvidenceBundle

CORE_VALID_FROM = "https://cepio.org/ontology/core#validFrom"
CORE_VALID_TO = "https://cepio.org/ontology/core#validTo"
CORE_IMPACTS = "https://cepio.org/ontology/core#impacts"
AGENTIC_PREDICTION = "https://cepio.org/ontology/agentic#Prediction"
AGENTIC_SUPPORTED_BY_EVIDENCE = "https://cepio.org/ontology/agentic#supportedByEvidence"
KIN_REVISES_PLAN = "https://cepio.org/ontology/kinetic#revisesPlan"
KIN_AUTHORIZES_REVISION = "https://cepio.org/ontology/kinetic#authorizesRevision"
WF_AUTHORITY_FOR_ASSET = "https://cepio.org/ontology/workforce#authorityForAsset"
WF_AUTHORITY_HOLDER = "https://cepio.org/ontology/workforce#authorityHolder"
PERF_ASSESSMENT_OF_DECISION = "https://cepio.org/ontology/performance#assessmentOfDecision"
PERF_OBSERVED_OUTCOME = "https://cepio.org/ontology/performance#observedOutcome"
PERF_CONSIDERS_RISK = "https://cepio.org/ontology/performance#considersRisk"


class QualificationGateResult(BaseModel):
    status: Literal["PASS", "REJECTED"]
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == "PASS"


def _parse_time(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _is_current(obj: OntologyObject, at: datetime) -> bool:
    query_time = at if at.tzinfo is not None else at.replace(tzinfo=timezone.utc)
    valid_from = _parse_time(obj.properties.get(CORE_VALID_FROM))
    valid_to = _parse_time(obj.properties.get(CORE_VALID_TO))
    if valid_from is None or valid_to is None:
        return False
    return valid_from <= query_time < valid_to


def evaluate_prediction_freshness(
    prediction: OntologyObject,
    *,
    at: datetime,
) -> QualificationGateResult:
    """Reject a prediction as current enterprise context when its validity has expired."""

    if prediction.type != AGENTIC_PREDICTION:
        return QualificationGateResult(
            status="REJECTED",
            reason="object-is-not-a-governed-prediction",
            details={"object_id": prediction.id, "type": prediction.type},
        )
    if not _is_current(prediction, at):
        return QualificationGateResult(
            status="REJECTED",
            reason="prediction-is-stale-or-has-no-validity-window",
            details={
                "prediction_id": prediction.id,
                "valid_from": prediction.properties.get(CORE_VALID_FROM),
                "valid_to": prediction.properties.get(CORE_VALID_TO),
                "evaluated_at": at.isoformat(),
            },
        )
    return QualificationGateResult(
        status="PASS",
        reason="prediction-is-current-in-governed-validity-window",
        details={"prediction_id": prediction.id, "evaluated_at": at.isoformat()},
    )


def evaluate_recommendation_evidence(
    runtime: Any,
    recommendation_id: str,
) -> QualificationGateResult:
    """Require at least one CEPIO enterprise-evidence edge before surfacing a recommendation."""

    evidence = runtime.neighbors(recommendation_id, AGENTIC_SUPPORTED_BY_EVIDENCE)
    evidence_ids = sorted({item.id for item in evidence})
    if not evidence_ids:
        return QualificationGateResult(
            status="REJECTED",
            reason="recommendation-has-no-supporting-enterprise-evidence",
            details={"recommendation_id": recommendation_id},
        )
    return QualificationGateResult(
        status="PASS",
        reason="recommendation-is-grounded-in-cepio-evidence",
        evidence_ids=evidence_ids,
        details={"recommendation_id": recommendation_id},
    )


def evaluate_plan_revision_authority(
    runtime: Any,
    revision_id: str,
    *,
    actor_id: str,
    at: datetime,
) -> QualificationGateResult:
    """Require original plan, authorizing decision and current scoped human authority."""

    plans = runtime.neighbors(revision_id, KIN_REVISES_PLAN)
    decisions = runtime.reverse_neighbors(revision_id, KIN_AUTHORIZES_REVISION)
    assets = runtime.neighbors(revision_id, CORE_IMPACTS)
    if not plans:
        return QualificationGateResult(
            status="REJECTED", reason="plan-revision-has-no-original-plan"
        )
    if not decisions:
        return QualificationGateResult(
            status="REJECTED", reason="plan-revision-has-no-authorizing-decision"
        )
    if not assets:
        return QualificationGateResult(
            status="REJECTED", reason="plan-revision-has-no-operating-scope"
        )

    valid_assignments: list[str] = []
    for asset in assets:
        assignments = runtime.reverse_neighbors(asset.id, WF_AUTHORITY_FOR_ASSET)
        for assignment in assignments:
            if not _is_current(assignment, at):
                continue
            holders = runtime.neighbors(assignment.id, WF_AUTHORITY_HOLDER)
            if any(holder.id == actor_id for holder in holders):
                valid_assignments.append(assignment.id)

    if not valid_assignments:
        return QualificationGateResult(
            status="REJECTED",
            reason="actor-lacks-current-authority-for-plan-revision-scope",
            details={
                "revision_id": revision_id,
                "actor_id": actor_id,
                "asset_ids": sorted({asset.id for asset in assets}),
                "evaluated_at": at.isoformat(),
            },
        )

    return QualificationGateResult(
        status="PASS",
        reason="plan-revision-has-current-scoped-authority-and-authorizing-decision",
        evidence_ids=sorted({item.id for item in decisions}) + sorted(valid_assignments),
        details={
            "revision_id": revision_id,
            "actor_id": actor_id,
            "plan_ids": sorted({item.id for item in plans}),
            "asset_ids": sorted({item.id for item in assets}),
        },
    )


def evaluate_outcome_assessment(
    runtime: Any,
    assessment_id: str,
    *,
    evidence: EvidenceBundle,
) -> QualificationGateResult:
    """Reject value-realization claims unless decision, KPI, risk and provenance are evidenced."""

    decisions = runtime.neighbors(assessment_id, PERF_ASSESSMENT_OF_DECISION)
    outcomes = runtime.neighbors(assessment_id, PERF_OBSERVED_OUTCOME)
    risks = runtime.neighbors(assessment_id, PERF_CONSIDERS_RISK)
    if not decisions:
        return QualificationGateResult(
            status="REJECTED", reason="outcome-assessment-has-no-governed-decision"
        )
    if not outcomes:
        return QualificationGateResult(
            status="REJECTED", reason="outcome-assessment-has-no-kpi-evidence"
        )
    if not risks:
        return QualificationGateResult(
            status="REJECTED", reason="outcome-assessment-has-no-risk-context"
        )

    evidence_kinds = {record.kind for record in evidence.records}
    required_provenance = {"source_reference", "property_provenance", "transformation"}
    if not required_provenance.issubset(evidence_kinds):
        return QualificationGateResult(
            status="REJECTED",
            reason="outcome-assessment-lacks-provenance-chain",
            details={"present_evidence_kinds": sorted(evidence_kinds)},
        )

    serialized_evidence = json.dumps(
        [record.payload for record in evidence.records],
        sort_keys=True,
        default=str,
    )
    missing_ids = [item.id for item in [*outcomes, *risks] if item.id not in serialized_evidence]
    if missing_ids:
        return QualificationGateResult(
            status="REJECTED",
            reason="outcome-or-risk-not-present-in-provenance-evidence",
            details={"missing_ids": sorted(missing_ids)},
        )

    return QualificationGateResult(
        status="PASS",
        reason="outcome-assessment-is-evidence-backed-and-risk-aware",
        evidence_ids=sorted(evidence.evidence_ids),
        details={
            "assessment_id": assessment_id,
            "decision_ids": sorted({item.id for item in decisions}),
            "outcome_ids": sorted({item.id for item in outcomes}),
            "risk_ids": sorted({item.id for item in risks}),
        },
    )
