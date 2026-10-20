from copy import deepcopy
from pathlib import Path

import pytest
import yaml

import cepio.icc_qualification as icc
from cepio.domain_onboarding import run_domain_onboarding
from cepio.generalization import load_pack
from cepio.persona_binding import (
    PersonaCapabilityBinding,
    PersonaQuestionBinding,
    load_persona_binding,
    resolve_persona_questions,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "generalization/domain-packs/drilling-contractor-reference-v0.1.yaml"
WORKFLOW = ROOT / "workflows/domain-onboarding-v0.1.yaml"
POLICY = ROOT / "policies/domain-onboarding-v0.1.yaml"
COMPETENCY = ROOT / "generalization/competency/drilling-contractor-persona-capabilities-v0.3.yaml"


def _rig_manager_question_id() -> str:
    pack = load_pack(COMPETENCY)
    return next(question.id for question in pack.questions if "rig-manager" in question.personas)


def _binding(**overrides):
    pack = load_pack(COMPETENCY)
    values = {
        "id": "test-binding-v0.1",
        "version": "0.1",
        "domain": "drilling-contractor",
        "persona_id": "rig-manager",
        "competency_pack_id": pack.id,
        "minimum_question_count": 1,
        "questions": [
            PersonaQuestionBinding(
                question_id=pack.questions[0].id,
                mode="primary",
                rationale="test coverage",
            )
        ],
    }
    values.update(overrides)
    return PersonaCapabilityBinding(**values)


def _manifest_copy(tmp_path: Path, **overrides) -> Path:
    payload = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    payload.update(overrides)
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def test_rig_manager_icc_is_persona_scoped_and_reuses_existing_capabilities():
    report = icc.run_icc_persona_qualification(ROOT, MANIFEST, WORKFLOW, POLICY)

    assert report["status"] == "READY_FOR_HUMAN_REVIEW"
    assert report["qualification_status"] == "QUALIFIED"
    assert report["domain"] == "drilling-contractor"
    assert report["persona_id"] == "rig-manager"
    assert report["persona_binding"]["role"] == "Rig Manager"
    assert report["persona_binding"]["selection_source"] == "explicit-persona-binding"
    assert report["persona_binding"]["binding_id"] == "drilling-contractor-rig-manager-binding-v0.1"
    assert report["persona_binding"]["question_count"] == 14
    assert report["qualification"]["semantic_pass_rate"] == 1.0
    assert report["qualification"]["runtime_coverage_rate"] == 1.0
    assert report["icc_delta"]["required_question_ids"] == [
        f"DC-PC-{index:03d}" for index in range(1, 15)
    ]
    assert report["icc_delta"]["required_capabilities"]
    assert len(report["icc_delta"]["reused_capabilities"]) == len(
        report["icc_delta"]["required_capabilities"]
    )
    assert report["icc_delta"]["missing_capabilities"] == []
    assert report["icc_delta"]["new_semantic_candidates"] == []
    assert report["icc_delta"]["runtime_gaps"] == []
    assert report["icc_delta"]["policy_authority_gaps"] == []
    assert report["human_review_required"] is True
    assert len(report["provenance"]["manifest_sha256"]) == 64
    assert len(report["provenance"]["persona_binding_sha256"]) == 64
    assert len(report["provenance"]["persona_scope_hash"]) == 64


def test_persona_binding_loader_and_validation_fail_closed(tmp_path):
    invalid = tmp_path / "invalid-binding.yaml"
    invalid.write_text("- not\n- a\n- mapping\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must contain a YAML mapping"):
        load_persona_binding(invalid)

    pack = load_pack(COMPETENCY)

    with pytest.raises(ValueError, match="does not match manifest domain"):
        resolve_persona_questions(
            _binding(domain="wrong-domain"),
            pack,
            domain="drilling-contractor",
            persona_id="rig-manager",
        )

    with pytest.raises(ValueError, match="does not match requested persona"):
        resolve_persona_questions(
            _binding(persona_id="wrong-persona"),
            pack,
            domain="drilling-contractor",
            persona_id="rig-manager",
        )

    with pytest.raises(ValueError, match="competency_pack_id does not match"):
        resolve_persona_questions(
            _binding(competency_pack_id="wrong-pack"),
            pack,
            domain="drilling-contractor",
            persona_id="rig-manager",
        )

    duplicate = PersonaQuestionBinding(
        question_id=pack.questions[0].id,
        mode="oversight",
        rationale="duplicate",
    )
    with pytest.raises(ValueError, match="duplicate question IDs"):
        resolve_persona_questions(
            _binding(questions=[duplicate, duplicate]),
            pack,
            domain="drilling-contractor",
            persona_id="rig-manager",
        )

    unknown = PersonaQuestionBinding(
        question_id="UNKNOWN-QUESTION",
        mode="support",
        rationale="unknown",
    )
    with pytest.raises(ValueError, match="unknown competency questions"):
        resolve_persona_questions(
            _binding(questions=[unknown]),
            pack,
            domain="drilling-contractor",
            persona_id="rig-manager",
        )

    with pytest.raises(ValueError, match="requires at least 2"):
        resolve_persona_questions(
            _binding(minimum_question_count=2),
            pack,
            domain="drilling-contractor",
            persona_id="rig-manager",
        )


def test_icc_yaml_loader_and_scope_helpers_fail_closed(tmp_path):
    invalid = tmp_path / "not-a-manifest.yaml"
    invalid.write_text("- not\n- a\n- mapping\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must contain a YAML mapping"):
        icc._load_yaml(invalid)

    pack = load_pack(COMPETENCY)
    question = pack.questions[0]

    missing_result = icc._semantic_scope({"results": []}, [question])
    assert missing_result["semantic_pass_rate"] == 0.0
    assert missing_result["semantic_gaps"] == [
        {
            "question_id": question.id,
            "kind": "missing-qualification-result",
            "missing": ["qualification-result"],
        }
    ]

    baseline = run_domain_onboarding(ROOT, MANIFEST, WORKFLOW, POLICY)["semantic_baseline"]
    baseline = deepcopy(baseline)
    result = next(item for item in baseline["results"] if item["id"] == question.id)
    result["capability_details"] = []
    result["status"] = "PARTIAL"
    result["missing"] = ["urn:test:missing-capability"]
    scoped = icc._semantic_scope(baseline, [question])
    assert scoped["missing_capabilities"]
    assert scoped["semantic_gaps"]

    no_runtime = icc._runtime_scope(None, {question.id})
    assert no_runtime["runtime_coverage_rate"] == 0.0
    assert no_runtime["runtime_gaps"] == [
        {"question_id": question.id, "status": "MISSING_RUNTIME_REPORT"}
    ]


def test_icc_persona_qualification_requires_explicit_persona(tmp_path):
    payload = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    payload.pop("persona_id", None)
    payload.pop("persona_binding", None)
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    report = icc.run_icc_persona_qualification(ROOT, manifest, WORKFLOW, POLICY)

    assert report["status"] == "BLOCKED"
    assert report["block_reason"] == "persona qualification requires an explicit persona_id"


def test_icc_persona_qualification_fails_closed_for_invalid_binding(tmp_path, monkeypatch):
    monkeypatch.setattr(
        icc,
        "load_persona_binding",
        lambda path: (_ for _ in ()).throw(ValueError("binding exploded")),
    )

    report = icc.run_icc_persona_qualification(ROOT, MANIFEST, WORKFLOW, POLICY)

    assert report["status"] == "BLOCKED"
    assert report["block_reason"] == "invalid persona capability binding: binding exploded"


def test_icc_persona_qualification_can_fallback_to_frozen_persona_tags(tmp_path):
    payload = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    payload.pop("persona_binding", None)
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    report = icc.run_icc_persona_qualification(ROOT, manifest, WORKFLOW, POLICY)

    assert report["status"] == "READY_FOR_HUMAN_REVIEW"
    assert report["persona_binding"]["selection_source"] == "competency-persona-tags"
    assert report["persona_binding"]["question_count"] == 2


def test_icc_persona_qualification_blocks_when_fallback_has_no_questions(tmp_path):
    payload = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    payload["persona_id"] = "chief-executive"
    payload.pop("persona_binding", None)
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    report = icc.run_icc_persona_qualification(ROOT, manifest, WORKFLOW, POLICY)

    assert report["status"] == "BLOCKED"
    assert "has no competency questions" in report["block_reason"]


def test_icc_persona_qualification_propagates_parent_domain_block(monkeypatch):
    monkeypatch.setattr(
        icc,
        "run_domain_onboarding",
        lambda *args, **kwargs: {"status": "BLOCKED", "block_reason": "parent failed"},
    )

    report = icc.run_icc_persona_qualification(ROOT, MANIFEST, WORKFLOW, POLICY)

    assert report["status"] == "BLOCKED"
    assert report["block_reason"] == "parent domain onboarding blocked: parent failed"


def test_icc_persona_qualification_fails_closed_for_unknown_persona():
    report = icc.run_icc_persona_qualification(
        ROOT,
        MANIFEST,
        WORKFLOW,
        POLICY,
        persona_id="not-a-real-persona",
    )

    assert report["status"] == "BLOCKED"
    assert report["current_state"] == "BLOCKED"
    assert "not declared in the scoped persona pack" in report["block_reason"]


def test_icc_persona_qualification_fails_closed_on_semantic_gap(monkeypatch):
    domain_report = run_domain_onboarding(ROOT, MANIFEST, WORKFLOW, POLICY)
    question_id = _rig_manager_question_id()
    mutated = deepcopy(domain_report)
    result = next(
        item for item in mutated["semantic_baseline"]["results"] if item["id"] == question_id
    )
    result["status"] = "PARTIAL"
    result["checks_passed"] = max(0, int(result["checks_total"]) - 1)
    result["missing"] = ["urn:test:persona-semantic-gap"]

    monkeypatch.setattr(icc, "run_domain_onboarding", lambda *args, **kwargs: mutated)
    report = icc.run_icc_persona_qualification(ROOT, MANIFEST, WORKFLOW, POLICY)

    assert report["status"] == "BLOCKED"
    assert report["icc_delta"]["new_semantic_candidates"]
    assert "persona semantic pass rate" in report["block_reason"]


def test_icc_persona_qualification_fails_closed_on_semantic_error(monkeypatch):
    domain_report = run_domain_onboarding(ROOT, MANIFEST, WORKFLOW, POLICY)
    question_id = _rig_manager_question_id()
    mutated = deepcopy(domain_report)
    result = next(
        item for item in mutated["semantic_baseline"]["results"] if item["id"] == question_id
    )
    result["status"] = "ERROR"

    monkeypatch.setattr(icc, "run_domain_onboarding", lambda *args, **kwargs: mutated)
    report = icc.run_icc_persona_qualification(ROOT, MANIFEST, WORKFLOW, POLICY)

    assert report["status"] == "BLOCKED"
    assert "persona semantic qualification contains ERROR results" in report["block_reason"]


def test_icc_persona_qualification_fails_closed_on_runtime_gap(monkeypatch):
    domain_report = run_domain_onboarding(ROOT, MANIFEST, WORKFLOW, POLICY)
    question_id = _rig_manager_question_id()
    mutated = deepcopy(domain_report)
    runtime_result = next(
        item
        for item in mutated["runtime_qualification"]["results"]
        if item["question_id"] == question_id
    )
    runtime_result["status"] = "FAIL"

    monkeypatch.setattr(icc, "run_domain_onboarding", lambda *args, **kwargs: mutated)
    report = icc.run_icc_persona_qualification(ROOT, MANIFEST, WORKFLOW, POLICY)

    assert report["status"] == "BLOCKED"
    assert report["icc_delta"]["runtime_gaps"]
    assert "persona runtime coverage rate" in report["block_reason"]
