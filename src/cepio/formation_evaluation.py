"""Deterministic PET-02 Formation Evaluation Assurance runtime.

This module executes the first CEPIO Subsurface persona journey against a governed
benchmark or equivalent resolved data package. It does not calculate petrophysical
properties. It assembles evidence, compares interpretation revisions, exposes
assumptions/uncertainty/confidence, reconciles contradictory evidence and traces
current downstream dependency impact.

The implementation is intentionally deterministic so the semantic contract can be
validated in CI before an LLM-backed Operator is introduced. External technical
records remain referenced by source identity and version; bulk source payloads are
not copied into CEPIO.
"""

from __future__ import annotations

from collections import deque
from copy import deepcopy
from pathlib import Path
from typing import Any, Literal, Mapping

import yaml
from pydantic import BaseModel, Field


PET02Status = Literal[
    "ANSWERED",
    "INSUFFICIENT_CEPIO_EVIDENCE",
    "AUTHORITY_CONFLICT",
]


class Pet02Blocker(BaseModel):
    code: str
    message: str


class Pet02SkillTrace(BaseModel):
    skill_id: str
    status: Literal["PASS", "BLOCKED"]
    outputs: list[str] = Field(default_factory=list)
    message: str


class Pet02ValueChange(BaseModel):
    name: str
    previous: Any
    current: Any


class Pet02SourceReference(BaseModel):
    source_system: str
    source_service: str
    record_kind: str
    record_id: str
    record_version: str
    partition: str | None = None


class Pet02EvidenceSummary(BaseModel):
    id: str
    role: Literal["supporting", "contradictory"]
    description: str
    source_ref: Pet02SourceReference
    observed_values: dict[str, Any] = Field(default_factory=dict)
    comparison_target: str | None = None


class Pet02UncertaintySummary(BaseModel):
    id: str
    assesses: str
    uncertainty_type: str
    representation: str
    material_drivers: list[str] = Field(default_factory=list)
    assessment: dict[str, Any] = Field(default_factory=dict)


class Pet02ConfidenceSummary(BaseModel):
    id: str
    rating: str
    rationale: str


class Pet02DependencyImpact(BaseModel):
    id: str
    kind: str
    depends_on: list[str]


class Pet02RecommendedAction(BaseModel):
    action_type: Literal["technical_review", "information_gain"]
    recommendation: str
    authority: Literal["recommend_only"] = "recommend_only"


class Pet02FormationEvaluationAnswer(BaseModel):
    well: str
    interval: str
    benchmark_id: str | None = None
    benchmark_synthetic: bool = False
    benchmark_origin: str | None = None
    authoritative_case: str
    authority_state: str
    superseded_case: str | None = None
    changed_assumptions: list[Pet02ValueChange]
    changed_findings: list[Pet02ValueChange]
    active_assumptions: dict[str, Any]
    current_findings: dict[str, Any]
    supporting_evidence: list[Pet02EvidenceSummary]
    contradictory_evidence: list[Pet02EvidenceSummary]
    uncertainty: list[Pet02UncertaintySummary]
    confidence: list[Pet02ConfidenceSummary]
    downstream_impact: list[Pet02DependencyImpact]
    recommended_actions: list[Pet02RecommendedAction]
    human_authority_required: bool = True
    prohibited_ai_conclusions: list[str] = Field(
        default_factory=lambda: [
            "declare_authoritative",
            "approve_reserves_basis",
            "overwrite_external_record",
            "approve_investment_decision",
        ]
    )


class Pet02ExecutionResult(BaseModel):
    status: PET02Status
    question: str
    answer: Pet02FormationEvaluationAnswer | None = None
    trace: list[Pet02SkillTrace] = Field(default_factory=list)
    blockers: list[Pet02Blocker] = Field(default_factory=list)


