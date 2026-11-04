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


def create_readonly_harness(client, host: ReadOnlyCompositionHost):
    """Use the SDK Harness with only ACCC; no provider configuration or inference.

    The caller owns client/session lifetime and any inference authorization.
    Defaults that expose web, files, modes, tasks or additional tools are disabled.
    SDK approval handling remains enabled with no auto-approval rules.
    """
    from agent_framework import create_harness_agent

    return create_harness_agent(
        client,
        name="cepio-accc-readonly",
        tools=[composition_tool(host)],
        harness_instructions="Compose read-only CEPIO plans. READY is not execution authority.",
        disable_compaction=True,
        disable_todo=True,
        disable_mode=True,
        disable_file_memory=True,
        disable_web_search=True,
        auto_approval_rules=[],
    )
