from __future__ import annotations

from typing import Any

import jwt
from fastapi import HTTPException, Request, status

from shared.observability import inc_auth_rejected


class JwtAuth:
    def __init__(
        self,
        *,
        service_name: str,
        enabled: bool,
        secret: str,
        algorithm: str,
        required_scope: str | None,
        issuer: str | None,
        audience: str | None,
    ) -> None:
        self.service_name = service_name
        self.enabled = enabled
        self.secret = secret
        self.algorithm = algorithm
        self.required_scope = required_scope
        self.issuer = issuer
        self.audience = audience

    def verify_write_access(self, request: Request) -> dict[str, Any]:
        if not self.enabled:
            return {"sub": "anonymous", "scope": ""}

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            inc_auth_rejected(self.service_name, request.url.path, "missing_bearer")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Bearer token",
            )

        token = auth_header.removeprefix("Bearer ").strip()
        if not token:
            inc_auth_rejected(self.service_name, request.url.path, "empty_bearer")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Empty Bearer token",
            )

        decode_kwargs: dict[str, Any] = {
            "key": self.secret,
            "algorithms": [self.algorithm],
        }
        if self.issuer:
            decode_kwargs["issuer"] = self.issuer
        if self.audience:
            decode_kwargs["audience"] = self.audience

        try:
            claims = jwt.decode(token, **decode_kwargs)
        except jwt.PyJWTError:
            inc_auth_rejected(self.service_name, request.url.path, "invalid_token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            ) from None

        required = self.required_scope
        token_scope = str(claims.get("scope", ""))
        token_scopes = {scope for scope in token_scope.split() if scope}
        if required and required not in token_scopes:
            inc_auth_rejected(self.service_name, request.url.path, "missing_scope")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scope: {required}",
            )
        return claims


async def require_write_access(request: Request) -> dict[str, Any]:
    auth = request.app.state.auth
    claims = auth.verify_write_access(request)
    request.state.auth_claims = claims
    return claims
