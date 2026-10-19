"""CEPIO Production Technologist v0.2 runtime.

Extends the qualified v0.1 surveillance/deliverability/diagnosis spine with:

PROD-03 Production Optimization & Constraint Allocation
PROD-04 Artificial Lift Performance & Optimization
PROD-05 Well Integrity & Operating Envelope Assurance

The runtime remains deterministic and recommendation-only. Engineering model
sensitivities are external evidence; CEPIO does not solve nodal/lift hydraulics
and does not authorize or execute live operating changes.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import yaml
from pydantic import BaseModel, Field

from .production_technology import (
    ProductionJourneyBlocker,
    ProductionJourneyResult,
    ProductionJourneyTrace,
    ProductionTechnologistRuntime,
)
from .runtime import CEPIORuntime
from .skill_preflight import SkillGraphPathRequirement, SkillGraphPathStep, SkillPreflightSpec

CORE = "https://cepio.org/ontology/core#"
ENERGY = "https://cepio.org/ontology/energy#"
KIN = "https://cepio.org/ontology/kinetic#"
PROD = "https://cepio.org/ontology/production#"


class ProductionTechnologistV02CoverageResult(BaseModel):
    milestone: str = "CEPIO Production Technologist v0.2 — Optimization, Artificial Lift & Operating Envelope"
    benchmark_id: str
    synthetic: bool
    results: dict[str, ProductionJourneyResult]
    answered: int
    blocked: int
    frozen_future_journeys: list[str] = Field(
        default_factory=lambda: ["PROD-07", "PROD-08", "PROD-09", "PROD-10"]
    )

    @property
    def complete(self) -> bool:
        return self.blocked == 0 and set(self.results) == {
            "PROD-01", "PROD-02", "PROD-03", "PROD-04", "PROD-05", "PROD-06"
        }


class ProductionTechnologistV02Runtime(ProductionTechnologistRuntime):
    """Execute the cumulative Production Technologist v0.2 persona depth slice."""

    JOURNEY_QUESTIONS = {
        **ProductionTechnologistRuntime.JOURNEY_QUESTIONS,
        "PROD-03": (
            "Given current well, lift-gas, integrity and surface constraints, which operating "
            "options for P-118 are feasible, which require review, and which should be rejected?"
        ),
        "PROD-04": (
            "Is P-118's gas-lift setting technically under-optimized under the current allocation "
            "constraint, where do external model sensitivities show diminishing returns, and what "
            "authorized test should be recommended?"
        ),
        "PROD-05": (
            "Which P-118 operating options remain inside the approved well operating envelope, "
            "which have insufficient margin, and which violate a hard limit?"
        ),
    }

    SKILL_IDS = {
        **ProductionTechnologistRuntime.SKILL_IDS,
        "PROD-03": "cepio.skill.production.constraint-aware-optimization",
        "PROD-04": "cepio.skill.production.artificial-lift-assurance",
        "PROD-05": "cepio.skill.production.operating-envelope-assurance",
    }

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ProductionTechnologistV02Runtime":
        path = Path(path).resolve()
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Production Technologist v0.2 benchmark must be a YAML mapping")
        base_ref = payload.get("base_benchmark")
        if not base_ref:
            return cls(payload, resource_root=path.parents[2])
        resource_root = path.parents[2]
        base_path = (resource_root / str(base_ref)).resolve()
        base_payload = yaml.safe_load(base_path.read_text(encoding="utf-8"))
        if not isinstance(base_payload, dict):
            raise ValueError("Base Production Technologist benchmark must be a YAML mapping")
        merged = deepcopy(base_payload)
        for key, value in payload.items():
            if key != "base_benchmark":
                merged[key] = deepcopy(value)
        return cls(merged, resource_root=resource_root)

    @classmethod
    def skill_specs(cls) -> dict[str, SkillPreflightSpec]:
        specs = dict(ProductionTechnologistRuntime.skill_specs())
        binding = "production-technologist-v0.2"
        specs.update(
            {
                "PROD-03": SkillPreflightSpec(
                    skill_id=cls.SKILL_IDS["PROD-03"],
                    binding_id=binding,
                    object_types={
                        "case": f"{PROD}ProductionAssuranceCase",
                        "constraint": f"{PROD}ProductionConstraintAssessment",
                        "opportunity": f"{KIN}Opportunity",
                        "option": f"{KIN}Option",
                        "recommendation": f"{KIN}OptionRecommendation",
                        "well": f"{ENERGY}Well",
                    },
                    relationships={
                        "has_assessment": f"{PROD}hasWellPerformanceAssessment",
                        "has_option": f"{KIN}hasOption",
                        "has_recommendation": f"{KIN}hasRecommendation",
                        "recommends_option": f"{KIN}recommendsOption",
                    },
                    graph_paths=[
                        SkillGraphPathRequirement(
                            id="optimization-constraint-context",
                            start_type="case",
                            steps=[SkillGraphPathStep(relationship="has_assessment", target_type="constraint")],
                        ),
                        SkillGraphPathRequirement(
                            id="optimization-options",
                            start_type="opportunity",
                            steps=[SkillGraphPathStep(relationship="has_option", target_type="option")],
                        ),
                        SkillGraphPathRequirement(
                            id="optimization-recommendation",
                            start_type="opportunity",
                            steps=[
                                SkillGraphPathStep(relationship="has_recommendation", target_type="recommendation"),
                                SkillGraphPathStep(relationship="recommends_option", target_type="option"),
                            ],
                        ),
                    ],
                ),
                "PROD-04": SkillPreflightSpec(
                    skill_id=cls.SKILL_IDS["PROD-04"],
                    binding_id=binding,
                    object_types={
                        "case": f"{PROD}ProductionAssuranceCase",
                        "lift_assessment": f"{PROD}ArtificialLiftPerformanceAssessment",
                        "evidence": f"{CORE}Evidence",
                        "uncertainty": f"{CORE}UncertaintyAssessment",
                        "well": f"{ENERGY}Well",
                    },
                    relationships={
                        "has_assessment": f"{PROD}hasWellPerformanceAssessment",
                        "has_evidence": f"{CORE}hasEvidence",
                    },
                    evidence_types={"evidence"},
                    graph_paths=[
                        SkillGraphPathRequirement(
                            id="lift-assurance-assessment",
                            start_type="case",
                            steps=[SkillGraphPathStep(relationship="has_assessment", target_type="lift_assessment")],
                        ),
                        SkillGraphPathRequirement(
                            id="lift-assurance-evidence",
                            start_type="case",
                            steps=[SkillGraphPathStep(relationship="has_evidence", target_type="evidence")],
                        ),
                    ],
                ),
                "PROD-05": SkillPreflightSpec(
                    skill_id=cls.SKILL_IDS["PROD-05"],
                    binding_id=binding,
                    object_types={
                        "case": f"{PROD}ProductionAssuranceCase",
                        "envelope": f"{PROD}WellOperatingEnvelope",
                        "limit": f"{PROD}WellOperatingLimit",
                        "integrity": f"{PROD}WellIntegrityAssessment",
                        "well": f"{ENERGY}Well",
                    },
                    relationships={
                        "has_envelope": f"{PROD}hasOperatingEnvelope",
                        "has_limit": f"{PROD}hasOperatingLimit",
                    },
                    graph_paths=[
                        SkillGraphPathRequirement(
                            id="well-envelope-limits",
                            start_type="case",
                            steps=[
                                SkillGraphPathStep(relationship="has_envelope", target_type="envelope"),
                                SkillGraphPathStep(relationship="has_limit", target_type="limit"),
                            ],
                        )
                    ],
                ),
            }
        )
        return specs

    def _identity_blockers(self) -> list[ProductionJourneyBlocker]:
        blockers = list(super()._identity_blockers())
        refs: list[tuple[str, Mapping[str, Any]]] = []
        optimization_ref = self.data.get("optimization_case", {}).get("source_ref")
        if isinstance(optimization_ref, Mapping):
            refs.append(("optimization_case.source_ref", optimization_ref))
        lift_ref = self.data.get("artificial_lift", {}).get("source_ref")
        if isinstance(lift_ref, Mapping):
            refs.append(("artificial_lift.source_ref", lift_ref))
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

    def execute_all(
        self,
        *,
        runtime: CEPIORuntime | None = None,
        actor_id: str = "production_technologist",
        actor_roles: set[str] | None = None,
    ) -> ProductionTechnologistV02CoverageResult:
        cepio_runtime = self._runtime(runtime)
        order = ["PROD-01", "PROD-02", "PROD-03", "PROD-04", "PROD-05", "PROD-06"]
        results = {
            journey_id: self.execute(
                journey_id,
                runtime=cepio_runtime,
                actor_id=actor_id,
                actor_roles=actor_roles,
            )
            for journey_id in order
        }
        answered = sum(result.status == "ANSWERED" for result in results.values())
        return ProductionTechnologistV02CoverageResult(
            benchmark_id=str(self.data.get("id", "")),
            synthetic=bool(self.data.get("synthetic", False)),
            results=results,
            answered=answered,
            blocked=len(results) - answered,
        )

    def _execute_prod03(self) -> tuple[dict[str, Any], list[ProductionJourneyTrace]]:
        case = self.data["optimization_case"]
        constraints = {item["id"]: item for item in case["constraints"]}
        max_drawdown = float(constraints["C-DRAWDOWN"]["maximum"])
        max_gas_lift = float(constraints["C-GASLIFT"]["maximum"])
        min_backpressure = float(constraints["C-BACKPRESSURE"]["minimum_attainable_without_reconfiguration"])

        evaluated: dict[str, Any] = {}
        feasible: list[dict[str, Any]] = []
        conditional: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        for option in case["options"]:
            violations: list[str] = []
            if float(option["estimated_drawdown_bar"]) > max_drawdown:
                violations.append("max_governed_drawdown")
            if float(option["gas_lift_mmscfd"]) > max_gas_lift:
                violations.append("lift_gas_allocation_cap")
            if float(option["facility_backpressure_bar"]) < min_backpressure:
                violations.append("surface_backpressure_operability_floor")
            margin = max_drawdown - float(option["estimated_drawdown_bar"])
            if violations:
                status = "rejected_constraint_violation"
                bucket = rejected
            elif margin <= 1.0:
                status = "conditional_integrity_review"
                bucket = conditional
            else:
                status = "feasible"
                bucket = feasible
            record = {
                **option,
                "drawdown_margin_bar": round(margin, 2),
                "constraint_violations": violations,
                "status": status,
            }
            evaluated[option["id"]] = record
            if float(option.get("expected_uplift_bopd", 0.0)) > 0:
                bucket.append(record)

        feasible.sort(key=lambda item: float(item["expected_uplift_bopd"]), reverse=True)
        conditional.sort(key=lambda item: float(item["expected_uplift_bopd"]), reverse=True)
        rejected.sort(key=lambda item: float(item["expected_uplift_bopd"]), reverse=True)
        recommended = feasible[0]["id"] if feasible else None
        return (
            {
                "well": self.data["focus_well"]["id"],
                "objective": case["objective"],
                "ranked_feasible_options": [item["id"] for item in feasible],
                "conditional_review_options": [item["id"] for item in conditional],
                "rejected_options": [item["id"] for item in rejected],
                "recommended_option": recommended,
                "options": evaluated,
                "recommendation_authority": "recommendation_only",
                "live_control_permitted": False,
                "cepio_solved_network_or_nodal_hydraulics": False,
            },
            [
                ProductionJourneyTrace(
                    stage="constraint-aware-optimization",
                    message=(
                        f"Evaluated {len(case['options'])} external operating sensitivities against "
                        "current lift-gas, surface-operability and governed drawdown constraints."
                    ),
                )
            ],
        )

    def _execute_prod04(self) -> tuple[dict[str, Any], list[ProductionJourneyTrace]]:
        lift = self.data["artificial_lift"]
        points = sorted(lift["external_sensitivity_points"], key=lambda item: float(item["gas_lift_mmscfd"]))
        marginal: list[dict[str, Any]] = []
        max_marginal = 0.0
        for left, right in zip(points, points[1:]):
            delta_lift = float(right["gas_lift_mmscfd"]) - float(left["gas_lift_mmscfd"])
            delta_rate = float(right["predicted_rate_bopd"]) - float(left["predicted_rate_bopd"])
            efficiency = delta_rate / delta_lift if delta_lift else 0.0
            max_marginal = max(max_marginal, efficiency)
            marginal.append(
                {
                    "from_mmscfd": float(left["gas_lift_mmscfd"]),
                    "to_mmscfd": float(right["gas_lift_mmscfd"]),
                    "incremental_rate_bopd": round(delta_rate, 1),
                    "marginal_bopd_per_mmscfd": round(efficiency, 1),
                }
            )
        diminishing_after = None
        for interval in marginal:
            if max_marginal and interval["marginal_bopd_per_mmscfd"] < 0.5 * max_marginal:
                diminishing_after = interval["from_mmscfd"]
                break

        cap = float(lift["field_allocation_cap_mmscfd"])
        candidates = [point for point in points if float(point["gas_lift_mmscfd"]) <= cap]
        candidate = max(candidates, key=lambda item: float(item["predicted_rate_bopd"]))
        current = float(lift["current_injection_mmscfd"])
        return (
            {
                "well": self.data["focus_well"]["id"],
                "lift_method": lift["method"],
                "current_gas_lift_mmscfd": current,
                "field_allocation_cap_mmscfd": cap,
                "constrained_candidate_mmscfd": float(candidate["gas_lift_mmscfd"]),
                "candidate_external_predicted_rate_bopd": float(candidate["predicted_rate_bopd"]),
                "diminishing_returns_after_mmscfd": diminishing_after,
                "marginal_response": marginal,
                "falsification_test": lift["falsification_test"],
                "recommended_next_step": (
                    "Recommend an authorized, monitored lift-response test up to the constrained candidate; "
                    "do not change the live setpoint autonomously."
                ),
                "cepio_calculated_lift_hydraulics": False,
                "live_setpoint_change_permitted": False,
            },
            [
                ProductionJourneyTrace(
                    stage="artificial-lift-assurance",
                    message=(
                        "Compared external gas-lift sensitivity outputs with the current field allocation cap "
                        "and identified the constrained candidate without recalculating lift hydraulics."
                    ),
                )
            ],
        )

    def _execute_prod05(self) -> tuple[dict[str, Any], list[ProductionJourneyTrace]]:
        focus = self.data["focus_well"]
        envelope = focus["operating_envelope"]
        evaluation = self.data["operating_envelope_evaluation"]
        options = {item["id"]: item for item in self.data["optimization_case"]["options"]}
        drawdown_limit = next(
            item for item in envelope["limits"] if item["parameter"] == "drawdown_bar" and "maximum" in item
        )
        maximum = float(drawdown_limit["maximum"])
        reduced_margin = float(evaluation["reduced_margin_thresholds"]["drawdown_bar"])

        statuses: dict[str, Any] = {}
        safe: list[str] = []
        review: list[str] = []
        prohibited: list[str] = []
        for option_id, option in options.items():
            predicted = float(option["estimated_drawdown_bar"])
            margin = maximum - predicted
            if margin < 0:
                status = "violates_hard_limit"
                prohibited.append(option_id)
            elif margin <= reduced_margin:
                status = "within_reduced_margin_requires_review"
                review.append(option_id)
            else:
                status = "within"
                safe.append(option_id)
            statuses[option_id] = {
                "expected_drawdown_bar": predicted,
                "maximum_drawdown_bar": maximum,
                "drawdown_margin_bar": round(margin, 2),
                "status": status,
            }

        return (
            {
                "well": focus["id"],
                "operating_envelope": envelope["id"],
                "safe_options": safe,
                "requires_integrity_or_operations_review": review,
                "prohibited_under_current_envelope": prohibited,
                "option_assessments": statuses,
                "authority_rule": evaluation["authority_rule"],
                "autonomous_exception_approval": False,
                "autonomous_operating_change": False,
            },
            [
                ProductionJourneyTrace(
                    stage="operating-envelope-assurance",
                    message=(
                        f"Classified {len(statuses)} operating options against governed drawdown limit "
                        f"{maximum:g} bar and reduced-margin threshold {reduced_margin:g} bar."
                    ),
                )
            ],
        )


def run_production_technologist_v02(
    benchmark_path: str | Path,
    *,
    actor_id: str = "production_technologist",
    actor_roles: set[str] | None = None,
) -> ProductionTechnologistV02CoverageResult:
    """Run cumulative Production Technologist v0.2 coverage against a benchmark YAML."""
    return ProductionTechnologistV02Runtime.from_yaml(benchmark_path).execute_all(
        actor_id=actor_id,
        actor_roles=actor_roles,
    )
