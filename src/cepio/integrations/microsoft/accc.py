"""Optional Microsoft Agent Framework tool; no agent loop or provider client."""

from __future__ import annotations

from typing import Protocol

from ...accc_readonly import CompositionPlan, CompositionRequest


class ReadOnlyCompositionHost(Protocol):
    def compose(self, request: CompositionRequest) -> CompositionPlan: ...


def composition_tool(host: ReadOnlyCompositionHost):
    """Bind one host-owned composition tool. Never install generic harness tools.

    Import is lazy: CEPIO Core does not require the Microsoft SDK. The embedding
    host supplies request-local authentication; do not capture a user's identity
    in a shared singleton. The tool schema contains no identity or authority.
    """
    from agent_framework import tool

    def invoke(**arguments) -> str:
        request = CompositionRequest.model_validate(arguments)
        return host.compose(request).model_dump_json()

    return tool(
        invoke,
        name="cepio_compose_context_and_competence",
        description="Compose a read-only CEPIO plan. READY never authorizes execution.",
        schema=CompositionRequest,
        approval_mode="always_require",
    )
