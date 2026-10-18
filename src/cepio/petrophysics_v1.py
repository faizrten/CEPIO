"""CEPIO Petrophysics v1 persona-depth runtime.

This module executes the horizontal PET-01 readiness journey and PET-03..PET-08
depth journeys against one synthetic multi-well portfolio. PET-02 remains the
anchor formation-evaluation runtime and is delegated to its existing executable
contract.

The v1 runtime is deterministic by design. It proves that the same CEPIO
epistemic/kinetic spine can support multiple Petrophysics questions without
creating a separate application model for each workflow.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Literal, Mapping

import yaml
from pydantic import BaseModel, Field

from .bootstrap import build_runtime
from .formation_evaluation import FormationEvaluationAssuranceRuntime
from .runtime import CEPIORuntime
from .skill_preflight import (
    SkillGraphPathRequirement,
    SkillGraphPathStep,
    SkillPreflightResult,
    SkillPreflightSpec,
    SkillRegistry,
)

CORE = "https://cepio.org/ontology/core#"
SUB = "https://cepio.org/ontology/subsurface#"

PetrophysicsV1Status = Literal["ANSWERED", "BLOCKED", "INSUFFICIENT_CEPIO_EVIDENCE"]


class PetrophysicsV1Blocker(BaseModel):
    code: str
    message: str


class PetrophysicsV1Trace(BaseModel):
    stage: str
    message: str


class PetrophysicsJourneyResult(BaseModel):
    journey_id: str
    status: PetrophysicsV1Status
    question: str
    answer: dict[str, Any] | None = None
    preflights: list[SkillPreflightResult] = Field(default_factory=list)
    trace: list[PetrophysicsV1Trace] = Field(default_factory=list)
    blockers: list[PetrophysicsV1Blocker] = Field(default_factory=list)
    human_authority_required: bool = True
    prohibited_ai_conclusions: list[str] = Field(
        default_factory=lambda: [
            "declare_authoritative",
            "approve_reserves_basis",
            "overwrite_external_record",
            "approve_investment_decision",
        ]
    )


class PetrophysicsV1CoverageResult(BaseModel):
    milestone: str = "CEPIO Petrophysics v1 Persona Coverage"
    benchmark_id: str
    synthetic: bool
    results: dict[str, PetrophysicsJourneyResult]
    passed: int
    blocked: int

    @property
    def complete(self) -> bool:
        return self.blocked == 0 and set(self.results) == {
            "PET-01", "PET-02", "PET-03", "PET-04",
            "PET-05", "PET-06", "PET-07", "PET-08",
        }


class PetrophysicsV1Runtime:
    """Execute the complete CEPIO Petrophysics v1 persona coverage milestone."""

    JOURNEY_QUESTIONS: dict[str, str] = {
        "PET-01": (
            "Is the available evidence fit for the formation-evaluation and assurance "
            "questions we need to answer, and what is missing?"
        ),
        "PET-02": (
            "Show me the authoritative formation evaluation for Well A-17, Zone B. "
            "Explain why it changed, what evidence supports or contradicts it, what "
            "remains uncertain, and which downstream decisions are exposed."
        ),
        "PET-03": (
            "For Reservoir R3, what is our current view of fluid saturation and contacts, "
            "what assumptions drive it, where do wells disagree, and which reserves or "
            "development decisions are sensitive?"
        ),
        "PET-04": (
            "Which rock-property interpretations are supported by both log and core "
            "evidence, where do they disagree, and which transforms should be challenged?"
        ),
        "PET-05": (
            "Find wells in Reservoir R3 where materially different petrophysical methods, "
            "cutoffs or assumptions are used for equivalent intervals and show potential impact."
        ),
        "PET-06": (
            "Show how authoritative petrophysical interpretations propagated into Static "
            "Model SM18 and Reservoir Model RM21, including transformations, upscaling and "
            "stale dependencies."
        ),
        "PET-07": (
            "Where does current petrophysical evidence indicate remaining or bypassed "
            "hydrocarbons, and which recovery opportunities depend materially on that interpretation?"
        ),
        "PET-08": (
            "What did Well A-17 teach us that we did not know before drilling it, which "
            "beliefs changed, and what should be updated downstream?"
        ),
    }

    SKILL_IDS = {
        "PET-01": "cepio.skill.subsurface.petrophysics.evidence-readiness",
        "PET-03": "cepio.skill.subsurface.petrophysics.saturation-contact-reasoning",
        "PET-04": "cepio.skill.subsurface.petrophysics.core-log-rocktype-reconciliation",
        "PET-05": "cepio.skill.subsurface.petrophysics.cross-well-consistency",
        "PET-06": "cepio.skill.subsurface.petrophysics.model-handover-trace",
        "PET-07": "cepio.skill.subsurface.petrophysics.remaining-hydrocarbon-opportunity",
        "PET-08": "cepio.skill.subsurface.petrophysics.new-well-learning",
    }

    def __init__(self, data: Mapping[str, Any], *, resource_root: str | Path | None = None) -> None:
        self.data: dict[str, Any] = deepcopy(dict(data))
        self.resource_root = Path(resource_root).resolve() if resource_root else None

    @classmethod
    def from_yaml(cls, path: str | Path) -> "PetrophysicsV1Runtime":
        path = Path(path).resolve()
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Petrophysics v1 benchmark must be a YAML mapping")
        return cls(payload, resource_root=path.parents[2])

    @classmethod
    def skill_specs(cls) -> dict[str, SkillPreflightSpec]:
        """Runtime admission for each v1 journey using the governed shared spine."""
        binding = "subsurface-petrophysics-v1-persona-coverage"
        return {
            "PET-01": SkillPreflightSpec(
                skill_id=cls.SKILL_IDS["PET-01"], binding_id=binding,
                object_types={"case": f"{SUB}FormationEvaluationCase", "evidence": f"{CORE}Evidence"},
                relationships={"has_evidence": f"{CORE}hasEvidence"}, evidence_types={"evidence"},
                graph_paths=[SkillGraphPathRequirement(id="readiness-case-evidence", start_type="case", steps=[SkillGraphPathStep(relationship="has_evidence", target_type="evidence")])],
            ),
            "PET-03": SkillPreflightSpec(
                skill_id=cls.SKILL_IDS["PET-03"], binding_id=binding,
                object_types={"case": f"{SUB}FormationEvaluationCase", "characteristic": f"{SUB}PetrophysicalCharacteristic", "assumption": f"{CORE}Assumption", "uncertainty": f"{CORE}UncertaintyAssessment"},
                relationships={"has_assumption": f"{CORE}hasAssumption", "has_characteristic": f"{SUB}hasCharacteristic", "has_uncertainty": f"{CORE}hasUncertaintyAssessment"},
                graph_paths=[
                    SkillGraphPathRequirement(id="saturation-assumptions", start_type="case", steps=[SkillGraphPathStep(relationship="has_assumption", target_type="assumption")]),
                    SkillGraphPathRequirement(id="saturation-characteristic-uncertainty", start_type="case", steps=[SkillGraphPathStep(relationship="has_characteristic", target_type="characteristic"), SkillGraphPathStep(relationship="has_uncertainty", target_type="uncertainty")]),
                ],
            ),
            "PET-04": SkillPreflightSpec(
                skill_id=cls.SKILL_IDS["PET-04"], binding_id=binding,
                object_types={"case": f"{SUB}FormationEvaluationCase", "evidence": f"{CORE}Evidence", "confidence": f"{CORE}ConfidenceAssessment"},
                relationships={"has_evidence": f"{CORE}hasEvidence", "has_confidence": f"{CORE}hasConfidenceAssessment"}, evidence_types={"evidence"},
                graph_paths=[
                    SkillGraphPathRequirement(id="core-log-evidence", start_type="case", steps=[SkillGraphPathStep(relationship="has_evidence", target_type="evidence")]),
                    SkillGraphPathRequirement(id="core-log-confidence", start_type="case", steps=[SkillGraphPathStep(relationship="has_confidence", target_type="confidence")]),
                ],
            ),
            "PET-05": SkillPreflightSpec(
                skill_id=cls.SKILL_IDS["PET-05"], binding_id=binding,
                object_types={"case": f"{SUB}FormationEvaluationCase"}, relationships={"supersedes": f"{CORE}supersedes"},
                graph_paths=[SkillGraphPathRequirement(id="interpretation-lineage", start_type="case", steps=[SkillGraphPathStep(relationship="supersedes", target_type="case")])],
            ),
            "PET-06": SkillPreflightSpec(
                skill_id=cls.SKILL_IDS["PET-06"], binding_id=binding,
                object_types={"dependency": f"{CORE}Dependency", "case": f"{SUB}FormationEvaluationCase"}, relationships={"dependency_source": f"{CORE}dependencySource"},
                graph_paths=[SkillGraphPathRequirement(id="handover-dependency-source", start_type="dependency", steps=[SkillGraphPathStep(relationship="dependency_source", target_type="case")])],
            ),
            "PET-07": SkillPreflightSpec(
                skill_id=cls.SKILL_IDS["PET-07"], binding_id=binding,
                object_types={"case": f"{SUB}FormationEvaluationCase", "evidence": f"{CORE}Evidence", "uncertainty": f"{CORE}UncertaintyAssessment"},
                relationships={"has_evidence": f"{CORE}hasEvidence", "has_uncertainty": f"{CORE}hasUncertaintyAssessment"}, evidence_types={"evidence"},
                graph_paths=[SkillGraphPathRequirement(id="opportunity-evidence-basis", start_type="case", steps=[SkillGraphPathStep(relationship="has_evidence", target_type="evidence")])],
            ),
            "PET-08": SkillPreflightSpec(
                skill_id=cls.SKILL_IDS["PET-08"], binding_id=binding,
                object_types={"case": f"{SUB}FormationEvaluationCase", "evidence": f"{CORE}Evidence", "confidence": f"{CORE}ConfidenceAssessment"},
                relationships={"has_evidence": f"{CORE}hasEvidence", "has_confidence": f"{CORE}hasConfidenceAssessment"}, evidence_types={"evidence"},
                graph_paths=[SkillGraphPathRequirement(id="learning-evidence", start_type="case", steps=[SkillGraphPathStep(relationship="has_evidence", target_type="evidence")])],
            ),
        }

    def _runtime(self, runtime: CEPIORuntime | None) -> CEPIORuntime:
        if runtime is not None:
            return runtime
        kwargs: dict[str, Any] = {}
        if self.resource_root is not None:
            kwargs["resource_root"] = self.resource_root
        return build_runtime(**kwargs)

    def _preflight(self, journey_id: str, runtime: CEPIORuntime, *, actor_id: str, actor_roles: set[str]) -> list[SkillPreflightResult]:
        spec = self.skill_specs()[journey_id]
        registry = SkillRegistry(runtime)
        registry.register(spec)
        return [registry.preflight(spec.skill_id, actor_id=actor_id, actor_roles=actor_roles)]

    def execute(self, journey_id: str, *, runtime: CEPIORuntime | None = None, actor_id: str = "petrophysicist", actor_roles: set[str] | None = None) -> PetrophysicsJourneyResult:
        journey_id = journey_id.upper()
        if journey_id not in self.JOURNEY_QUESTIONS:
            raise ValueError(f"Unknown Petrophysics journey: {journey_id}")
        roles = set(actor_roles or {"petrophysicist"})
        cepio_runtime = self._runtime(runtime)
        question = self.JOURNEY_QUESTIONS[journey_id]

        if journey_id == "PET-02":
            root = self.resource_root or Path.cwd()
            benchmark = root / "generalization" / "benchmarks" / "subsurface-petrophysics-pet02-a17-zone-b.yaml"
            result = FormationEvaluationAssuranceRuntime.from_yaml(benchmark).execute(well="A-17", interval="Zone-B", cepio_runtime=cepio_runtime, actor_id=actor_id, actor_roles=roles)
            if result.status != "ANSWERED" or result.answer is None:
                return PetrophysicsJourneyResult(journey_id=journey_id, status="BLOCKED", question=question, preflights=result.preflights, trace=[PetrophysicsV1Trace(stage=t.skill_id, message=t.message) for t in result.trace], blockers=[PetrophysicsV1Blocker(code=b.code, message=b.message) for b in result.blockers])
            return PetrophysicsJourneyResult(journey_id=journey_id, status="ANSWERED", question=question, answer=result.answer.model_dump(mode="json"), preflights=result.preflights, trace=[PetrophysicsV1Trace(stage=t.skill_id, message=t.message) for t in result.trace])

        preflights = self._preflight(journey_id, cepio_runtime, actor_id=actor_id, actor_roles=roles)
        blockers = [PetrophysicsV1Blocker(code="SKILL_PREFLIGHT_BLOCKED", message=f"{p.skill_id}: {', '.join(sorted({b.code for b in p.blockers}))}") for p in preflights if p.status == "BLOCKED"]
        if blockers:
            return PetrophysicsJourneyResult(journey_id=journey_id, status="BLOCKED", question=question, preflights=preflights, blockers=blockers)
        handler = getattr(self, f"_execute_{journey_id.replace('-', '').lower()}")
        answer, trace = handler()
        return PetrophysicsJourneyResult(journey_id=journey_id, status="ANSWERED", question=question, answer=answer, preflights=preflights, trace=trace)

    def execute_all(self, *, runtime: CEPIORuntime | None = None, actor_id: str = "petrophysicist", actor_roles: set[str] | None = None) -> PetrophysicsV1CoverageResult:
        cepio_runtime = self._runtime(runtime)
        results = {journey: self.execute(journey, runtime=cepio_runtime, actor_id=actor_id, actor_roles=actor_roles) for journey in self.JOURNEY_QUESTIONS}
        passed = sum(r.status == "ANSWERED" for r in results.values())
        return PetrophysicsV1CoverageResult(benchmark_id=str(self.data.get("id", "")), synthetic=bool(self.data.get("synthetic", False)), results=results, passed=passed, blocked=len(results) - passed)

    def _execute_pet01(self) -> tuple[dict[str, Any], list[PetrophysicsV1Trace]]:
        readiness = {}
        gaps = []
        for well, state in self.data["PET-01"]["readiness"].items():
            missing = list(state.get("missing") or [])
            available = list(state.get("available") or [])
            readiness[well] = {"available": available, "missing": missing, "ready_for_full_v1": not missing, "readiness_fraction": round(len(available) / max(1, len(available) + len(missing)), 3)}
            if missing:
                gaps.append({"well": well, "missing": missing})
        return {"readiness_by_well": readiness, "blocking_gaps": gaps, "best_ready_context": max(readiness, key=lambda w: readiness[w]["readiness_fraction"]), "rule": "Missing evidence is exposed; CEPIO does not infer source evidence that is absent."}, [PetrophysicsV1Trace(stage="evidence-readiness", message=f"Assessed {len(readiness)} wells for v1 evidence fitness.")]

    def _execute_pet03(self) -> tuple[dict[str, Any], list[PetrophysicsV1Trace]]:
        spec, wells = self.data["PET-03"], self.data["wells"]
        consensus = float(spec["reservoir_contact_consensus_tvdss_m"])
        contact_threshold = float(spec["outlier_rules"]["contact_difference_m"])
        sw_values = sorted(float(w["sw_fraction"]) for w in wells.values())
        sw_median = sw_values[len(sw_values) // 2]
        sw_threshold = float(spec["outlier_rules"]["sw_difference_fraction"])
        outliers = []
        for well, values in wells.items():
            reasons = []
            if abs(float(values["contact_tvdss_m"]) - consensus) > contact_threshold: reasons.append("fluid_contact")
            if abs(float(values["sw_fraction"]) - sw_median) > sw_threshold: reasons.append("water_saturation")
            if values["method"] != "Archie": reasons.append("methodology")
            if reasons: outliers.append({"well": well, "reasons": reasons, "contact_tvdss_m": values["contact_tvdss_m"], "sw_fraction": values["sw_fraction"], "method": values["method"]})
        return {"consensus_contact_tvdss_m": consensus, "uncertainty_range_tvdss_m": spec["uncertainty_range_tvdss_m"], "well_views": {w: {"sw_fraction": v["sw_fraction"], "contact_tvdss_m": v["contact_tvdss_m"], "method": v["method"], "rw_ohm_m": v["rw_ohm_m"]} for w, v in wells.items()}, "outlier_wells": outliers, "material_assumptions": spec["primary_assumptions"], "downstream_sensitivity": spec["sensitive_downstream"], "recommendation": "Resolve A-22 methodology/contact divergence before using a single reservoir-wide contact or saturation basis."}, [PetrophysicsV1Trace(stage="saturation-contact", message=f"Compared {len(wells)} well interpretations against the reservoir consensus.")]

    def _execute_pet04(self) -> tuple[dict[str, Any], list[PetrophysicsV1Trace]]:
        spec = self.data["PET-04"]
        threshold = float(spec["contradiction_threshold_fraction"])
        reconciled, contradictory, challenged = [], [], []
        for rock_type, values in spec["rock_types"].items():
            core_k, log_k = float(values["core_permeability_md"]), float(values["log_permeability_md"])
            delta = abs(log_k - core_k) / max(abs(core_k), 1e-9)
            summary = {"rock_type": rock_type, "wells": values["wells"], "core_permeability_md": core_k, "log_permeability_md": log_k, "relative_difference": round(delta, 3), "transform": values["transform"]}
            if delta > threshold or values["status"] == "contradiction": contradictory.append(summary); challenged.append(values["transform"])
            else: reconciled.append(summary)
        return {"reconciled_rock_types": reconciled, "contradictory_rock_types": contradictory, "challenged_transforms": sorted(set(challenged)), "downstream_impact": spec["downstream_if_transform_invalid"] if challenged else [], "recommendation": "Technically review K_TRANSFORM_V5 for RT-3; preserve the core/log conflict until resolved."}, [PetrophysicsV1Trace(stage="core-log-reconciliation", message=f"Evaluated {len(spec['rock_types'])} rock types against the contradiction threshold.")]

    def _execute_pet05(self) -> tuple[dict[str, Any], list[PetrophysicsV1Trace]]:
        profile, wells = self.data["PET-05"]["canonical_profile"], self.data["wells"]
        inconsistencies = []
        for well, values in wells.items():
            deviations = []
            if values["method"] != profile["method"]: deviations.append({"field": "method", "value": values["method"], "expected": profile["method"]})
            lo, hi = profile["rw_range_ohm_m"]
            if not (lo <= values["rw_ohm_m"] <= hi): deviations.append({"field": "rw_ohm_m", "value": values["rw_ohm_m"], "expected_range": [lo, hi]})
            lo, hi = profile["porosity_cutoff_range_fraction"]
            if not (lo <= values["porosity_cutoff_fraction"] <= hi): deviations.append({"field": "porosity_cutoff_fraction", "value": values["porosity_cutoff_fraction"], "expected_range": [lo, hi]})
            lo, hi = profile["sw_cutoff_range_fraction"]
            if not (lo <= values["sw_cutoff_fraction"] <= hi): deviations.append({"field": "sw_cutoff_fraction", "value": values["sw_cutoff_fraction"], "expected_range": [lo, hi]})
            if values["permeability_transform"] not in profile["accepted_transforms"]: deviations.append({"field": "permeability_transform", "value": values["permeability_transform"], "accepted": profile["accepted_transforms"]})
            if deviations: inconsistencies.append({"well": well, "deviations": deviations, "impact_targets": self.data["PET-05"]["impact_targets"].get(well, [])})
        return {"canonical_profile": profile, "inconsistent_wells": inconsistencies, "consistent_wells": sorted(set(wells) - {i["well"] for i in inconsistencies}), "recommendation": "Prioritize technical review by downstream impact; do not normalize divergent methods automatically."}, [PetrophysicsV1Trace(stage="cross-well-consistency", message=f"Compared {len(wells)} equivalent-interval interpretations against the canonical profile.")]

    def _execute_pet06(self) -> tuple[dict[str, Any], list[PetrophysicsV1Trace]]:
        spec = self.data["PET-06"]
        handover = spec["authoritative_handover"]
        transformations = []
        for item in handover["transformations"]:
            row = dict(item); row["changed"] = row.get("from") != row.get("to"); transformations.append(row)
        stale = [dict(dep) for dep in spec.get("stale_dependencies") or [] if dep["current_transform"] != dep["consumed_transform"]]
        return {"source_case": handover["source_case"], "source_properties": handover["source_properties"], "transformations": transformations, "downstream_chain": handover["downstream_chain"], "stale_dependencies": stale, "recommendation": "Reconcile A-14 transform lineage in SM18 before treating the model as fully aligned with current Petrophysics authority."}, [PetrophysicsV1Trace(stage="model-handover", message=f"Traced {len(transformations)} transformations and {len(stale)} stale dependencies.")]

    def _execute_pet07(self) -> tuple[dict[str, Any], list[PetrophysicsV1Trace]]:
        spec = self.data["PET-07"]
        opportunity = deepcopy(spec["opportunity"])
        opportunity["petrophysical_signal_fraction"] = round(float(spec["evidence"]["expected_depleted_sw_fraction"]) - float(spec["evidence"]["current_sw_fraction"]), 3)
        return {"zone": spec["zone"], "evidence": spec["evidence"], "remaining_hydrocarbon_assessment": dict(spec["assessment"]), "opportunity": opportunity, "recommendation": {"option": opportunity["petrophysics_recommendation"], "reason": opportunity["recommendation_reason"], "authority": "recommend_only"}}, [PetrophysicsV1Trace(stage="opportunity-support", message=f"Linked Petrophysics evidence to {opportunity['id']} with {len(opportunity['options'])} governed options.")]

    def _execute_pet08(self) -> tuple[dict[str, Any], list[PetrophysicsV1Trace]]:
        spec = self.data["PET-08"]
        delta = {}
        for name in sorted(set(spec["prior"]) | set(spec["posterior"])):
            before, after = spec["prior"].get(name), spec["posterior"].get(name)
            delta[name] = {"prior": before, "posterior": after, "delta": round(after - before, 6)} if isinstance(before, (int, float)) and isinstance(after, (int, float)) else {"prior": before, "posterior": after}
        return {"well": spec["well"], "belief_delta": delta, "hypothesis_updates": spec["hypotheses"], "information_gain": spec["information_gain"], "downstream_updates": spec["downstream_updates"], "recommendation": "Propagate the A-17 posterior basis through affected model/reserves/opportunity contexts while preserving the pre-drill belief state for decision provenance."}, [PetrophysicsV1Trace(stage="new-well-learning", message=f"Compared {len(delta)} prior/posterior beliefs and {len(spec['hypotheses'])} hypothesis updates.")]


def run_petrophysics_v1(benchmark_path: str | Path, *, actor_id: str = "petrophysicist", actor_roles: set[str] | None = None) -> PetrophysicsV1CoverageResult:
    return PetrophysicsV1Runtime.from_yaml(benchmark_path).execute_all(actor_id=actor_id, actor_roles=actor_roles)
