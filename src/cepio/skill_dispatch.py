"""Host-only admission and deterministic dispatch; never an Operator tool."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Iterable, Literal, TypeVar

from .skill_preflight import SkillPreflightResult, SkillPreflightSpec, evaluate_skill_preflight
from .runtime import CEPIORuntime

T = TypeVar("T")


@dataclass(frozen=True)
class SkillCandidate:
    """Host-compiled contract. Static admission must come from the package binder."""

    skill_id: str
    static_status: Literal["BOUND", "BLOCKED"]
    spec: SkillPreflightSpec | None = None


@dataclass(frozen=True)
class SkillDispatchResult(Generic[T]):
    status: Literal["DISPATCHED", "NO_READY_SKILL", "NO_MATCH", "CONFLICT"]
    ready_ids: tuple[str, ...]
    matched_ids: tuple[str, ...]
    preflights: tuple[SkillPreflightResult, ...]
    output: T | None = None


def dispatch_skill(
    runtime: CEPIORuntime,
    candidates: Iterable[SkillCandidate],
    *,
    actor_id: str,
    actor_roles: set[str],
    matches: Callable[[str], bool],
    dispatch: Callable[[str], T],
) -> SkillDispatchResult[T]:
    """Recheck admission for this invocation before exposing IDs to trigger matching.

    Duplicate identities and malformed BOUND candidates are configuration errors.
    No ranking or registration order can resolve ambiguous matches. Callbacks are
    trusted host code; dispatch must construct the Operator with the same identity
    and runtime. READY does not assert instance evidence sufficiency.
    """
    ordered = sorted(candidates, key=lambda candidate: candidate.skill_id)
    if len({candidate.skill_id for candidate in ordered}) != len(ordered):
        raise ValueError("Duplicate Skill identity")
    for candidate in ordered:
        if candidate.static_status not in {"BOUND", "BLOCKED"}:
            raise ValueError("Unknown static admission status")
        if candidate.static_status == "BOUND" and (
            candidate.spec is None or candidate.spec.skill_id != candidate.skill_id
        ):
            raise ValueError("BOUND candidate requires an identity-matched resolved contract")
    roles = set(actor_roles)
    checks = tuple(
        evaluate_skill_preflight(
            runtime, candidate.spec, actor_id=actor_id, actor_roles=roles
        )
        for candidate in ordered
        if candidate.static_status == "BOUND" and candidate.spec is not None
    )
    ready = tuple(check.skill_id for check in checks if check.status == "READY")
    matched = tuple(skill_id for skill_id in ready if matches(skill_id))
    if not ready:
        status = "NO_READY_SKILL"
    elif not matched:
        status = "NO_MATCH"
    elif len(matched) > 1:
        status = "CONFLICT"
    else:
        return SkillDispatchResult("DISPATCHED", ready, matched, checks, dispatch(matched[0]))
    return SkillDispatchResult(status, ready, matched, checks)
