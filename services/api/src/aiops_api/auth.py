"""Shared request guards. Business rules stay in each context's use cases."""

import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from aiops_api.settings import Settings


def settings_of(request: Request) -> Settings:
    return request.app.state.settings


def require_service_token(
    settings: Annotated[Settings, Depends(settings_of)],
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Internal endpoints accept only the service token (agent, Alertmanager).

    Fails closed: with no token configured, every internal call is refused.
    """
    if settings.internal_token is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "internal token not configured")
    presented = (authorization or "").removeprefix("Bearer ")
    if not hmac.compare_digest(presented.encode(), settings.internal_token.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid service token")
