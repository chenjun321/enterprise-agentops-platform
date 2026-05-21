from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, Request, status

from app.core.config import get_settings


@dataclass(frozen=True)
class AuthContext:
    employee_id: str
    role: str
    token: str


def require_internal_api_key(request: Request) -> None:
    settings = get_settings()
    if not settings.internal_api_key:
        return

    provided = request.headers.get(settings.api_key_header_name)
    if provided == settings.internal_api_key:
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid_api_key",
        headers={"WWW-Authenticate": settings.api_key_header_name},
    )


def require_public_channel_token(request: Request) -> None:
    settings = get_settings()
    if not settings.public_channel_token:
        return

    provided = request.headers.get(settings.public_channel_header_name)
    if provided == settings.public_channel_token:
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid_channel_token",
        headers={"WWW-Authenticate": settings.public_channel_header_name},
    )


def get_optional_auth_context(request: Request) -> Optional[AuthContext]:
    settings = get_settings()
    if not settings.auth_tokens:
        return None

    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing_bearer_token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = settings.auth_tokens.get(token)
    if not claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_bearer_token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthContext(employee_id=claims["employee_id"], role=claims["role"], token=token)
