import hmac
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status

from aiops_api.settings import Settings
from aiops_api.usage import use_cases
from aiops_api.usage.ports import UsageRepository
from aiops_contracts.usage import BudgetStatus, LlmUsage

router = APIRouter()


def _repo(request: Request) -> UsageRepository:
    return request.app.state.usage_repo


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def require_service_token(
    settings: Annotated[Settings, Depends(_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Internal endpoints accept only the agent's service token. Fail closed if unset."""
    if settings.internal_token is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "internal token not configured")
    presented = (authorization or "").removeprefix("Bearer ")
    if not hmac.compare_digest(presented.encode(), settings.internal_token.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid service token")


@router.post(
    "/internal/usage",
    tags=["internal"],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_service_token)],
    responses={200: {"description": "Duplicate call_id: already recorded"}},
)
def post_usage(
    usage: LlmUsage,
    response: Response,
    repo: Annotated[UsageRepository, Depends(_repo)],
) -> dict[str, str]:
    """Record one LLM call reported by the agent. Idempotent on call_id."""
    if not use_cases.record_usage(repo, usage):
        response.status_code = status.HTTP_200_OK
        return {"status": "duplicate"}
    return {"status": "recorded"}


@router.get("/api/budget/today", tags=["budget"])
def get_budget_today(
    repo: Annotated[UsageRepository, Depends(_repo)],
    settings: Annotated[Settings, Depends(_settings)],
) -> BudgetStatus:
    """Today's (UTC) LLM spend against the cap, for the console's budget meter."""
    return use_cases.daily_budget(
        repo,
        datetime.now(UTC).date(),
        settings.daily_llm_budget_usd,
        settings.daily_llm_call_cap,
    )
