from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Protocol

import uvicorn
from fastapi import HTTPException
from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from ...auth import ActorContext as AuthActorContext
from ...auth import AuthSettings, EntraTokenValidator
from ...bootstrap import build_runtime_from_settings
from ...runtime import AuthorizationError, CEPIORuntime
from .foundry_gateway import ContextVarActorProvider, EntraClaimsMapper
from .foundry_mcp import MCPToolProfile, build_mcp_server_with_profile


class TokenValidator(Protocol):
    def validate(self, token: str) -> AuthActorContext: ...


def _json_map(name: str, *, required: bool = False) -> dict[str, str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        if required:
            raise RuntimeError(f"{name} is required")
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{name} must be valid JSON") from exc
    if not isinstance(value, dict) or not all(
        isinstance(key, str) and isinstance(item, str) for key, item in value.items()
    ):
        raise RuntimeError(f"{name} must be a JSON object mapping strings to strings")
    return dict(value)


def _csv(name: str, *, required: bool = False) -> list[str]:
    values = [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]
    if required and not values:
        raise RuntimeError(f"{name} is required")
    return values


class EntraMCPAuthMiddleware:
    """Bind verified Entra identity to the CEPIO MCP ContextVar actor boundary."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        token_validator: TokenValidator,
        claims_mapper: EntraClaimsMapper,
        actor_provider: ContextVarActorProvider,
        auth_mode: str = "agentic-identity",
    ) -> None:
        self.app = app
        self.token_validator = token_validator
        self.claims_mapper = claims_mapper
        self.actor_provider = actor_provider
        self.auth_mode = auth_mode

    async def _reject(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        *,
        status_code: int,
        code: str,
        message: str,
    ) -> None:
        headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
        response = JSONResponse(
            {"code": code, "message": message},
            status_code=status_code,
            headers=headers,
        )
        await response(scope, receive, send)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        authorization = Headers(scope=scope).get("authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            await self._reject(
                scope,
                receive,
                send,
                status_code=401,
                code="authentication_required",
                message="Bearer token is required",
            )
            return

        try:
            validated = self.token_validator.validate(token.strip())
            claims = validated.claims or {}
            actor = self.claims_mapper.map_claims(
                claims,
                principal_type="agent",
                auth_mode=self.auth_mode,  # type: ignore[arg-type]
            )
        except HTTPException as exc:
            await self._reject(
                scope,
                receive,
                send,
                status_code=exc.status_code,
                code="invalid_token",
                message="Access token validation failed",
            )
            return
        except AuthorizationError:
            await self._reject(
                scope,
                receive,
                send,
                status_code=403,
                code="forbidden",
                message="Authenticated principal has no mapped CEPIO authority",
            )
            return

        with self.actor_provider.bind(actor):
            await self.app(scope, receive, send)


def create_foundry_mcp_app(
    runtime: CEPIORuntime | None = None,
    *,
    token_validator: TokenValidator | None = None,
    role_map: Mapping[str, str] | None = None,
    group_role_map: Mapping[str, str] | None = None,
    allowed_hosts: list[str] | None = None,
    allowed_origins: list[str] | None = None,
    tool_profile: MCPToolProfile | None = None,
) -> ASGIApp:
    """Create the authenticated remote CEPIO MCP ASGI host used by Foundry G1."""

    try:
        from mcp.server.transport_security import TransportSecuritySettings
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Install CEPIO with the 'mcp' extra to host the MCP server") from exc

    runtime = runtime or build_runtime_from_settings()
    role_map = (
        dict(role_map)
        if role_map is not None
        else _json_map("CEPIO_MCP_ENTRA_ROLE_MAP", required=True)
    )
    group_role_map = (
        dict(group_role_map)
        if group_role_map is not None
        else _json_map("CEPIO_MCP_ENTRA_GROUP_ROLE_MAP")
    )
    allowed_hosts = allowed_hosts or _csv("CEPIO_MCP_ALLOWED_HOSTS", required=True)
    allowed_origins = allowed_origins or _csv("CEPIO_MCP_ALLOWED_ORIGINS")

    if tool_profile is None:
        raw_profile = os.getenv("CEPIO_MCP_TOOL_PROFILE", "recommendation-only").strip()
        if raw_profile == "full":
            selected_profile: MCPToolProfile = "full"
        elif raw_profile == "recommendation-only":
            selected_profile = "recommendation-only"
        else:
            raise RuntimeError(f"Unsupported CEPIO_MCP_TOOL_PROFILE: {raw_profile}")
    else:
        selected_profile = tool_profile

    actor_provider = ContextVarActorProvider()
    mapper = EntraClaimsMapper(
        role_map=role_map,
        group_role_map=group_role_map,
    )
    validator = token_validator or EntraTokenValidator(AuthSettings.from_env())
    mcp = build_mcp_server_with_profile(
        runtime,
        actor_provider,
        tool_profile=selected_profile,
    )
    security = TransportSecuritySettings(
        allowed_hosts=allowed_hosts,
        allowed_origins=allowed_origins,
    )
    mcp_app = mcp.streamable_http_app(
        stateless_http=True,
        json_response=True,
        transport_security=security,
    )
    return EntraMCPAuthMiddleware(
        mcp_app,
        token_validator=validator,
        claims_mapper=mapper,
        actor_provider=actor_provider,
    )


def main() -> None:
    port = int(os.getenv("PORT", os.getenv("CEPIO_MCP_PORT", "8000")))
    bind_host = os.getenv("CEPIO_MCP_BIND_HOST", "127.0.0.1").strip() or "127.0.0.1"
    app = create_foundry_mcp_app()
    uvicorn.run(app, host=bind_host, port=port)


if __name__ == "__main__":
    main()
