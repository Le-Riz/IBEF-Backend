from fastapi import APIRouter, HTTPException
from typing import Any
from dataclasses import asdict
from core.models.test_data import TestMetaData
from core.models.test_state import TestState
from core.services.test_manager import test_manager
from schemas import TestStatusResponse

router = APIRouter(prefix="/test", tags=["test"])


@router.get("/running", response_model=TestStatusResponse)
async def get_test_state() -> TestStatusResponse:
    """
    Get the current state of the test system.
    
    Returns one of four possible states:
    - **NOTHING**: No test is running, no test is stopped, AND no test metadata has been prepared.
      Ready to start fresh.
    - **PREPARED**: No test is currently running AND no test stopped, BUT test metadata has been set.
      Ready to call PUT /start to begin the test.
    - **RUNNING**: A test is currently executing and recording data.
      Data is being collected; call PUT /stop to end recording.
    - **STOPPED**: A test has stopped recording BUT not yet finalized.
      Review the data, then call PUT /finalize to move to history.
    """
    state = test_manager.get_test_state()
    return TestStatusResponse(status=state)


@router.post("/info", status_code=204, responses={
    409: {
        "description": "A test is already running. Cannot prepare new metadata while a test is in progress.",
        "content": {
            "application/json": {
                "example": {"detail": "A test is already running."}
            }
        }
    }
})
async def set_test_info(metadata: TestMetaData) -> None:
    """
    Set test metadata to prepare for a test run.
    
    This endpoint stores the test information without starting data collection.
    After calling this, the test will be in PREPARED state.
    Then call PUT /start to begin the actual test.
    """
    # Prepare the test with metadata
    try:
        test_manager.prepare_test(metadata)
    except RuntimeError as e:
        # A test is already running
        raise HTTPException(status_code=409, detail=str(e))


@router.put("/start", status_code=204, responses={
    400: {
        "description": "No test metadata prepared. Call POST /info first.",
        "content": {
            "application/json": {
                "example": {"detail": "No test metadata prepared. Call POST /info first."}
            }
        }
    },
    409: {
        "description": "A test is already running.",
        "content": {
            "application/json": {
                "example": {"detail": "A test is already running."}
            }
        }
    }
})
async def start_test() -> None:
    """
    Start the prepared test and begin recording data.
    
    Requires that metadata has been set via POST /info first.
    Changes state from PREPARED to RUNNING.
    """
    # Start the prepared test via TestManager
    try:
        test_manager.start_test()
    except ValueError as e:
        # Missing prepared test
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # A test is already running
        raise HTTPException(status_code=409, detail=str(e))


@router.put("/stop", status_code=204)
async def stop_test() -> None:
    """
    Stop the currently running test and end data recording.
    
    Changes state from RUNNING to STOPPED.
    Test data is preserved in memory and on disk but not yet moved to history.
    Call PUT /finalize to move the test to history.
    """
    # Stop the current test via TestManager
    test_manager.stop_test()


@router.get("/description", responses={
    409: {
        "description": "No test prepared. Call POST /info first.",
        "content": {
            "application/json": {
                "example": {"detail": "No test prepared. Call POST /info first."}
            }
        }
    }
})
async def get_current_test_description() -> dict:
    """
    Get the description of the current test (PREPARED or RUNNING state).
    
    Available after POST /info has been called.
    Returns the markdown content of description.md
    """
    if test_manager.current_test is None:
        raise HTTPException(status_code=409, detail="No test prepared. Call POST /info first.")
    
    try:
        content = test_manager.get_description(test_manager.current_test.test_id)
        return {"content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Description file not found")


@router.get("/info", responses={
    409: {
        "description": "No test prepared. Call POST /info first.",
        "content": {
            "application/json": {
                "example": {"detail": "No test prepared. Call POST /info first."}
            }
        }
    }
})
async def get_current_test_info() -> Any:
    """
    Return the metadata of the current prepared/test in memory.

    Returns 409 if no test metadata was prepared via POST /info.
    """
    if test_manager.current_test is None:
        raise HTTPException(status_code=409, detail="No test prepared. Call POST /info first.")

    # Return a JSON-serializable dict of the TestMetaData
    try:
        return asdict(test_manager.current_test)
    except Exception:
        # Fallback: attempt to convert via dataclass fields
        return dict(test_manager.current_test.__dict__)


@router.put("/description", status_code=204, responses={
    409: {
        "description": "No test prepared. Call POST /info first.",
        "content": {
            "application/json": {
                "example": {"detail": "No test prepared. Call POST /info first."}
            }
        }
    },
    500: {
        "description": "Failed to update description.",
        "content": {
            "application/json": {
                "example": {"detail": "Failed to update description: Permission denied"}
            }
        }
    }
})
async def update_current_test_description(payload: dict) -> None:
    """
    Update the description of the current test (PREPARED or RUNNING state).
    
    Available after POST /info has been called.
    Modifies the description.md file in real-time.
    
    Request body:
    ```json
    {
        "content": "# Updated Description\n\nNew markdown content..."
    }
    ```
    """
    if test_manager.current_test is None:
        raise HTTPException(status_code=409, detail="No test prepared. Call POST /info first.")
    
    content = payload.get("content", "")
    test_id = test_manager.current_test.test_id
    
    if not test_manager.set_description(test_id, content):
        raise HTTPException(status_code=500, detail="Failed to update description")


@router.put("/finalize", status_code=204, responses={
    400: {
        "description": "No test in STOPPED state to finalize.",
        "content": {
            "application/json": {
                "example": {"detail": "No test to finalize."}
            }
        }
    },
    409: {
        "description": "Test is still running. Call PUT /stop first.",
        "content": {
            "application/json": {
                "example": {"detail": "Test is not stopped. Call PUT /stop first."}
            }
        }
    }
})
async def finalize_test() -> None:
    """
    Finalize a stopped test and move it to history.
    
    Changes state from STOPPED to NOTHING.
    Test data is now part of the historical record and cannot be modified.
    
    Requires that the test has been stopped via PUT /stop first.
    """
    try:
        test_manager.finalize_test()
    except ValueError as e:
        # No test to finalize
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # Test is not stopped
        raise HTTPException(status_code=409, detail=str(e))