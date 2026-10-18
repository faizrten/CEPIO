from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path

import yaml

KIN = "https://cepio.org/ontology/kinetic#"
AGENTIC = "https://cepio.org/ontology/agentic#"
CORE = "https://cepio.org/ontology/core#"
DRILL = "https://cepio.org/ontology/drilling#"
HSE = "https://cepio.org/ontology/hse#"
PERF = "https://cepio.org/ontology/performance#"
WF = "https://cepio.org/ontology/workforce#"


def term(iri: str, kind: str = "class") -> dict[str, str]:
    return {"iri": iri, "kind": kind}


def edge(source: str, predicate: str, target: str) -> dict[str, str]:
    return {"source": source, "predicate": predicate, "target": target}


def normalize(source: dict) -> dict:
    data = deepcopy(source)
    data["id"] = "drilling-contractor-domain-qualification-v0.4.1"
    data["version"] = "0.4.1"

    questions = {question["id"]: question for question in data["questions"]}

    questions["DC-DQ-009"]["capabilities"] = [
        {
            "id": "predictive-operational-risk",
            "description": (
                "Represent a model-derived prediction as inference, scope it to the current "
                "operating context and predicted risk, and keep it distinct from enterprise fact."
            ),
            "alternatives": [
                {
                    "id": "prediction-risk-context",
                    "terms": [
                        term(f"{AGENTIC}Prediction"),
                        term(f"{CORE}Risk"),
                        term(f"{DRILL}ActivityInterval"),
                    ],
                    "edges": [
                        edge(
                            f"{AGENTIC}Prediction",
                            f"{AGENTIC}predictionFor",
                            f"{DRILL}ActivityInterval",
                        ),
                        edge(f"{AGENTIC}Prediction", f"{AGENTIC}predictsRisk", f"{CORE}Risk"),
                    ],
                }
            ],
        }
    ]

    questions["DC-DQ-011"]["capabilities"] = [
        {
            "id": "evidence-grounded-agent-recommendation",
            "description": (
                "Bind an agent recommendation to the affected equipment, supporting enterprise "
                "evidence and a governance control point before execution."
            ),
            "alternatives": [
                {
                    "id": "recommendation-evidence-control",
                    "terms": [
                        term(f"{AGENTIC}Recommendation"),
                        term(f"{DRILL}BlowoutPreventer"),
                        term(f"{DRILL}WellControlTest"),
                        term(f"{AGENTIC}ControlPoint"),
                        term(f"{WF}AuthorityAssignment"),
                    ],
                    "edges": [
                        edge(
                            f"{AGENTIC}Recommendation",
                            f"{AGENTIC}recommendationFor",
                            f"{DRILL}BlowoutPreventer",
                        ),
                        edge(
                            f"{AGENTIC}Recommendation",
                            f"{AGENTIC}supportedByEvidence",
                            f"{DRILL}WellControlTest",
                        ),
                        edge(
                            f"{AGENTIC}Recommendation",
                            f"{AGENTIC}governedAtControlPoint",
                            f"{AGENTIC}ControlPoint",
                        ),
                    ],
                }
            ],
        }
    ]

    questions["DC-DQ-014"]["capabilities"] = [
        {
            "id": "governed-plan-deviation",
            "description": (
                "Preserve the original operating plan, proposed revision, authorizing decision, "
                "scoped authority and auditability as distinct governed records."
            ),
            "alternatives": [
                {
                    "id": "plan-revision-decision-authority",
                    "terms": [
                        term(f"{KIN}OperationalPlan"),
                        term(f"{KIN}PlanRevision"),
                        term(f"{KIN}Decision"),
                        term(f"{WF}AuthorityAssignment"),
                    ],
                    "edges": [
                        edge(f"{KIN}PlanRevision", f"{KIN}revisesPlan", f"{KIN}OperationalPlan"),
                        edge(f"{KIN}Decision", f"{KIN}authorizesRevision", f"{KIN}PlanRevision"),
                    ],
                }
            ],
        }
    ]

    questions["DC-DQ-015"]["capabilities"] = [
        {
            "id": "governed-agent-value-realization",
            "description": (
                "Assess whether a governed intervention changed an operating outcome using KPI "
                "evidence while retaining safety context and causal attribution."
            ),
            "alternatives": [
                {
                    "id": "outcome-assessment-decision-kpi",
                    "terms": [
                        term(f"{PERF}OutcomeAssessment"),
                        term(f"{KIN}Decision"),
                        term(f"{PERF}KPIObservation"),
                        term(f"{CORE}Risk"),
                    ],
                    "edges": [
                        edge(
                            f"{PERF}OutcomeAssessment",
                            f"{PERF}assessmentOfDecision",
                            f"{KIN}Decision",
                        ),
                        edge(
                            f"{PERF}OutcomeAssessment",
                            f"{PERF}observedOutcome",
                            f"{PERF}KPIObservation",
                        ),
                        edge(f"{PERF}OutcomeAssessment", f"{PERF}considersRisk", f"{CORE}Risk"),
                    ],
                }
            ],
        }
    ]

    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        default="generalization/competency/drilling-contractor-domain-qualification-v0.4.yaml",
    )
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    source = yaml.safe_load(Path(args.source).read_text())
    normalized = normalize(source)
    Path(args.out).write_text(yaml.safe_dump(normalized, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
