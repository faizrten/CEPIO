from pathlib import Path

import pytest

from cepio.generalization import CompetencyQuestion, OntologyIndex, evaluate_question, run_harness

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "generalization"
ARCHETYPE = BASE / "archetypes/drilling-contractor-v0.1.yaml"
PERSONAS = BASE / "personas/drilling-contractor-v0.2.yaml"
STANDARDS = BASE / "standards/drilling-references.yaml"
V02 = BASE / "competency/drilling-contractor-persona-expansion-v0.2.yaml"
V02_GAPS = BASE / "gaps/drilling-contractor-persona-v0.2.yaml"
V03 = BASE / "competency/drilling-contractor-persona-capabilities-v0.3.yaml"


def test_capability_alternatives_accept_any_complete_approved_pattern():
    ontology = OntologyIndex.from_repo(ROOT)
    question = CompetencyQuestion.model_validate(
        {
            "id": "ALT-001",
            "question": "Can one of the approved semantic patterns satisfy this capability?",
            "capabilities": [
                {
                    "id": "rig-identity",
                    "description": "Resolve a rig concept through one approved semantic alternative.",
                    "alternatives": [
                        {
                            "id": "missing-pattern",
                            "terms": [
                                {
                                    "iri": "https://cepio.org/ontology/drilling#DefinitelyMissing",
                                    "kind": "class",
                                }
                            ],
                        },
                        {
                            "id": "operating-rig",
                            "terms": [
                                {
                                    "iri": "https://cepio.org/ontology/drilling#OperatingRig",
                                    "kind": "class",
                                }
                            ],
                        },
                    ],
                }
            ],
        }
    )

    result = evaluate_question(question, ontology)
    assert result["status"] == "PASS"
    assert result["checks_passed"] == 1
    assert result["checks_total"] == 1
    assert result["capability_details"][0]["matched_pattern"] == "operating-rig"


def test_literal_v02_pack_remains_backward_compatible():
    report = run_harness(ROOT, ARCHETYPE, V02, PERSONAS, STANDARDS, V02_GAPS)
    assert report["harness_version"] == "0.1"
    assert report["evaluation_contract"] == "literal-prerequisites"
    assert report["status_counts"] == {"PASS": 6, "PARTIAL": 8, "FAIL": 0, "ERROR": 0}
    assert report["semantic_check_pass_rate"] == pytest.approx(64 / 74)


def test_drilling_persona_capability_contract_v03_is_fully_answerable_semantically():
    report = run_harness(ROOT, ARCHETYPE, V03, PERSONAS, STANDARDS)
    assert report["harness_version"] == "0.2"
    assert report["evaluation_contract"] == "capability-alternatives"
    assert report["mode"] == "deterministic-semantic-capability-readiness"
    assert report["question_count"] == 14
    assert report["status_counts"] == {"PASS": 14, "PARTIAL": 0, "FAIL": 0, "ERROR": 0}
    assert report["semantic_check_pass_rate"] == pytest.approx(1.0)
    assert all(result["capability_details"] for result in report["results"])
    assert all(
        detail["matched_pattern"] is not None
        for result in report["results"]
        for detail in result["capability_details"]
    )
