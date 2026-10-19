"""Authorized application service for CEPIO Enterprise Performance.

This boundary composes the versioned Performance Contract Registry, governed Business
Logic execution and deterministic Performance Runtime without granting mutation or
Kinetic action authority. Customer scope is resolved through an explicit tenant-to-
organization mapping; Entra tenant IDs are never assumed to equal CEPIO organization IDs.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from .auth import ActorContext
from .performance_business_logic import (
    BusinessLogicExecution,
    BusinessLogicExecutionError,
    BusinessLogicInvocation,
    BusinessLogicRegistry,
    PerformanceBusinessLogicRuntime,
)
from .performance_contract import PerformanceContract
from .performance_registry import (
    InMemoryPerformanceContractStore,
    PerformanceContractRegistry,
    PerformanceContractRegistryError,
    PerformanceContractRevisionRef,
    SQLitePerformanceContractStore,
)
from .performance_runtime import PerformanceEvaluation, PerformanceObservation, PerformanceRuntime
from .runtime import CEPIORuntime


class PerformanceServiceError(ValueError):
    def __init__(self, code: str, message: str, *, status_code: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class PerformanceAccessPolicy:
    """Explicit host mapping from identity tenant to CEPIO customer organizations."""

    def __init__(self, tenant_organizations: dict[str, set[str]] | None = None) -> None:
        self.tenant_organizations = {
            str(tenant): {str(org) for org in organizations}
            for tenant, organizations in (tenant_organizations or {}).items()
        }

    @classmethod
    def from_env(cls) -> "PerformanceAccessPolicy":
        raw = os.getenv("CEPIO_TENANT_ORGANIZATION_MAP", "{}").strip() or "{}"
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("CEPIO_TENANT_ORGANIZATION_MAP must be valid JSON") from exc
        if not isinstance(parsed, dict):
            raise RuntimeError("CEPIO_TENANT_ORGANIZATION_MAP must be a JSON object")
        normalized: dict[str, set[str]] = {}
        for tenant, organizations in parsed.items():
            if not isinstance(organizations, list) or not all(
                isinstance(value, str) and value for value in organizations
            ):
                raise RuntimeError(
                    "CEPIO_TENANT_ORGANIZATION_MAP values must be arrays of non-empty strings"
                )
            normalized[str(tenant)] = set(organizations)
        return cls(normalized)

    def require_organization(self, actor: ActorContext, organization_id: str) -> None:
        tenant_id = actor.tenant_id
        if tenant_id is None:
            raise PerformanceServiceError(
                "PERFORMANCE_TENANT_REQUIRED",
                "Authenticated identity does not contain a tenant scope",
                status_code=403,
            )
        permitted = self.tenant_organizations.get(tenant_id, set())
        if organization_id not in permitted:
            raise PerformanceServiceError(
                "PERFORMANCE_ORGANIZATION_FORBIDDEN",
                f"Tenant {tenant_id!r} is not mapped to CEPIO organization {organization_id!r}",
                status_code=403,
            )


class PerformanceContractView(BaseModel):
    model_config = ConfigDict(frozen=True)

    contract: PerformanceContract
    source_revisions: tuple[PerformanceContractRevisionRef, ...]


class PerformanceEvaluationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    observations: tuple[PerformanceObservation, ...] = ()
    business_logic: tuple[BusinessLogicInvocation, ...] = ()
    evaluated_at: datetime | None = None


class PerformanceEvaluationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    contract_id: str
    contract_version: str
    source_revisions: tuple[PerformanceContractRevisionRef, ...]
    business_logic_executions: tuple[BusinessLogicExecution, ...]
    evaluation: PerformanceEvaluation


class PerformanceService:
    """Read/evaluate service. Registry and logic mutation remain control-plane concerns."""

    def __init__(
        self,
        runtime: CEPIORuntime,
        registry: PerformanceContractRegistry,
        *,
        access_policy: PerformanceAccessPolicy,
        business_logic_registry: BusinessLogicRegistry | None = None,
        evaluator: PerformanceRuntime | None = None,
    ) -> None:
        self.runtime = runtime
        self.registry = registry
        self.access_policy = access_policy
        self.business_logic_registry = business_logic_registry or BusinessLogicRegistry()
        self.business_logic_runtime = PerformanceBusinessLogicRuntime(
            runtime, self.business_logic_registry
        )
        self.evaluator = evaluator or PerformanceRuntime()

    def resolve(
        self,
        actor: ActorContext,
        organization_id: str,
        contract_id: str,
        *,
        version: str | None = None,
    ) -> PerformanceContractView:
        self._authorize_read(actor, organization_id)
        try:
            resolved = self.registry.resolve(
                contract_id,
                version,
                organization_id=organization_id,
            )
        except PerformanceContractRegistryError as exc:
            raise _registry_service_error(exc) from exc
        return PerformanceContractView(
            contract=resolved.resolved.contract,
            source_revisions=resolved.source_revisions,
        )

    def evaluate(
        self,
        actor: ActorContext,
        organization_id: str,
        contract_id: str,
        request: PerformanceEvaluationRequest,
        *,
        version: str | None = None,
    ) -> PerformanceEvaluationResponse:
        view = self.resolve(actor, organization_id, contract_id, version=version)
        direct_node_ids = {observation.node_id for observation in request.observations}
        formula_node_ids = {invocation.node_id for invocation in request.business_logic}
        conflicts = sorted(direct_node_ids.intersection(formula_node_ids))
        if conflicts:
            raise PerformanceServiceError(
                "PERFORMANCE_OBSERVATION_SOURCE_CONFLICT",
                f"Nodes cannot receive direct and Business Logic observations in one evaluation: {conflicts}",
            )

        materialized = []
        for invocation in request.business_logic:
            self._authorize_formula(actor, view.contract, invocation)
            try:
                materialized.append(
                    self.business_logic_runtime.materialize(
                        view.contract,
                        invocation.node_id,
                        invocation.inputs,
                        evaluated_at=request.evaluated_at,
                    )
                )
            except BusinessLogicExecutionError as exc:
                raise PerformanceServiceError(
                    exc.code,
                    str(exc),
                    status_code=422,
                ) from exc

        observations = tuple(request.observations) + tuple(
            result.observation for result in materialized
        )
        try:
            evaluation = self.evaluator.evaluate(
                view.contract,
                observations,
                evaluated_at=request.evaluated_at,
            )
        except ValueError as exc:
            raise PerformanceServiceError(
                "PERFORMANCE_EVALUATION_INVALID",
                str(exc),
            ) from exc
        return PerformanceEvaluationResponse(
            contract_id=view.contract.id,
            contract_version=view.contract.version,
            source_revisions=view.source_revisions,
            business_logic_executions=tuple(result.execution for result in materialized),
            evaluation=evaluation,
        )

    def _authorize_read(self, actor: ActorContext, organization_id: str) -> None:
        self.access_policy.require_organization(actor, organization_id)
        if not self.runtime.policy_engine.can_read_type(actor.roles, "KPI"):
            raise PerformanceServiceError(
                "PERFORMANCE_READ_FORBIDDEN",
                "Actor roles are not authorized to read enterprise performance",
                status_code=403,
            )

    def _authorize_formula(
        self,
        actor: ActorContext,
        contract: PerformanceContract,
        invocation: BusinessLogicInvocation,
    ) -> None:
        node = next(
            (candidate for candidate in contract.nodes if candidate.id == invocation.node_id),
            None,
        )
        if node is None:
            raise PerformanceServiceError(
                "NODE_NOT_FOUND",
                f"Performance node not found: {invocation.node_id}",
            )
        if node.formula_ref is None:
            raise PerformanceServiceError(
                "FORMULA_REF_REQUIRED",
                f"Performance node does not declare formula_ref: {invocation.node_id}",
            )
        try:
            definition = self.business_logic_registry.get(node.formula_ref).definition
        except BusinessLogicExecutionError as exc:
            raise PerformanceServiceError(exc.code, str(exc)) from exc
        if not self.runtime.policy_engine.can_call_function(actor.roles, definition.function_name):
            raise PerformanceServiceError(
                "PERFORMANCE_FUNCTION_FORBIDDEN",
                f"Actor roles are not authorized to call function {definition.function_name}",
                status_code=403,
            )


def build_performance_service(
    runtime: CEPIORuntime,
    *,
    registry: PerformanceContractRegistry | None = None,
    business_logic_registry: BusinessLogicRegistry | None = None,
    access_policy: PerformanceAccessPolicy | None = None,
) -> PerformanceService:
    if registry is None:
        path = os.getenv("CEPIO_PERFORMANCE_REGISTRY_PATH")
        if path:
            store = SQLitePerformanceContractStore(Path(path))
        else:
            store = InMemoryPerformanceContractStore()
        registry = PerformanceContractRegistry(store)
    return PerformanceService(
        runtime,
        registry,
        access_policy=access_policy or PerformanceAccessPolicy.from_env(),
        business_logic_registry=business_logic_registry,
    )


def _registry_service_error(exc: PerformanceContractRegistryError) -> PerformanceServiceError:
    not_found = {
        "REVISION_NOT_FOUND",
        "ACTIVE_REVISION_NOT_FOUND",
        "PINNED_PARENT_NOT_FOUND",
    }
    status_code = 404 if exc.code in not_found else 422
    return PerformanceServiceError(exc.code, str(exc), status_code=status_code)
