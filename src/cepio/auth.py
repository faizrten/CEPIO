from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class ActorContext:
    actor_id: str
    roles: set[str]
    tenant_id: str | None = None
    claims: dict[str, Any] | None = None


@dataclass(frozen=True)
class AuthSettings:
    mode: str
    environment: str
    tenant_id: str | None
    audience: str | None
    issuer: str | None
    jwks_uri: str | None
    group_role_map: dict[str, list[str]]

    @classmethod
    def from_env(cls) -> "AuthSettings":
        environment = os.getenv("CEPIO_ENVIRONMENT", "production").strip().lower()
        mode = os.getenv("CEPIO_AUTH_MODE", "entra").strip().lower()
        tenant_id = os.getenv("CEPIO_ENTRA_TENANT_ID") or None
        audience = os.getenv("CEPIO_ENTRA_AUDIENCE") or None
        issuer = os.getenv("CEPIO_ENTRA_ISSUER") or None
        jwks_uri = os.getenv("CEPIO_ENTRA_JWKS_URI") or None
        raw_mapping = os.getenv("CEPIO_GROUP_ROLE_MAP", "{}")
        try:
            group_role_map = json.loads(raw_mapping)
        except json.JSONDecodeError as exc:
            raise RuntimeError("CEPIO_GROUP_ROLE_MAP must be valid JSON") from exc
        if not isinstance(group_role_map, dict):
            raise RuntimeError("CEPIO_GROUP_ROLE_MAP must be a JSON object")
        normalized = {
            str(group): [str(role) for role in roles]
            for group, roles in group_role_map.items()
            if isinstance(roles, list)
        }
        if mode == "dev" and environment not in {"development", "test"}:
            raise RuntimeError(
                "CEPIO_AUTH_MODE=dev is permitted only when CEPIO_ENVIRONMENT is development or test"
            )
        return cls(
            mode=mode,
            environment=environment,
            tenant_id=tenant_id,
            audience=audience,
            issuer=issuer,
            jwks_uri=jwks_uri,
            group_role_map=normalized,
        )

    def resolved_issuer(self) -> str:
        if self.issuer:
            return self.issuer
        if not self.tenant_id:
            raise RuntimeError("CEPIO_ENTRA_TENANT_ID or CEPIO_ENTRA_ISSUER is required")
        return f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"

    def resolved_jwks_uri(self) -> str:
        if self.jwks_uri:
            return self.jwks_uri
        if not self.tenant_id:
            raise RuntimeError("CEPIO_ENTRA_TENANT_ID or CEPIO_ENTRA_JWKS_URI is required")
        return f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"


class EntraTokenValidator:
    def __init__(self, settings: AuthSettings) -> None:
        self.settings = settings

    def validate(self, token: str) -> ActorContext:
        if not self.settings.audience:
            raise RuntimeError("CEPIO_ENTRA_AUDIENCE is required for Entra authentication")
        jwks_client = jwt.PyJWKClient(self.settings.resolved_jwks_uri())
        try:
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.settings.audience,
                issuer=self.settings.resolved_issuer(),
                options={"require": ["exp", "iat"]},
            )
            # Issuer and audience validation do not independently constrain tid,
            # including when a custom issuer/JWKS binding is configured.
            if self.settings.tenant_id and claims.get("tid") != self.settings.tenant_id:
                raise jwt.InvalidTokenError("Tenant claim does not match configured tenant")
        except jwt.PyJWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "invalid_token", "message": "Access token validation failed"},
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        actor_id = claims.get("oid") or claims.get("sub")
        if not actor_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "invalid_token", "message": "Token is missing an actor identifier"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        roles = {str(role) for role in claims.get("roles", [])}
        for group in claims.get("groups", []):
            roles.update(self.settings.group_role_map.get(str(group), []))

        return ActorContext(
            actor_id=str(actor_id),
            roles=roles,
            tenant_id=str(claims.get("tid")) if claims.get("tid") else None,
            claims=dict(claims),
        )


def get_actor_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> ActorContext:
    settings = AuthSettings.from_env()
    if settings.mode == "dev":
        actor_id = request.headers.get("X-CEPIO-Dev-Actor", "dev-user")
        roles = {
            role.strip()
            for role in request.headers.get("X-CEPIO-Dev-Roles", "").split(",")
            if role.strip()
        }
        return ActorContext(actor_id=actor_id, roles=roles, tenant_id="dev")

    if settings.mode != "entra":
        raise RuntimeError(f"Unsupported CEPIO_AUTH_MODE: {settings.mode}")
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "authentication_required", "message": "Bearer token is required"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return EntraTokenValidator(settings).validate(credentials.credentials)
