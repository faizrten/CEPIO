from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

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


class _RestartSafeMCPMount:
    """Stable ASGI mount whose MCP transport is recreated for each host lifespan.

    MCP's StreamableHTTPSessionManager is deliberately single-use. A production
    process normally has one lifespan, but application hosts and tests may start
    and stop the same FastAPI app more than once. Rebuilding the protocol transport
    per lifespan preserves that SDK invariant without making the CEPIO host
    single-start-only.
    """

    def __init__(self) -> None:
        self.current_app: ASGIApp | None = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self.current_app is None:
            response = JSONResponse(
                status_code=503,
                content={
                    "detail": {
                        "code": "mcp_not_ready",
                        "message": "CEPIO MCP transport is not running",
                    }
                },
            )
            await response(scope, receive, send)
            return
        await self.current_app(scope, receive, send)


_mcp_mount = _RestartSafeMCPMount()
_previous_lifespan = app.router.lifespan_context


@asynccontextmanager
async def _hosted_lifespan(host_app: FastAPI) -> AsyncIterator[None]:
    # Mounted Starlette sub-app lifespans are not started by the parent. Build a
    # fresh MCP server for every parent lifespan because the official MCP session
    # manager is intentionally single-use and cannot be restarted after shutdown.
    mcp_server, mcp_http_app = build_hosted_mcp(legacy.runtime)
    _mcp_mount.current_app = mcp_http_app
    try:
        async with _previous_lifespan(host_app):
            async with mcp_server.session_manager.run():
                yield
    finally:
        _mcp_mount.current_app = None


app.router.lifespan_context = _hosted_lifespan

# Mount at the root *after* all explicit REST and management routes. The MCP child
# app owns `/mcp`, while existing FastAPI routes continue to win by route order.
app.mount("/", _mcp_mount, name="cepio-mcp")
