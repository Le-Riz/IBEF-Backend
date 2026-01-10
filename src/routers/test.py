from fastapi import APIRouter
from typing import Any
from schemas import EmptyResponse

router = APIRouter(prefix="/test", tags=["test"])


@router.put("/start", response_model=EmptyResponse)
async def start_test(payload: list[dict] | None = None) -> EmptyResponse:
    # accept a list of fields to start a test; placeholder
    return EmptyResponse()


@router.put("/stop", response_model=EmptyResponse)
async def stop_test() -> EmptyResponse:
    # placeholder stop
    return EmptyResponse()
