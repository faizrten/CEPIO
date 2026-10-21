from __future__ import annotations

import os
from typing import Any, Literal

from fastapi import HTTPException, status
from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from ...auth import AuthSettings, EntraTokenValidator
from ...application_contract import CEPIOApplicationService
from ...runtime import CEPIORuntime
from .foundry_gateway import ActorContext, ContextVarActorProvider
from .foundry_mcp import build_mcp_server, build_mcp_server_with_application_service


def _csv_env(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _transport_security():
    """Build explicit Streamable HTTP host/origin protection for deployed MCP.

    Azure App Service publishes its canonical hostname in WEBSITE_HOSTNAME. Other
    hosts must be declared explicitly with CEPIO_MCP_ALLOWED_HOSTS. Local/test
    hosts remain available so the same composition can be qualified offline.
    """

    try:
        from mcp.server.transport_security import TransportSecuritySettings
    except ImportError as exc:  # pragma: no cover - hosting dependency guard
        raise RuntimeError("Install CEPIO with the 'mcp' extra to host /mcp") from exc

    configured_hosts = _csv_env("CEPIO_MCP_ALLOWED_HOSTS")
    website_hostname = os.getenv("WEBSITE_HOSTNAME", "").strip()
    allowed_hosts = configured_hosts or [
        "127.0.0.1",
        "127.0.0.1:*",
        "localhost",
        "localhost:*",
        "testserver",
        "testserver:*",
    ]
    if website_hostname:
        for value in (website_hostname, f"{website_hostname}:*"):
            if value not in allowed_hosts:
                allowed_hosts.append(value)

    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=_csv_env("CEPIO_MCP_ALLOWED_ORIGINS"),
    )


def _http_exception(status_code: int, code: str, message: str) -> HTTPException:
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
        headers=headers,
    )


def actor_from_headers(headers: Headers) -> ActorContext:
    """Authenticate one MCP HTTP request and return governed CEPIO actor context.

    This intentionally reuses CEPIO's REST bearer-token validator. MCP tool callers
    never provide actor identity or roles as tool arguments.
    """

    settings = AuthSettings.from_env()
    if settings.mode == "dev":
        actor_id = headers.get("X-CEPIO-Dev-Actor", "dev-user")
        roles = {
            role.strip() for role in headers.get("X-CEPIO-Dev-Roles", "").split(",") if role.strip()
        }
        if not roles:
            raise _http_exception(
                status.HTTP_403_FORBIDDEN,
                "mcp_role_required",
                "Authenticated MCP actor has no CEPIO role",
            )
        return ActorContext(
            subject_id=actor_id,
            roles=roles,
            principal_type="user",
            auth_mode="development",
            tenant_id="dev",
        )

    if settings.mode != "entra":
        raise RuntimeError(f"Unsupported CEPIO_AUTH_MODE: {settings.mode}")

    authorization = headers.get("Authorization", "").strip()
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token.strip():
        raise _http_exception(
            status.HTTP_401_UNAUTHORIZED,
            "authentication_required",
            "Bearer token is required",
        )

    validated = EntraTokenValidator(settings).validate(token.strip())
    if not validated.roles:
        raise _http_exception(
            status.HTTP_403_FORBIDDEN,
            "mcp_role_required",
            "Authenticated MCP actor has no CEPIO role",
        )

    claims: dict[str, Any] = validated.claims or {}
    application_identity = claims.get("idtyp") == "app" or (
        bool(claims.get("roles")) and not bool(claims.get("scp"))
    )
    return ActorContext(
        subject_id=validated.actor_id,
        roles=set(validated.roles),
        principal_type="service" if application_identity else "user",
        auth_mode="agentic-identity" if application_identity else "oauth2",
        tenant_id=validated.tenant_id,
        client_id=claims.get("azp") or claims.get("appid"),
    )


class MCPActorBindingMiddleware:
    """Bind one verified HTTP principal to the ContextVar-backed MCP gateway."""

    def __init__(self, app: ASGIApp, actor_provider: ContextVarActorProvider) -> None:
        self.app = app
        self.actor_provider = actor_provider

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        try:
            actor = actor_from_headers(Headers(scope=scope))
        except HTTPException as exc:
            response = JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=exc.headers,
            )
            await response(scope, receive, send)
            return

        with self.actor_provider.bind(actor):
            await self.app(scope, receive, send)


def build_hosted_mcp(runtime: CEPIORuntime):
    """Build CEPIO's authenticated Streamable HTTP MCP surface.

    The returned MCP server owns the session manager; the outer host application
    must enter ``server.session_manager.run()`` in its lifespan before serving.
    """

    return _build_hosted_mcp(runtime)


def build_hosted_mcp_with_application_service(
    application_service: CEPIOApplicationService,
    *,
    tool_profile: Literal["g1", "full"] = "g1",
):
    """Externally compose protected Skills into authenticated hosted MCP.

    The deployer retains control of identity/authentication middleware and the
    session-manager lifecycle. G1 defaults to the six investigation tools.
    """
    if not isinstance(application_service, CEPIOApplicationService):
        raise TypeError("Expected CEPIOApplicationService")
    return _build_hosted_mcp(application_service.runtime, application_service, tool_profile)


def _build_hosted_mcp(
    runtime: CEPIORuntime,
    application_service: CEPIOApplicationService | None = None,
    tool_profile: Literal["g1", "full"] = "g1",
):
    actor_provider = ContextVarActorProvider()
    if application_service is None:
        server = build_mcp_server(runtime, actor_provider)
    else:
        server = build_mcp_server_with_application_service(
            application_service, actor_provider, tool_profile=tool_profile
        )
    http_app = server.streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        transport_security=_transport_security(),
    )
    return server, MCPActorBindingMiddleware(http_app, actor_provider)
