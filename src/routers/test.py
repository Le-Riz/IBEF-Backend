from fastapi import APIRouter, HTTPException
from typing import Any
from core.models.test_data import TestMetaData
from core.services.test_manager import test_manager

router = APIRouter(prefix="/test", tags=["test"])


@router.put("/start", status_code=204)
async def start_test(payload: TestMetaData | None = None) -> None:
    # Start the test via TestManager
    try:
        test_manager.start_test(payload)
    except ValueError as e:
        # Missing prepared test and no metadata provided
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # A test is already running
        raise HTTPException(status_code=409, detail=str(e))


@router.put("/stop", status_code=204)
async def stop_test() -> None:
    # Stop the current test via TestManager
    test_manager.stop_test()
