from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import api as legacy
from .integrations.microsoft.hosted_mcp import build_hosted_mcp
from .management_remote import build_remote_management_router
from .management_runtime import build_management_service
from .public_api import app


# The hosted CEPIO process exposes three deliberately separate protocol surfaces:
# - /api/v1/*: Application Contract for industrial applications and SDK clients;
# - /management/v1/*: authenticated, read-only Management Contract projection;
# - /mcp: authenticated Streamable HTTP MCP projection for agents/Copilot/Foundry.
#
# All three surfaces converge on the same runtime, policy engine and industrial
# capability contracts. The standalone `cepio-management` process remains
# loopback-only and remote management mutation remains intentionally absent.
_management_service = build_management_service(legacy.runtime)
app.include_router(build_remote_management_router(_management_service))

_mcp_server, _mcp_http_app = build_hosted_mcp(legacy.runtime)
_previous_lifespan = app.router.lifespan_context


@asynccontextmanager
async def _hosted_lifespan(host_app: FastAPI) -> AsyncIterator[None]:
    # Mounted Starlette sub-app lifespans are not started by the parent. Preserve
    # the existing FastAPI lifespan and explicitly own the MCP session manager.
    async with _previous_lifespan(host_app):
        async with _mcp_server.session_manager.run():
            yield


app.router.lifespan_context = _hosted_lifespan

# Mount at the root *after* all explicit REST and management routes. The MCP child
# app owns `/mcp`, while existing FastAPI routes continue to win by route order.
app.mount("/", _mcp_http_app, name="cepio-mcp")
