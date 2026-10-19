"""CEPIO Production Technologist v0.1 runtime.

This module executes the first Production Technology depth spine:

PROD-01 Daily Well Surveillance and Exception Triage
PROD-02 Well Deliverability and Nodal Model Assurance
PROD-06 Well Underperformance Diagnosis

The runtime is deterministic and source-system neutral. It does not calculate
nodal hydraulics, optimize live controls or execute well operations. It reasons
over referenced observations, external model outputs, governed limits,
competing hypotheses and uncertainty after CEPIO Skill preflight succeeds.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Literal, Mapping

import yaml
from pydantic import BaseModel, Field

from .bootstrap import build_runtime
from .runtime import CEPIORuntime
from .skill_preflight import (
    SkillGraphPathRequirement,
    SkillGraphPathStep,
    SkillPreflightResult,
    SkillPreflightSpec,
    SkillRegistry,
)

CORE = "https://cepio.org/ontology/core#"
ENERGY = "https://cepio.org/ontology/energy#"
PROD = "https://cepio.org/ontology/production#"

ProductionJourneyStatus = Literal["ANSWERED", "BLOCKED", "INSUFFICIENT_CEPIO_EVIDENCE"]


class ProductionJourneyBlocker(BaseModel):
    code: str
    message: str


class ProductionJourneyTrace(BaseModel):
    stage: str
    message: str


class ProductionJourneyResult(BaseModel):
    journey_id: str
    status: ProductionJourneyStatus
    question: str
    answer: dict[str, Any] | None = None
    preflights: list[SkillPreflightResult] = Field(default_factory=list)
    trace: list[ProductionJourneyTrace] = Field(default_factory=list)
    blockers: list[ProductionJourneyBlocker] = Field(default_factory=list)
    human_authority_required: bool = True
    prohibited_ai_conclusions: list[str] = Field(
        default_factory=lambda: [
            "change_live_setpoint",
            "start_or_stop_well",
            "override_operating_envelope",
            "approve_integrity_deviation",
            "approve_workover",
            "execute_intervention",
            "overwrite_external_record",
        ]
    )


class ProductionTechnologistV01CoverageResult(BaseModel):
    milestone: str = "CEPIO Production Technologist v0.1"
    benchmark_id: str
    synthetic: bool
    results: dict[str, ProductionJourneyResult]
    answered: int
    blocked: int
    frozen_future_journeys: list[str] = Field(
        default_factory=lambda: [
            "PROD-03", "PROD-04", "PROD-05", "PROD-07",
            "PROD-08", "PROD-09", "PROD-10",
        ]
    )

    @property
    def complete(self) -> bool:
        return self.blocked == 0 and set(self.results) == {"PROD-01", "PROD-02", "PROD-06"}


class ProductionTechnologistRuntime:
    """Execute governed Production Technologist v0.1 reference journeys."""

    JOURNEY_QUESTIONS: dict[str, str] = {
        "PROD-01": "Which wells need my attention today, why, and what evidence makes each exception material?",
        "PROD-02": (
            "What should Well P-118 be capable of producing under current conditions, "
            "what is it actually producing, and which model assumptions are no longer valid?"
        ),
        "PROD-06": (
            "Why is Well P-118 producing below expected deliverability, what evidence "
            "supports or contradicts each cause, and what observation would falsify each diagnosis?"
        ),
    }

    SKILL_IDS: dict[str, str] = {
        "PROD-01": "cepio.skill.production.surveillance-exception-triage",
        "PROD-02": "cepio.skill.production.deliverability-assurance",
        "PROD-06": "cepio.skill.production.underperformance-diagnosis",
    }

    def __init__(self, data: Mapping[str, Any], *, resource_root: str | Path | None = None) -> None:
        self.data: dict[str, Any] = deepcopy(dict(data))
        self.resource_root = Path(resource_root).resolve() if resource_root else None

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ProductionTechnologistRuntime":
        path = Path(path).resolve()
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Production Technologist benchmark must be a YAML mapping")
        return cls(payload, resource_root=path.parents[2])

    @classmethod
    def skill_specs(cls) -> dict[str, SkillPreflightSpec]:
        binding = "production-technologist-v0.1"
        return {
            "PROD-01": SkillPreflightSpec(
                skill_id=cls.SKILL_IDS["PROD-01"],
                binding_id=binding,
                object_types={
                    "case": f"{PROD}ProductionAssuranceCase",
                    "assessment": f"{PROD}WellPerformanceAssessment",
                    "well": f"{ENERGY}Well",
                },
                relationships={
                    "assurance_for_well": f"{PROD}assuranceForWell",
                    "has_assessment": f"{PROD}hasWellPerformanceAssessment",
                },
                graph_paths=[
                    SkillGraphPathRequirement(
                        id="production-case-assessment",
                        start_type="case",
                        steps=[SkillGraphPathStep(relationship="has_assessment", target_type="assessment")],
                    )
                ],
            ),
            "PROD-02": SkillPreflightSpec(
                skill_id=cls.SKILL_IDS["PROD-02"],
                binding_id=binding,
                object_types={
                    "case": f"{PROD}ProductionAssuranceCase",
                    "assessment": f"{PROD}WellPerformanceAssessment",
                    "deliverability": f"{PROD}DeliverabilityAssessment",
                    "evidence": f"{CORE}Evidence",
                    "assumption": f"{CORE}Assumption",
                    "uncertainty": f"{CORE}UncertaintyAssessment",
                    "well": f"{ENERGY}Well",
                },
                relationships={
                    "has_assessment": f"{PROD}hasWellPerformanceAssessment",
                    "has_evidence": f"{CORE}hasEvidence",
                    "has_assumption": f"{CORE}hasAssumption",
                    "has_uncertainty": f"{CORE}hasUncertaintyAssessment",
                },
                evidence_types={"evidence"},
                graph_paths=[
                    SkillGraphPathRequirement(
                        id="deliverability-evidence",
                        start_type="case",
                        steps=[SkillGraphPathStep(relationship="has_evidence", target_type="evidence")],
                    ),
                    SkillGraphPathRequirement(
                        id="deliverability-assumptions",
                        start_type="case",
                        steps=[SkillGraphPathStep(relationship="has_assumption", target_type="assumption")],
                    ),
                ],
            ),
            "PROD-06": SkillPreflightSpec(
                skill_id=cls.SKILL_IDS["PROD-06"],
                binding_id=binding,
                object_types={
                    "case": f"{PROD}ProductionAssuranceCase",
                    "hypothesis": f"{CORE}Hypothesis",
                    "evidence": f"{CORE}Evidence",
                    "confidence": f"{CORE}ConfidenceAssessment",
                    "uncertainty": f"{CORE}UncertaintyAssessment",
                    "well": f"{ENERGY}Well",
                },
                relationships={
                    "has_hypothesis": f"{CORE}hasHypothesis",
                    "supported_by": f"{CORE}supportedBy",
                    "has_confidence": f"{CORE}hasConfidenceAssessment",
                },
                evidence_types={"evidence"},
                graph_paths=[
                    SkillGraphPathRequirement(
                        id="diagnosis-hypothesis-evidence",
                        start_type="case",
                        steps=[
                            SkillGraphPathStep(relationship="has_hypothesis", target_type="hypothesis"),
                            SkillGraphPathStep(relationship="supported_by", target_type="evidence"),
                        ],
                    ),
                    SkillGraphPathRequirement(
                        id="diagnosis-confidence",
                        start_type="case",
                        steps=[
                            SkillGraphPathStep(relationship="has_hypothesis", target_type="hypothesis"),
                            SkillGraphPathStep(relationship="has_confidence", target_type="confidence"),
                        ],
                    ),
                ],
            ),
        }

    def _runtime(self, runtime: CEPIORuntime | None) -> CEPIORuntime:
        if runtime is not None:
            return runtime
        kwargs: dict[str, Any] = {}
        if self.resource_root is not None:
            kwargs["resource_root"] = self.resource_root
        return build_runtime(**kwargs)

    def _preflight(
        self,
        journey_id: str,
        runtime: CEPIORuntime,
        *,
        actor_id: str,
        actor_roles: set[str],
    ) -> list[SkillPreflightResult]:
        spec = self.skill_specs()[journey_id]
        registry = SkillRegistry(runtime)
        registry.register(spec)
        return [registry.preflight(spec.skill_id, actor_id=actor_id, actor_roles=actor_roles)]

    def _identity_blockers(self) -> list[ProductionJourneyBlocker]:
        blockers: list[ProductionJourneyBlocker] = []
        refs: list[tuple[str, Mapping[str, Any]]] = []
        focus = self.data.get("focus_well", {})
        identity = focus.get("external_identity")
        if isinstance(identity, Mapping):
            refs.append(("focus_well.external_identity", identity))
        model_ref = focus.get("deliverability_model", {}).get("source_ref")
        if isinstance(model_ref, Mapping):
            refs.append(("focus_well.deliverability_model.source_ref", model_ref))
        envelope_ref = focus.get("operating_envelope", {}).get("source_ref")
        if isinstance(envelope_ref, Mapping):
            refs.append(("focus_well.operating_envelope.source_ref", envelope_ref))
        for item in self.data.get("external_evidence", []):
            if isinstance(item, Mapping) and isinstance(item.get("source_ref"), Mapping):
                refs.append((f"external_evidence.{item.get('id', 'unknown')}", item["source_ref"]))
        for label, ref in refs:
            for key in ("source_system", "record_kind", "record_id", "record_version"):
                if not str(ref.get(key, "")).strip():
                    blockers.append(
                        ProductionJourneyBlocker(
                            code="INCOMPLETE_EXTERNAL_IDENTITY",
                            message=f"{label} is missing {key}",
                        )
                    )
        return blockers

    def execute(
        self,
        journey_id: str,
        *,
        runtime: CEPIORuntime | None = None,
        actor_id: str = "production_technologist",
        actor_roles: set[str] | None = None,
    ) -> ProductionJourneyResult:
        journey_id = journey_id.upper()
        if journey_id not in self.JOURNEY_QUESTIONS:
            raise ValueError(f"Journey {journey_id} is not executable in Production Technologist v0.1")
        roles = set(actor_roles or {"production_technologist"})
        cepio_runtime = self._runtime(runtime)
        preflights = self._preflight(journey_id, cepio_runtime, actor_id=actor_id, actor_roles=roles)
        blockers = [
            ProductionJourneyBlocker(
                code="SKILL_PREFLIGHT_BLOCKED",
                message=f"{p.skill_id}: {', '.join(sorted({b.code for b in p.blockers}))}",
            )
            for p in preflights
            if p.status == "BLOCKED"
        ]
        blockers.extend(self._identity_blockers())
        if blockers:
            return ProductionJourneyResult(
                journey_id=journey_id,
                status="BLOCKED",
                question=self.JOURNEY_QUESTIONS[journey_id],
                preflights=preflights,
                blockers=blockers,
            )
        handler = getattr(self, f"_execute_{journey_id.replace('-', '').lower()}")
        answer, trace = handler()
        return ProductionJourneyResult(
            journey_id=journey_id,
            status="ANSWERED",
            question=self.JOURNEY_QUESTIONS[journey_id],
            answer=answer,
            preflights=preflights,
            trace=trace,
        )

    def execute_all(
        self,
        *,
        runtime: CEPIORuntime | None = None,
        actor_id: str = "production_technologist",
        actor_roles: set[str] | None = None,
    ) -> ProductionTechnologistV01CoverageResult:
        cepio_runtime = self._runtime(runtime)
        results = {
            journey_id: self.execute(
                journey_id,
                runtime=cepio_runtime,
                actor_id=actor_id,
                actor_roles=actor_roles,
            )
            for journey_id in self.JOURNEY_QUESTIONS
        }
        answered = sum(result.status == "ANSWERED" for result in results.values())
        return ProductionTechnologistV01CoverageResult(
            benchmark_id=str(self.data.get("id", "")),
            synthetic=bool(self.data.get("synthetic", False)),
            results=results,
            answered=answered,
            blocked=len(results) - answered,
        )

    def _execute_prod01(self) -> tuple[dict[str, Any], list[ProductionJourneyTrace]]:
        portfolio = self.data["surveillance_portfolio"]
        details: dict[str, Any] = {}
        priority: list[tuple[int, float, str]] = []
        for well, state in portfolio.items():
            expected = float(state["expected_deliverability_bopd"])
            actual = float(state["actual_stable_rate_bopd"])
            gap = max(0.0, expected - actual)
            gap_fraction = gap / expected if expected else 0.0
            completeness = float(state.get("evidence_completeness", 0.0))
            flags = list(state.get("data_quality_flags") or [])
            if completeness < 0.70 or len(flags) >= 2:
                classification = "data_quality_limited"
                tier = 2
            elif gap_fraction >= 0.15:
                classification = "material_underperformance"
                tier = 3
            else:
                classification = "normal"
                tier = 1
            details[well] = {
                "classification": classification,
                "expected_deliverability_bopd": expected,
                "actual_stable_rate_bopd": actual,
                "deliverability_gap_bopd": round(gap, 1),
                "deliverability_gap_fraction": round(gap_fraction, 3),
                "evidence_completeness": completeness,
                "data_quality_flags": flags,
                "envelope_status": state.get("envelope_status"),
            }
            priority.append((tier, gap_fraction, well))
        attention_order = [well for _, _, well in sorted(priority, reverse=True)]
        return (
            {
                "attention_order": attention_order,
                "wells": details,
                "rule": "Evidence-limited wells are not converted into technical diagnoses; missing source evidence remains explicit.",
            },
            [
                ProductionJourneyTrace(
                    stage="surveillance-triage",
                    message=f"Triaged {len(details)} wells by material deviation and evidence fitness.",
                )
            ],
        )

    def _execute_prod02(self) -> tuple[dict[str, Any], list[ProductionJourneyTrace]]:
        focus = self.data["focus_well"]
        current = focus["current_state"]
        model = focus["deliverability_model"]
        expected = float(model["predicted_rate_bopd"])
        actual = float(current["actual_stable_rate_bopd"])
        gap = expected - actual
        assumptions = model["assumptions"]
        comparisons = {
            "water_cut_fraction": (float(assumptions["water_cut_fraction"]), float(current["water_cut_fraction"])),
            "gas_lift_mmscfd": (float(assumptions["gas_lift_mmscfd"]), float(current["gas_lift_mmscfd"])),
            "surface_backpressure_bar": (float(assumptions["surface_backpressure_bar"]), float(current["facility_backpressure_bar"])),
        }
        stale = [name for name, (assumed, observed) in comparisons.items() if abs(observed - assumed) > max(0.01, abs(assumed) * 0.05)]
        return (
            {
                "well": focus["id"],
                "model": {
                    "id": model["id"],
                    "source_ref": deepcopy(model["source_ref"]),
                    "calibration": deepcopy(model["calibration"]),
                },
                "expected_deliverability_bopd": expected,
                "actual_stable_rate_bopd": actual,
                "deliverability_gap_bopd": round(gap, 1),
                "deliverability_gap_fraction": round(gap / expected, 3) if expected else None,
                "assumption_reconciliation": {
                    name: {"model_assumption": assumed, "current_observation": observed}
                    for name, (assumed, observed) in comparisons.items()
                },
                "stale_or_violated_assumptions": stale,
                "uncertainty": {
                    "current_downhole_pressure": "insufficient_recent_evidence",
                    "implication": "CEPIO can explain model-context drift but must not attribute the full residual gap to reservoir or near-wellbore causes without updated pressure evidence.",
                },
                "cepio_recalculated_nodal_hydraulics": False,
                "required_external_computation": "Re-run or reconcile the authoritative nodal/network model using current governed conditions.",
            },
            [
                ProductionJourneyTrace(stage="model-identity", message=f"Resolved external model {model['id']} with source/version identity."),
                ProductionJourneyTrace(stage="model-vs-reality", message=f"Observed a {round(gap, 1)} bopd gap and {len(stale)} materially changed model assumptions."),
            ],
        )

    def _execute_prod06(self) -> tuple[dict[str, Any], list[ProductionJourneyTrace]]:
        evidence = {item["id"]: item for item in self.data["external_evidence"]}
        ranked = sorted(self.data["hypotheses"], key=lambda item: float(item["confidence"]), reverse=True)
        diagnoses = []
        evidence_gaps = []
        for item in ranked:
            gap = item.get("evidence_gap")
            if gap:
                evidence_gaps.append(str(gap))
            diagnoses.append(
                {
                    "id": item["id"],
                    "statement": item["statement"],
                    "confidence": float(item["confidence"]),
                    "supporting_evidence": [
                        {"id": evidence_id, "description": evidence[evidence_id]["description"]}
                        for evidence_id in item.get("supporting_evidence", [])
                    ],
                    "contradictory_evidence": [
                        {"id": evidence_id, "description": evidence[evidence_id]["description"]}
                        for evidence_id in item.get("contradictory_evidence", [])
                    ],
                    "estimated_exposure_bopd": item.get("estimated_exposure_bopd"),
                    "uncertainty": item.get("uncertainty"),
                    "evidence_gap": gap,
                    "falsification_test": item["falsification_test"],
                }
            )
        return (
            {
                "well": self.data["focus_well"]["id"],
                "ranked_hypotheses": diagnoses,
                "material_evidence_gaps": evidence_gaps,
                "recommended_next_steps": deepcopy(self.data["recommended_next_steps"]),
                "decision_rule": "A ranked diagnosis is not an operating instruction. Live changes and intervention approval remain outside AI authority.",
            },
            [
                ProductionJourneyTrace(stage="hypothesis-ranking", message=f"Ranked {len(diagnoses)} competing causes using benchmark confidence assessments."),
                ProductionJourneyTrace(stage="falsification", message="Attached a falsification or discriminating-evidence test to every diagnosis."),
            ],
        )


def run_production_technologist_v01(
    benchmark_path: str | Path,
    *,
    journey_id: str | None = None,
    runtime: CEPIORuntime | None = None,
    actor_id: str = "production_technologist",
    actor_roles: set[str] | None = None,
) -> ProductionJourneyResult | ProductionTechnologistV01CoverageResult:
    executor = ProductionTechnologistRuntime.from_yaml(benchmark_path)
    if journey_id:
        return executor.execute(
            journey_id,
            runtime=runtime,
            actor_id=actor_id,
            actor_roles=actor_roles,
        )
    return executor.execute_all(
        runtime=runtime,
        actor_id=actor_id,
        actor_roles=actor_roles,
    )
