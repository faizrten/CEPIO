"""Explicit persona-to-ICC question bindings.

Persona bindings are projections over a frozen competency pack. They do not modify the
canonical domain benchmark and therefore can express role-specific primary/oversight
coverage without creating persona-specific ontology semantics.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from .generalization import CompetencyPack, CompetencyQuestion


class PersonaQuestionBinding(BaseModel):
    question_id: str
    mode: Literal["primary", "oversight", "support"] = "oversight"
    rationale: str


class PersonaCapabilityBinding(BaseModel):
    id: str
    version: str
    domain: str
    persona_id: str
    competency_pack_id: str
    minimum_question_count: int = Field(default=1, ge=1)
    questions: list[PersonaQuestionBinding] = Field(min_length=1)


def load_persona_binding(path: Path) -> PersonaCapabilityBinding:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return PersonaCapabilityBinding.model_validate(raw)


def resolve_persona_questions(
    binding: PersonaCapabilityBinding,
    pack: CompetencyPack,
    *,
    domain: str,
    persona_id: str,
) -> tuple[list[CompetencyQuestion], list[dict[str, str]]]:
    if binding.domain != domain:
        raise ValueError(
            f"persona binding domain {binding.domain!r} does not match manifest domain {domain!r}"
        )
    if binding.persona_id != persona_id:
        raise ValueError(
            f"persona binding persona {binding.persona_id!r} does not match requested persona {persona_id!r}"
        )
    if binding.competency_pack_id != pack.id:
        raise ValueError(
            "persona binding competency_pack_id does not match the frozen domain competency pack"
        )

    ids = [item.question_id for item in binding.questions]
    if len(ids) != len(set(ids)):
        raise ValueError("persona binding contains duplicate question IDs")

    by_id = {question.id: question for question in pack.questions}
    unknown = sorted(set(ids) - set(by_id))
    if unknown:
        raise ValueError(f"persona binding references unknown competency questions: {unknown}")
    if len(ids) < binding.minimum_question_count:
        raise ValueError(
            f"persona binding covers {len(ids)} questions but requires at least {binding.minimum_question_count}"
        )

    questions = [by_id[question_id] for question_id in ids]
    metadata = [
        {
            "question_id": item.question_id,
            "mode": item.mode,
            "rationale": item.rationale,
        }
        for item in binding.questions
    ]
    return questions, metadata
