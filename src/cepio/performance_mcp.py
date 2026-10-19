"""Opt-in MCP adapter for CEPIO Enterprise Performance."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .mcp import MCPFacade
from .performance_runtime import PerformanceObservation
from .performance_service import PerformanceService
from .runtime import AuthorizationError, CEPIORuntime


class PerformanceMCPFacade(MCPFacade):
    """Extend the stable MCP facade with tenant-scoped performance tools."""

    def __init__(
        self,
        runtime: CEPIORuntime,
        *,
        actor_id: str,
        actor_roles: set[str],
        tenant_id: str | None,
        performance_service: PerformanceService,
    ) -> None:
        super().__init__(runtime, actor_id=actor_id, actor_roles=actor_roles)
        self.tenant_id = tenant_id
        self.performance_service = performance_service

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            *super().list_tools(),
            {
                "name": "cepio_resolve_performance_contract",
                "description": (
                    "Resolve an authorized active or version-pinned CEPIO Performance Contract"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "contract_id": {"type": "string"},
                        "version": {"type": ["string", "null"]},
                    },
                    "required": ["contract_id"],
                },
            },
            {
                "name": "cepio_evaluate_performance",
                "description": (
                    "Evaluate evidence-backed enterprise performance and return "
                    "explainable deviations plus recommend-only workflow candidates"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "contract_id": {"type": "string"},
                        "version": {"type": ["string", "null"]},
                        "observations": {
                            "type": "array",
                            "items": {"type": "object"},
                        },
                        "evaluated_at": {"type": ["string", "null"]},
                    },
                    "required": ["contract_id", "observations"],
                },
            },
        ]

    def _authorize_performance_scope(self, organization_id: str | None) -> None:
        if organization_id is None:
            return
        if self.tenant_id != organization_id:
            raise AuthorizationError(
                "Performance contract is outside the authenticated tenant boundary"
            )

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "cepio_resolve_performance_contract":
            resolution = self.performance_service.resolve(
                str(arguments["contract_id"]), arguments.get("version")
            )
            self._authorize_performance_scope(resolution.resolved.contract.organization_id)
            return resolution.model_dump(mode="json")

        if name == "cepio_evaluate_performance":
            contract_id = str(arguments["contract_id"])
            resolution = self.performance_service.resolve(contract_id, arguments.get("version"))
            self._authorize_performance_scope(resolution.resolved.contract.organization_id)
            observations = tuple(
                PerformanceObservation.model_validate(item)
                for item in arguments.get("observations", ())
            )
            evaluated_at = arguments.get("evaluated_at")
            if isinstance(evaluated_at, str):
                evaluated_at = datetime.fromisoformat(evaluated_at)
            assessment = self.performance_service.evaluate(
                contract_id,
                observations,
                version=resolution.resolved.contract.version,
                evaluated_at=evaluated_at,
            )
            return assessment.model_dump(mode="json")

        return super().call_tool(name, arguments)
