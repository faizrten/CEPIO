"""Local/development CEPIO MCP server.

This example uses a fixed development actor so the MCP protocol can be exercised
without Microsoft Foundry or Entra. Do not deploy this fixed-actor pattern to a
multi-user or production endpoint. Production hosting must bind verified Entra
claims to ContextVarActorProvider as documented in docs/foundry-mcp.md.
"""

from cepio.bootstrap import build_runtime
from cepio.integrations.microsoft.foundry_gateway import ActorContext, FixedActorProvider
from cepio.integrations.microsoft.foundry_mcp import build_mcp_server

runtime = build_runtime()
actor = ActorContext(
    subject_id="local-foundry-agent",
    roles={"ai_agent_recommender"},
    principal_type="agent",
    auth_mode="development",
)
mcp = build_mcp_server(runtime, FixedActorProvider(actor))


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000,
        stateless_http=True,
        json_response=True,
    )