class FormationEvaluationAssuranceRuntime:
    """Execute PET-02 against a resolved benchmark/data package.

    The input mapping is deliberately close to the public benchmark contract. A
    production adapter can resolve the same logical package from OSDU/ADME and
    customer-specific interpretation repositories without changing the reasoning
    stages below.
    """

    CONTEXT_SKILL = "cepio.skill.subsurface.petrophysics.formation-evaluation-context"
    DELTA_SKILL = "cepio.skill.subsurface.petrophysics.interpretation-delta"
    ASSUMPTION_SKILL = "cepio.skill.subsurface.petrophysics.assumption-trace"
    RECONCILIATION_SKILL = "cepio.skill.subsurface.petrophysics.core-log-reconciliation"
    IMPACT_SKILL = "cepio.skill.subsurface.petrophysics.downstream-impact"

    def __init__(self, data: Mapping[str, Any]) -> None:
        self.data: dict[str, Any] = deepcopy(dict(data))

    @classmethod
    def from_yaml(cls, path: str | Path) -> "FormationEvaluationAssuranceRuntime":
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("PET-02 input must be a YAML mapping")
        return cls(payload)

    def execute(self, *, well: str, interval: str) -> Pet02ExecutionResult:
        question = (
            f"Show me the authoritative formation evaluation for Well {well}, {interval}. "
            "Explain why it changed, what evidence supports or contradicts it, what "
            "remains uncertain, and which current models, reserves cases, opportunities "
            "or decisions would be affected if the interpretation is wrong."
        )
        trace: list[Pet02SkillTrace] = []
        blockers: list[Pet02Blocker] = []

        if self.data.get("well") != well or self.data.get("interval") != interval:
            blockers.append(
                Pet02Blocker(
                    code="CONTEXT_NOT_FOUND",
                    message=f"No resolved PET-02 context for Well {well}, interval {interval}.",
                )
            )
            trace.append(
                Pet02SkillTrace(
                    skill_id=self.CONTEXT_SKILL,
                    status="BLOCKED",
                    message="Requested well/interval does not match the resolved evidence package.",
                )
            )
            return Pet02ExecutionResult(
                status="INSUFFICIENT_CEPIO_EVIDENCE",
                question=question,
                trace=trace,
                blockers=blockers,
            )

        cases = self._cases_by_id()
        authoritative = [
            case
            for case in cases.values()
            if self._state_name(case.get("state")) == "Authoritative"
        ]
        if not authoritative:
            blockers.append(
                Pet02Blocker(
                    code="AUTHORITATIVE_CASE_NOT_FOUND",
                    message="No formation-evaluation case is marked Authoritative.",
                )
            )
            trace.append(
                Pet02SkillTrace(
                    skill_id=self.CONTEXT_SKILL,
                    status="BLOCKED",
                    message="The authority state cannot be resolved.",
                )
            )
            return Pet02ExecutionResult(
                status="INSUFFICIENT_CEPIO_EVIDENCE",
                question=question,
                trace=trace,
                blockers=blockers,
            )
        if len(authoritative) > 1:
            blockers.append(
                Pet02Blocker(
                    code="MULTIPLE_AUTHORITATIVE_CASES",
                    message="More than one formation-evaluation case is marked Authoritative.",
                )
            )
            trace.append(
                Pet02SkillTrace(
                    skill_id=self.CONTEXT_SKILL,
                    status="BLOCKED",
                    message="Authority conflict prevents a deterministic answer.",
                )
            )
            return Pet02ExecutionResult(
                status="AUTHORITY_CONFLICT",
                question=question,
                trace=trace,
                blockers=blockers,
            )

        current = authoritative[0]
        current_id = str(current.get("id"))
        previous_id = current.get("supersedes")
        previous = cases.get(previous_id) if previous_id else None
        if previous_id and previous is None:
            blockers.append(
                Pet02Blocker(
                    code="SUPERSEDED_CASE_NOT_FOUND",
                    message=f"Authoritative case references missing predecessor {previous_id}.",
                )
            )
            trace.append(
                Pet02SkillTrace(
                    skill_id=self.CONTEXT_SKILL,
                    status="BLOCKED",
                    message="Interpretation lineage is incomplete.",
                )
            )
            return Pet02ExecutionResult(
                status="INSUFFICIENT_CEPIO_EVIDENCE",
                question=question,
                trace=trace,
                blockers=blockers,
            )

        evidence, evidence_blockers = self._validated_evidence()
        if evidence_blockers:
            blockers.extend(evidence_blockers)
            trace.append(
                Pet02SkillTrace(
                    skill_id=self.CONTEXT_SKILL,
                    status="BLOCKED",
                    message="External evidence identity/version provenance is incomplete.",
                )
            )
            return Pet02ExecutionResult(
                status="INSUFFICIENT_CEPIO_EVIDENCE",
                question=question,
                trace=trace,
                blockers=blockers,
            )

        trace.append(
            Pet02SkillTrace(
                skill_id=self.CONTEXT_SKILL,
                status="PASS",
                outputs=["authoritative_case", "authority_state", "evidence_inventory"],
                message=f"Resolved {current_id} as the single authoritative case with versioned evidence.",
            )
        )

        changed_assumptions = self._diff_maps(
            previous.get("assumptions", {}) if previous else {},
            current.get("assumptions", {}),
        )
        changed_findings = self._diff_maps(
            previous.get("findings", {}) if previous else {},
            current.get("findings", {}),
        )
        trace.append(
            Pet02SkillTrace(
                skill_id=self.DELTA_SKILL,
                status="PASS",
                outputs=["changed_assumptions", "changed_findings"],
                message=(
                    f"Computed {len(changed_assumptions)} assumption changes and "
                    f"{len(changed_findings)} finding changes from source revisions."
                ),
            )
        )

        active_assumptions = dict(current.get("assumptions", {}))
        uncertainty = self._uncertainty_summaries()
        trace.append(
            Pet02SkillTrace(
                skill_id=self.ASSUMPTION_SKILL,
                status="PASS",
                outputs=["active_assumptions", "uncertainty"],
                message="Resolved active interpretation assumptions and material uncertainty drivers.",
            )
        )

        supporting = [item for item in evidence if item.role == "supporting"]
        contradictory = [item for item in evidence if item.role == "contradictory"]
        confidence = self._confidence_summaries(current_id)
        trace.append(
            Pet02SkillTrace(
                skill_id=self.RECONCILIATION_SKILL,
                status="PASS",
                outputs=["supporting_evidence", "contradictory_evidence", "confidence"],
                message=(
                    f"Separated {len(supporting)} supporting and {len(contradictory)} "
                    "contradictory evidence records without overwriting source data."
                ),
            )
        )

        downstream = self._downstream_impact(current_id)
        trace.append(
            Pet02SkillTrace(
                skill_id=self.IMPACT_SKILL,
                status="PASS",
                outputs=["downstream_impact"],
                message=f"Traced {len(downstream)} transitive downstream dependents from {current_id}.",
            )
        )

        provenance = self.data.get("provenance") or {}
        answer = Pet02FormationEvaluationAnswer(
            well=well,
            interval=interval,
            benchmark_id=self.data.get("id"),
            benchmark_synthetic=bool(self.data.get("synthetic", False)),
            benchmark_origin=provenance.get("origin"),
            authoritative_case=current_id,
            authority_state=self._state_name(current.get("state")),
            superseded_case=str(previous_id) if previous_id else None,
            changed_assumptions=changed_assumptions,
            changed_findings=changed_findings,
            active_assumptions=active_assumptions,
            current_findings=dict(current.get("findings", {})),
            supporting_evidence=supporting,
            contradictory_evidence=contradictory,
            uncertainty=uncertainty,
            confidence=confidence,
            downstream_impact=downstream,
            recommended_actions=self._recommended_actions(contradictory, uncertainty),
        )
        return Pet02ExecutionResult(
            status="ANSWERED",
            question=question,
            answer=answer,
            trace=trace,
            blockers=[],
        )

    def _cases_by_id(self) -> dict[str, dict[str, Any]]:
        cases = self.data.get("formation_evaluation_cases") or []
        return {
            str(case["id"]): dict(case)
            for case in cases
            if isinstance(case, dict) and case.get("id")
        }

    @staticmethod
    def _state_name(value: Any) -> str:
        if value is None:
            return ""
        return str(value).rsplit("#", 1)[-1]

    @staticmethod
    def _diff_maps(previous: Mapping[str, Any], current: Mapping[str, Any]) -> list[Pet02ValueChange]:
        names = sorted(set(previous) | set(current))
        return [
            Pet02ValueChange(name=name, previous=previous.get(name), current=current.get(name))
            for name in names
            if previous.get(name) != current.get(name)
        ]

    def _validated_evidence(self) -> tuple[list[Pet02EvidenceSummary], list[Pet02Blocker]]:
        summaries: list[Pet02EvidenceSummary] = []
        blockers: list[Pet02Blocker] = []
        required_ref_fields = (
            "source_system",
            "source_service",
            "record_kind",
            "record_id",
            "record_version",
        )
        for raw in self.data.get("external_evidence") or []:
            if not isinstance(raw, dict) or not raw.get("id"):
                blockers.append(
                    Pet02Blocker(
                        code="EVIDENCE_ID_MISSING",
                        message="External evidence item is missing a stable evidence id.",
                    )
                )
                continue
            ref = raw.get("source_ref") or {}
            missing = [name for name in required_ref_fields if not ref.get(name)]
            if missing:
                blockers.append(
                    Pet02Blocker(
                        code="SOURCE_VERSION_IDENTITY_INCOMPLETE",
                        message=(
                            f"Evidence {raw['id']} is missing source reference field(s): "
                            + ", ".join(missing)
                        ),
                    )
                )
                continue
            observed = {
                key: value
                for key, value in raw.items()
                if key
                not in {
                    "id",
                    "role",
                    "description",
                    "source_ref",
                    "comparison_target",
                }
            }
            summaries.append(
                Pet02EvidenceSummary(
                    id=str(raw["id"]),
                    role=raw.get("role", "supporting"),
                    description=str(raw.get("description", "")),
                    source_ref=Pet02SourceReference(**ref),
                    observed_values=observed,
                    comparison_target=raw.get("comparison_target"),
                )
            )
        return summaries, blockers

    def _uncertainty_summaries(self) -> list[Pet02UncertaintySummary]:
        result: list[Pet02UncertaintySummary] = []
        reserved = {
            "id",
            "assesses",
            "uncertainty_type",
            "representation",
            "material_drivers",
        }
        for raw in self.data.get("uncertainty_assessments") or []:
            assessment = {key: value for key, value in raw.items() if key not in reserved}
            result.append(
                Pet02UncertaintySummary(
                    id=str(raw.get("id")),
                    assesses=str(raw.get("assesses")),
                    uncertainty_type=str(raw.get("uncertainty_type")),
                    representation=str(raw.get("representation")),
                    material_drivers=list(raw.get("material_drivers") or []),
                    assessment=assessment,
                )
            )
        return result

    def _confidence_summaries(self, current_id: str) -> list[Pet02ConfidenceSummary]:
        result: list[Pet02ConfidenceSummary] = []
        for raw in self.data.get("confidence_assessments") or []:
            if raw.get("assesses") != current_id:
                continue
            result.append(
                Pet02ConfidenceSummary(
                    id=str(raw.get("id")),
                    rating=str(raw.get("rating")),
                    rationale=str(raw.get("rationale", "")),
                )
            )
        return result

    def _downstream_impact(self, root_id: str) -> list[Pet02DependencyImpact]:
        raw_nodes = [
            node
            for node in self.data.get("downstream_dependencies") or []
            if isinstance(node, dict) and node.get("id")
        ]
        remaining = {str(node["id"]): node for node in raw_nodes}
        discovered: set[str] = {root_id}
        ordered: list[Pet02DependencyImpact] = []
        queue: deque[str] = deque([root_id])

        while queue:
            source = queue.popleft()
            for node_id, raw in list(remaining.items()):
                depends_on_raw = raw.get("depends_on") or []
                depends_on = (
                    [str(depends_on_raw)]
                    if isinstance(depends_on_raw, str)
                    else [str(item) for item in depends_on_raw]
                )
                if source not in depends_on:
                    continue
                ordered.append(
                    Pet02DependencyImpact(
                        id=node_id,
                        kind=str(raw.get("kind", "unknown")),
                        depends_on=depends_on,
                    )
                )
                discovered.add(node_id)
                queue.append(node_id)
                del remaining[node_id]
        return ordered

    @staticmethod
    def _recommended_actions(
        contradictory: list[Pet02EvidenceSummary],
        uncertainty: list[Pet02UncertaintySummary],
    ) -> list[Pet02RecommendedAction]:
        actions: list[Pet02RecommendedAction] = []
        if contradictory:
            ids = ", ".join(item.id for item in contradictory)
            actions.append(
                Pet02RecommendedAction(
                    action_type="technical_review",
                    recommendation=(
                        "Reconcile contradictory formation-evaluation evidence "
                        f"({ids}) before relying on the affected property interpretation "
                        "for a governed downstream decision."
                    ),
                )
            )
        if uncertainty:
            subjects = ", ".join(sorted({item.assesses for item in uncertainty}))
            actions.append(
                Pet02RecommendedAction(
                    action_type="information_gain",
                    recommendation=(
                        "Evaluate additional information acquisition or technical work to "
                        f"reduce decision-relevant uncertainty in: {subjects}."
                    ),
                )
            )
        return actions


def run_pet02_formation_evaluation(
    benchmark: str | Path | Mapping[str, Any],
    *,
    well: str,
    interval: str,
) -> Pet02ExecutionResult:
    """Convenience entry point for deterministic PET-02 execution."""

    runtime = (
        FormationEvaluationAssuranceRuntime.from_yaml(benchmark)
        if isinstance(benchmark, (str, Path))
        else FormationEvaluationAssuranceRuntime(benchmark)
    )
    return runtime.execute(well=well, interval=interval)
