"""Deterministic Reliability contribution for the generic Industry IQ reasoning contract."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .application_contract import EvidenceReference, EvidenceRole
from .industry_iq import IndustryIQPackManifest
from .model import ObjectRef
from .performance_industry_iq import PERFORMANCE_RESPONSE_IQ_PACK_ID
from .reasoning_contribution import (
    ConfidenceBand,
    InformationGainCandidate,
    ReasoningContribution,
    ReasoningContributionHost,
    ReasoningContributionRequest,
    ReasoningEvidence,
    ReasoningHypothesis,
    ReasoningInterventionOption,
    ReasoningUncertainty,
    UncertaintyBand,
)
from .runtime import CEPIORuntime


RELIABILITY_REASONING_IQ_PACK_ID = "cepio.iq.reliability.reasoning"
RELIABILITY_REASONING_CONTRIBUTOR_ID = "cepio.reasoning.reliability"


class ReliabilityReasoningIndustryIQPack:
    """Capability declaration for Reliability reasoning contribution v0.1."""

    manifest = IndustryIQPackManifest(
        pack_id=RELIABILITY_REASONING_IQ_PACK_ID,
        version="0.1.0",
        requires_core=">=0.4.0,<1.0.0",
        requires_packs={PERFORMANCE_RESPONSE_IQ_PACK_ID: ">=0.1.0,<0.2.0"},
    )
    pack_id = manifest.pack_id
    version = manifest.version

    def install(self, runtime: CEPIORuntime) -> None:
        # This pack contributes reasoning only. It intentionally registers no Function,
        # Decision or Action capability and therefore cannot expand execution authority.
        del runtime


class ReliabilityReasoningContributor:
    """Evidence-bounded Reliability hypotheses for a Performance deviation.

    v0.1 intentionally uses only a small allow-list of properties on explicitly supplied,
    already-authorized CEPIO context objects. It never traverses the graph, invokes a
    function, persists a Decision, starts a workflow or executes an Action.
    """

    contributor_id = RELIABILITY_REASONING_CONTRIBUTOR_ID
    version = "0.1.0"
    domain = "reliability"
    required_pack_id = RELIABILITY_REASONING_IQ_PACK_ID

    _CONDITION_TYPES = {"ConditionObservation", "ConditionSignal"}
    _FAILURE_TYPES = {"FailureEvent"}
    _WORK_TYPES = {"WorkOrder"}

    def contribute(
        self,
        request: ReasoningContributionRequest,
        host: ReasoningContributionHost,
    ) -> ReasoningContribution:
        evidence: list[ReasoningEvidence] = []
        abnormal_condition_ids: list[str] = []
        normal_condition_ids: list[str] = []
        failure_ids: list[str] = []
        failure_modes: list[str] = []
        repeated_failure_ids: list[str] = []
        reopened_work_ids: list[str] = []
        verified_work_ids: list[str] = []

        for reference in request.context_object_refs:
            obj = host.read_object(reference)
            if obj.type in self._CONDITION_TYPES:
                item, abnormal, normal = self._condition_evidence(
                    obj.id, obj.type, obj.name, obj.properties
                )
                evidence.append(item)
                if abnormal:
                    abnormal_condition_ids.append(item.id)
                if normal:
                    normal_condition_ids.append(item.id)
            elif obj.type in self._FAILURE_TYPES:
                item, mode, repeated = self._failure_evidence(
                    obj.id, obj.type, obj.name, obj.properties
                )
                evidence.append(item)
                failure_ids.append(item.id)
                if mode is not None:
                    failure_modes.append(mode)
                if repeated:
                    repeated_failure_ids.append(item.id)
            elif obj.type in self._WORK_TYPES:
                item, reopened, verified = self._work_evidence(
                    obj.id, obj.type, obj.name, obj.properties
                )
                evidence.append(item)
                if reopened:
                    reopened_work_ids.append(item.id)
                if verified:
                    verified_work_ids.append(item.id)

        hypotheses: list[ReasoningHypothesis] = []
        uncertainties: list[ReasoningUncertainty] = []
        information_gain: list[InformationGainCandidate] = []
        interventions: list[ReasoningInterventionOption] = []

        if abnormal_condition_ids:
            confidence = self._confidence(len(abnormal_condition_ids), len(normal_condition_ids))
            hypothesis_id = "reliability.condition-degradation"
            hypotheses.append(
                ReasoningHypothesis(
                    id=hypothesis_id,
                    statement=(
                        "Observed equipment-condition degradation may be contributing to the "
                        "performance deviation."
                    ),
                    confidence=confidence,
                    supporting_evidence_ids=tuple(abnormal_condition_ids),
                    contradicting_evidence_ids=tuple(normal_condition_ids),
                    assumptions=(
                        "Condition observations are temporally relevant to the evaluated deviation.",
                    ),
                )
            )
            uncertainties.append(
                ReasoningUncertainty(
                    id="reliability.condition-mechanism-uncertainty",
                    description=(
                        "The condition evidence indicates degradation but does not establish the "
                        "physical failure mechanism or causal impact on the KPI."
                    ),
                    level=UncertaintyBand.medium,
                    related_hypothesis_ids=(hypothesis_id,),
                )
            )
            information_gain.append(
                InformationGainCandidate(
                    id="reliability.verify-condition-trend",
                    question=(
                        "Does an independent inspection or corroborating condition channel confirm "
                        "the degrading trend?"
                    ),
                    rationale=(
                        "Independent confirmation reduces the risk of acting on one noisy or stale "
                        "condition signal."
                    ),
                    evidence_needed=(
                        "independent condition measurement",
                        "inspection evidence",
                    ),
                    priority="high",
                )
            )
            interventions.append(
                ReasoningInterventionOption(
                    id="reliability.inspect-condition",
                    title="Inspect the affected equipment condition",
                    rationale=(
                        "Validate the observed degradation before selecting a corrective intervention."
                    ),
                    constraints=("Follow site integrity and maintenance policy",),
                )
            )

        mode_counts = Counter(failure_modes)
        repeated_modes = {mode for mode, count in mode_counts.items() if count >= 2}
        recurrence_support = [
            evidence_id for evidence_id in failure_ids if evidence_id in repeated_failure_ids
        ]
        if repeated_modes:
            recurrence_support = list(dict.fromkeys([*recurrence_support, *failure_ids]))
        elif len(failure_ids) >= 2:
            recurrence_support = list(dict.fromkeys([*recurrence_support, *failure_ids]))

        if recurrence_support:
            hypothesis_id = "reliability.recurring-failure-mechanism"
            hypotheses.append(
                ReasoningHypothesis(
                    id=hypothesis_id,
                    statement=(
                        "A recurring or unresolved failure mechanism may be contributing to the "
                        "performance deviation."
                    ),
                    confidence=(
                        ConfidenceBand.high
                        if len(recurrence_support) >= 3
                        else ConfidenceBand.medium
                    ),
                    supporting_evidence_ids=tuple(recurrence_support),
                    assumptions=(
                        "The failure records refer to the same operational subject or directly relevant equipment context.",
                    ),
                )
            )
            uncertainties.append(
                ReasoningUncertainty(
                    id="reliability.failure-mechanism-uncertainty",
                    description=(
                        "Repeated failure evidence does not by itself prove a common physical root cause."
                    ),
                    level=UncertaintyBand.medium,
                    related_hypothesis_ids=(hypothesis_id,),
                )
            )
            information_gain.append(
                InformationGainCandidate(
                    id="reliability.compare-repeat-failures",
                    question=(
                        "Do the repeated failures share a component, failure mode, operating regime or "
                        "post-maintenance recurrence pattern?"
                    ),
                    rationale=(
                        "A structured recurrence comparison can discriminate a shared mechanism from "
                        "unrelated events."
                    ),
                    evidence_needed=(
                        "failure-mode history",
                        "component history",
                        "operating-state history",
                        "post-maintenance recurrence evidence",
                    ),
                    priority="high",
                )
            )
            interventions.append(
                ReasoningInterventionOption(
                    id="reliability.review-repeat-failure-history",
                    title="Run a repeat-failure review",
                    rationale=(
                        "Compare failure and intervention history before escalating to a physical root-cause claim."
                    ),
                )
            )

        if reopened_work_ids:
            hypothesis_id = "reliability.corrective-action-effectiveness"
            hypotheses.append(
                ReasoningHypothesis(
                    id=hypothesis_id,
                    statement=(
                        "Previous corrective work may not have fully resolved the underlying reliability issue."
                    ),
                    confidence=(
                        ConfidenceBand.medium if not verified_work_ids else ConfidenceBand.low
                    ),
                    supporting_evidence_ids=tuple(reopened_work_ids),
                    contradicting_evidence_ids=tuple(verified_work_ids),
                    assumptions=(
                        "Reopened or repeated work is materially related to the current deviation.",
                    ),
                )
            )
            uncertainties.append(
                ReasoningUncertainty(
                    id="reliability.corrective-effectiveness-uncertainty",
                    description=(
                        "Reopened work can indicate ineffective correction, but can also reflect scope, "
                        "planning or unrelated follow-up activity."
                    ),
                    level=UncertaintyBand.high if verified_work_ids else UncertaintyBand.medium,
                    related_hypothesis_ids=(hypothesis_id,),
                )
            )
            information_gain.append(
                InformationGainCandidate(
                    id="reliability.verify-corrective-effectiveness",
                    question=(
                        "What completion evidence and post-maintenance verification show that the prior "
                        "corrective work addressed the observed mechanism?"
                    ),
                    rationale=(
                        "Verification separates recurrence after an effective repair from incomplete or "
                        "misdirected corrective work."
                    ),
                    evidence_needed=(
                        "work-order completion evidence",
                        "post-maintenance verification",
                    ),
                    priority="medium",
                )
            )
            interventions.append(
                ReasoningInterventionOption(
                    id="reliability.review-corrective-effectiveness",
                    title="Review corrective-work effectiveness",
                    rationale=(
                        "Confirm the prior work scope and post-maintenance evidence before changing the intervention strategy."
                    ),
                )
            )

        messages: list[str] = []
        if not hypotheses:
            messages.append(
                "Reliability context did not contain enough explicit evidence to form a supported hypothesis."
            )

        return ReasoningContribution(
            contributor_id=self.contributor_id,
            contributor_version=self.version,
            domain=self.domain,
            subject=request.subject,
            evidence=tuple(evidence),
            hypotheses=tuple(hypotheses),
            uncertainties=tuple(uncertainties),
            information_gain=tuple(information_gain),
            intervention_options=tuple(interventions),
            messages=tuple(messages),
        )

    @staticmethod
    def _string(value: Any) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @staticmethod
    def _normalized(value: Any) -> str:
        text = ReliabilityReasoningContributor._string(value)
        return "" if text is None else text.lower().replace("_", "-")

    @staticmethod
    def _safe_count(value: Any) -> int:
        if isinstance(value, bool):
            return 0
        if isinstance(value, int):
            return max(value, 0)
        if isinstance(value, float) and value.is_integer():
            return max(int(value), 0)
        return 0

    @staticmethod
    def _confidence(support_count: int, contradict_count: int) -> ConfidenceBand:
        if contradict_count:
            return ConfidenceBand.low
        if support_count >= 2:
            return ConfidenceBand.high
        return ConfidenceBand.medium

    @classmethod
    def _condition_evidence(
        cls,
        object_id: str,
        object_type: str,
        name: str,
        properties: dict[str, Any],
    ) -> tuple[ReasoningEvidence, bool, bool]:
        metric = cls._string(properties.get("metric")) or name
        status = cls._normalized(properties.get("status") or properties.get("condition"))
        trend = cls._normalized(properties.get("trend"))
        severity = cls._normalized(properties.get("severity"))
        value = properties.get("value")
        unit = cls._string(properties.get("unit"))

        abnormal = status in {"abnormal", "degraded", "poor", "critical", "alarm"}
        abnormal = abnormal or trend in {"worsening", "rising", "increasing", "degrading"}
        abnormal = abnormal or severity in {"high", "critical", "alarm"}
        normal = status in {"normal", "healthy", "good"} and not abnormal

        detail: list[str] = [f"metric={metric}"]
        if status:
            detail.append(f"status={status}")
        if trend:
            detail.append(f"trend={trend}")
        if severity:
            detail.append(f"severity={severity}")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            rendered = f"value={value:g}"
            if unit:
                rendered += f" {unit}"
            detail.append(rendered)

        evidence_id = f"reliability.condition:{object_id}"
        return (
            ReasoningEvidence(
                id=evidence_id,
                reference=EvidenceReference(
                    object_ref=ObjectRef(id=object_id, type=object_type),
                    role=EvidenceRole.supporting if abnormal else EvidenceRole.contextual,
                ),
                summary="Condition evidence: " + "; ".join(detail),
            ),
            abnormal,
            normal,
        )

    @classmethod
    def _failure_evidence(
        cls,
        object_id: str,
        object_type: str,
        name: str,
        properties: dict[str, Any],
    ) -> tuple[ReasoningEvidence, str | None, bool]:
        mode = cls._string(properties.get("failure_mode") or properties.get("failureMode"))
        repeated = bool(
            properties.get("repeat_failure") is True or properties.get("repeat") is True
        )
        detail = [f"event={name}"]
        if mode:
            detail.append(f"failure_mode={mode}")
        if repeated:
            detail.append("repeat_failure=true")
        evidence_id = f"reliability.failure:{object_id}"
        return (
            ReasoningEvidence(
                id=evidence_id,
                reference=EvidenceReference(
                    object_ref=ObjectRef(id=object_id, type=object_type),
                    role=EvidenceRole.supporting,
                ),
                summary="Failure evidence: " + "; ".join(detail),
            ),
            mode,
            repeated,
        )

    @classmethod
    def _work_evidence(
        cls,
        object_id: str,
        object_type: str,
        name: str,
        properties: dict[str, Any],
    ) -> tuple[ReasoningEvidence, bool, bool]:
        status = cls._normalized(properties.get("status"))
        reopen_count = cls._safe_count(
            properties.get("reopen_count", properties.get("reopenCount", 0))
        )
        verification = cls._normalized(
            properties.get("verification_status") or properties.get("verificationStatus")
        )
        reopened = reopen_count > 0 or status in {"reopened", "repeat", "repeat-work"}
        verified = verification in {"verified", "effective", "passed"} or status in {
            "closed-verified",
            "verified",
        }

        detail = [f"work_order={name}"]
        if status:
            detail.append(f"status={status}")
        if reopen_count:
            detail.append(f"reopen_count={reopen_count}")
        if verification:
            detail.append(f"verification={verification}")
        evidence_id = f"reliability.work:{object_id}"
        role = EvidenceRole.supporting if reopened else EvidenceRole.contextual
        if verified and reopened:
            role = EvidenceRole.contextual
        return (
            ReasoningEvidence(
                id=evidence_id,
                reference=EvidenceReference(
                    object_ref=ObjectRef(id=object_id, type=object_type),
                    role=role,
                ),
                summary="Work evidence: " + "; ".join(detail),
            ),
            reopened,
            verified,
        )


RELIABILITY_REASONING_IQ_PACK = ReliabilityReasoningIndustryIQPack()
