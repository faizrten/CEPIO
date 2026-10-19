"""Governed Business Logic execution for CEPIO Performance Contracts.

Performance nodes reference immutable Business Logic definitions through ``formula_ref``.
This runtime never evaluates arbitrary expressions or code. It dispatches only to functions
that are already registered with a trusted CEPIO function runtime, then materializes the
result as a normal evidence-backed ``PerformanceObservation``.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .performance_contract import PerformanceContract
from .performance_runtime import PerformanceObservation


class TrustedFunctionRuntime(Protocol):
    """Small boundary implemented by ``CEPIORuntime``."""

    def has_function(self, name: str) -> bool: ...

    def call_function(self, name: str, **kwargs: Any) -> Any: ...


class BusinessLogicDefinition(BaseModel):
    """Immutable executable definition addressed by an exact ``formula_ref``."""

    model_config = ConfigDict(frozen=True)

    formula_ref: str
    name: str
    function_name: str
    input_names: tuple[str, ...] = Field(min_length=1)
    organization_id: str | None = None
    output_path: str | None = None
    output_unit: str | None = None
    max_input_age_seconds: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_definition(self) -> "BusinessLogicDefinition":
        if not self.formula_ref:
            raise ValueError("business logic formula_ref is required")
        if not self.function_name:
            raise ValueError("business logic function_name is required")
        if len(self.input_names) != len(set(self.input_names)):
            raise ValueError("business logic input_names must be unique")
        if any(not name for name in self.input_names):
            raise ValueError("business logic input names cannot be empty")
        if self.output_path is not None and any(
            not segment for segment in self.output_path.split(".")
        ):
            raise ValueError("business logic output_path must contain non-empty segments")
        return self


class RegisteredBusinessLogicDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    definition: BusinessLogicDefinition
    definition_hash: str


class BusinessLogicInput(BaseModel):
    """One evidence-backed input value supplied to a governed formula."""

    model_config = ConfigDict(frozen=True)

    name: str
    value: Any
    observed_at: datetime
    evidence_refs: tuple[str, ...] = Field(min_length=1)


class BusinessLogicInputLineage(BaseModel):
    """Audit-safe lineage; intentionally excludes the source value itself."""

    model_config = ConfigDict(frozen=True)

    name: str
    observed_at: datetime
    evidence_refs: tuple[str, ...]


class BusinessLogicExecution(BaseModel):
    model_config = ConfigDict(frozen=True)

    formula_ref: str
    definition_hash: str
    function_name: str
    organization_id: str | None = None
    evaluated_at: datetime
    effective_observed_at: datetime
    value: float
    unit: str | None = None
    evidence_refs: tuple[str, ...]
    inputs: tuple[BusinessLogicInputLineage, ...]


class MaterializedPerformanceObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    observation: PerformanceObservation
    execution: BusinessLogicExecution


class BusinessLogicInvocation(BaseModel):
    model_config = ConfigDict(frozen=True)

    node_id: str
    inputs: tuple[BusinessLogicInput, ...] = Field(min_length=1)


class BusinessLogicExecutionError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class BusinessLogicRegistry:
    """Immutable exact-reference registry for governed Business Logic definitions."""

    def __init__(self) -> None:
        self._definitions: dict[str, RegisteredBusinessLogicDefinition] = {}

    def register(self, definition: BusinessLogicDefinition) -> RegisteredBusinessLogicDefinition:
        if definition.formula_ref in self._definitions:
            raise BusinessLogicExecutionError(
                "FORMULA_ALREADY_REGISTERED",
                f"Business Logic definition already registered: {definition.formula_ref}",
            )
        registered = RegisteredBusinessLogicDefinition(
            definition=definition,
            definition_hash=_definition_hash(definition),
        )
        self._definitions[definition.formula_ref] = registered
        return registered

    def get(self, formula_ref: str) -> RegisteredBusinessLogicDefinition:
        registered = self._definitions.get(formula_ref)
        if registered is None:
            raise BusinessLogicExecutionError(
                "FORMULA_NOT_FOUND",
                f"Business Logic definition is not registered: {formula_ref}",
            )
        return registered


class PerformanceBusinessLogicRuntime:
    """Materialize formula-backed nodes without bypassing Performance Runtime semantics."""

    def __init__(
        self,
        function_runtime: TrustedFunctionRuntime,
        registry: BusinessLogicRegistry,
    ) -> None:
        self.function_runtime = function_runtime
        self.registry = registry

    def materialize(
        self,
        contract: PerformanceContract,
        node_id: str,
        inputs: tuple[BusinessLogicInput, ...] | list[BusinessLogicInput],
        *,
        evaluated_at: datetime | None = None,
    ) -> MaterializedPerformanceObservation:
        now = evaluated_at or datetime.now(timezone.utc)
        if now.tzinfo is None:
            raise BusinessLogicExecutionError(
                "NAIVE_EVALUATION_TIME", "Business Logic evaluated_at must be timezone-aware"
            )

        node = next((candidate for candidate in contract.nodes if candidate.id == node_id), None)
        if node is None:
            raise BusinessLogicExecutionError(
                "NODE_NOT_FOUND", f"Performance node not found: {node_id}"
            )
        if node.formula_ref is None:
            raise BusinessLogicExecutionError(
                "FORMULA_REF_REQUIRED",
                f"Performance node does not declare formula_ref: {node_id}",
            )

        registered = self.registry.get(node.formula_ref)
        definition = registered.definition
        if (
            definition.organization_id is not None
            and definition.organization_id != contract.organization_id
        ):
            raise BusinessLogicExecutionError(
                "ORGANIZATION_SCOPE_MISMATCH",
                f"Business Logic {definition.formula_ref} is scoped to "
                f"{definition.organization_id!r}, not {contract.organization_id!r}",
            )
        if (
            definition.output_unit is not None
            and node.unit is not None
            and definition.output_unit != node.unit
        ):
            raise BusinessLogicExecutionError(
                "OUTPUT_UNIT_MISMATCH",
                f"Business Logic unit {definition.output_unit!r} does not match node unit {node.unit!r}",
            )
        if not self.function_runtime.has_function(definition.function_name):
            raise BusinessLogicExecutionError(
                "TRUSTED_FUNCTION_NOT_REGISTERED",
                f"Trusted CEPIO function is not registered: {definition.function_name}",
            )

        supplied = tuple(inputs)
        names = [item.name for item in supplied]
        if len(names) != len(set(names)):
            raise BusinessLogicExecutionError(
                "DUPLICATE_INPUT", "Business Logic input names must be unique per invocation"
            )
        expected = set(definition.input_names)
        actual = set(names)
        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            raise BusinessLogicExecutionError(
                "INPUT_CONTRACT_MISMATCH",
                f"Business Logic input mismatch; missing={missing}, extra={extra}",
            )

        for item in supplied:
            if item.observed_at.tzinfo is None:
                raise BusinessLogicExecutionError(
                    "NAIVE_INPUT_TIME",
                    f"Business Logic input timestamp must be timezone-aware: {item.name}",
                )
            if item.observed_at > now:
                raise BusinessLogicExecutionError(
                    "FUTURE_INPUT",
                    f"Business Logic input is from the future: {item.name}",
                )
            if definition.max_input_age_seconds is not None:
                age = (now - item.observed_at).total_seconds()
                if age > definition.max_input_age_seconds:
                    raise BusinessLogicExecutionError(
                        "STALE_INPUT",
                        f"Business Logic input is stale: {item.name}",
                    )

        kwargs = {item.name: item.value for item in supplied}
        try:
            raw_output = self.function_runtime.call_function(definition.function_name, **kwargs)
        except Exception as exc:
            raise BusinessLogicExecutionError(
                "FUNCTION_EXECUTION_FAILED",
                f"Trusted CEPIO function failed: {definition.function_name}: {exc}",
            ) from exc

        selected = _select_output(raw_output, definition.output_path)
        if isinstance(selected, bool) or not isinstance(selected, (int, float)):
            raise BusinessLogicExecutionError(
                "NON_NUMERIC_OUTPUT",
                f"Business Logic output is not numeric: {definition.formula_ref}",
            )
        value = float(selected)
        if not math.isfinite(value):
            raise BusinessLogicExecutionError(
                "NON_FINITE_OUTPUT",
                f"Business Logic output must be finite: {definition.formula_ref}",
            )

        # The derived observation is no fresher than its oldest required input.
        effective_observed_at = min(item.observed_at for item in supplied)
        evidence_refs = tuple(sorted({ref for item in supplied for ref in item.evidence_refs}))
        lineage = tuple(
            BusinessLogicInputLineage(
                name=item.name,
                observed_at=item.observed_at,
                evidence_refs=item.evidence_refs,
            )
            for item in sorted(supplied, key=lambda value: value.name)
        )
        execution = BusinessLogicExecution(
            formula_ref=definition.formula_ref,
            definition_hash=registered.definition_hash,
            function_name=definition.function_name,
            organization_id=definition.organization_id,
            evaluated_at=now,
            effective_observed_at=effective_observed_at,
            value=value,
            unit=definition.output_unit,
            evidence_refs=evidence_refs,
            inputs=lineage,
        )
        observation = PerformanceObservation(
            node_id=node_id,
            value=value,
            observed_at=effective_observed_at,
            evidence_refs=evidence_refs,
        )
        return MaterializedPerformanceObservation(observation=observation, execution=execution)

    def materialize_many(
        self,
        contract: PerformanceContract,
        invocations: tuple[BusinessLogicInvocation, ...] | list[BusinessLogicInvocation],
        *,
        evaluated_at: datetime | None = None,
    ) -> tuple[MaterializedPerformanceObservation, ...]:
        requested = tuple(invocations)
        node_ids = [item.node_id for item in requested]
        if len(node_ids) != len(set(node_ids)):
            raise BusinessLogicExecutionError(
                "DUPLICATE_NODE_INVOCATION",
                "Each performance node may be materialized only once per batch",
            )
        return tuple(
            self.materialize(
                contract,
                item.node_id,
                item.inputs,
                evaluated_at=evaluated_at,
            )
            for item in requested
        )


def _definition_hash(definition: BusinessLogicDefinition) -> str:
    payload = json.dumps(
        definition.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _select_output(raw_output: Any, output_path: str | None) -> Any:
    if output_path is None:
        return raw_output
    current = raw_output.model_dump() if isinstance(raw_output, BaseModel) else raw_output
    for segment in output_path.split("."):
        if not isinstance(current, Mapping) or segment not in current:
            raise BusinessLogicExecutionError(
                "OUTPUT_PATH_NOT_FOUND",
                f"Business Logic output path not found: {output_path}",
            )
        current = current[segment]
    return current
