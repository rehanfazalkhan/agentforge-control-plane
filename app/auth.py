"""JWT verification and principal normalization for production requests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import Settings


class AuthenticationError(ValueError):
    """Raised when a caller cannot be authenticated or assigned a role."""


@dataclass(frozen=True)
class Principal:
    subject: str
    role: str


VALID_ROLES = {"operator", "analyst", "admin"}


def authenticate(
    authorization: str | None,
    settings: Settings,
    requested_development_role: str,
) -> Principal:
    """Authenticate a bearer token in production; never trust a body role there."""
    if not settings.is_production:
        return Principal(subject="local-development-user", role=requested_development_role)

    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("A bearer token is required in production mode.")

    try:
        import jwt
    except ImportError as error:  # pragma: no cover - dependency is required in production
        raise AuthenticationError("PyJWT is not installed in this runtime.") from error

    token = authorization.removeprefix("Bearer ").strip()
    try:
        signing_key = jwt.PyJWKClient(settings.jwt_issuer + "/.well-known/jwks.json").get_signing_key_from_jwt(token)
        claims: dict[str, Any] = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
    except Exception as error:  # The public API must not disclose token-validation details.
        raise AuthenticationError("The supplied bearer token is invalid.") from error

    subject = claims.get("sub")
    raw_role = claims.get(settings.jwt_role_claim) or claims.get("role")
    roles = raw_role if isinstance(raw_role, list) else [raw_role]
    role = next((candidate for candidate in ("admin", "analyst", "operator") if candidate in roles), None)
    if not subject or role not in VALID_ROLES:
        raise AuthenticationError("The token does not contain an approved AgentForge role.")
    return Principal(subject=str(subject), role=role)
