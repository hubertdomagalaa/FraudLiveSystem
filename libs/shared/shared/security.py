from __future__ import annotations

from typing import Any

import jwt
from fastapi import HTTPException, Request, status
from jwt import PyJWKClient

from shared.observability import inc_auth_rejected


class JwtAuth:
    def __init__(
        self,
        *,
        service_name: str,
        enabled: bool,
        secret: str | None,
        jwks_url: str | None,
        algorithm: str,
        required_scope: str | None,
        issuer: str | None,
        audience: str | None,
        leeway_seconds: int,
    ) -> None:
        if enabled:
            has_secret = bool(secret)
            has_jwks = bool(jwks_url)
            if has_secret == has_jwks:
                raise ValueError("AUTH_ENABLED=true requires exactly one of JWT_SECRET or JWT_JWKS_URL")
            if has_jwks and algorithm.upper().startswith("HS"):
                raise ValueError("JWT_JWKS_URL requires an asymmetric JWT_ALGORITHM such as RS256")

        self.service_name = service_name
        self.enabled = enabled
        self.secret = secret
        self.jwks_url = jwks_url
        self.algorithm = algorithm
        self.required_scope = required_scope
        self.issuer = issuer
        self.audience = audience
        self.leeway_seconds = max(leeway_seconds, 0)
        self._jwks_client = PyJWKClient(jwks_url) if jwks_url else None

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
            "key": self._resolve_signing_key(token, request),
            "algorithms": [self.algorithm],
            "leeway": self.leeway_seconds,
        }
        if self.issuer:
            decode_kwargs["issuer"] = self.issuer
        if self.audience:
            decode_kwargs["audience"] = self.audience

        try:
            claims = jwt.decode(token, **decode_kwargs)
        except jwt.InvalidAudienceError:
            inc_auth_rejected(self.service_name, request.url.path, "invalid_audience")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token audience",
            ) from None
        except jwt.InvalidIssuerError:
            inc_auth_rejected(self.service_name, request.url.path, "invalid_issuer")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token issuer",
            ) from None
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

    def _resolve_signing_key(self, token: str, request: Request) -> Any:
        if self._jwks_client is not None:
            try:
                return self._jwks_client.get_signing_key_from_jwt(token).key
            except jwt.PyJWKClientError:
                inc_auth_rejected(self.service_name, request.url.path, "jwks_unavailable")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="JWKS resolver unavailable",
                ) from None

        if self.secret:
            return self.secret

        inc_auth_rejected(self.service_name, request.url.path, "auth_misconfigured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT auth misconfigured",
        )


async def require_write_access(request: Request) -> dict[str, Any]:
    auth = request.app.state.auth
    claims = auth.verify_write_access(request)
    request.state.auth_claims = claims
    return claims
