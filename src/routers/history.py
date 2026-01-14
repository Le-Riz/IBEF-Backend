from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import io
import zipfile
import os
from schemas import HistoryList
from core.models.test_data import TestMetaData
from core.services.test_manager import test_manager

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=HistoryList)
async def list_histories() -> HistoryList:
    """
    List all available test histories (sorted by date, newest first).
    """
    histories = test_manager.get_history()
    test_ids = [h.test_id for h in histories]
    return HistoryList(list=test_ids)


@router.get("/{name}", response_model=TestMetaData, responses={
    404: {
        "description": "Test history not found.",
        "content": {
            "application/json": {
                "example": {"detail": "Test history 'test_123' not found"}
            }
        }
    }
})
async def get_history_metadata(name: str) -> TestMetaData:
    """
    Get metadata for a specific test history.
    """
    histories = test_manager.get_history()
    for h in histories:
        if h.test_id == name:
            return h
    raise HTTPException(status_code=404, detail=f"Test history '{name}' not found")


@router.get("/{name}/download", responses={
    404: {
        "description": "Test history not found.",
        "content": {
            "application/json": {
                "example": {"detail": "Test history 'test_123' not found"}
            }
        }
    }
})
async def download_history(name: str):
    """
    Download a test history as a ZIP file containing metadata, raw log, and CSV.
    """
    from core.services.test_manager import TEST_DATA_DIR, ARCHIVE_DIR
    
    # Check if test exists in current or archived
    test_dir = os.path.join(TEST_DATA_DIR, name)
    if not os.path.exists(test_dir):
        test_dir = os.path.join(ARCHIVE_DIR, name)
        if not os.path.exists(test_dir):
            raise HTTPException(status_code=404, detail=f"Test history '{name}' not found")
    
    # Create ZIP in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(test_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(test_dir))
                zf.write(file_path, arcname)
    
    buf.seek(0)
    return StreamingResponse(
        buf, 
        media_type="application/zip", 
        headers={"Content-Disposition": f"attachment; filename=\"{name}.zip\""}
    )


@router.delete("/{name}", status_code=204, responses={
    404: {
        "description": "Test history not found.",
        "content": {
            "application/json": {
                "example": {"detail": "Test history 'test_123' not found"}
            }
        }
    }
})
async def delete_history(name: str) -> None:
    """
    Permanently delete a test history.
    """
    success = test_manager.delete_test(name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Test history '{name}' not found")


@router.put("/{name}/archive", status_code=204, responses={
    404: {
        "description": "Test history not found.",
        "content": {
            "application/json": {
                "example": {"detail": "Test history 'test_123' not found"}
            }
        }
    }
})
async def archive_history(name: str) -> None:
    """
    Archive a test history (move to archived storage).
    """
    success = test_manager.archive_test(name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Test history '{name}' not found")


@router.put("/{name}", status_code=204, responses={
    404: {
        "description": "Test history not found.",
        "content": {
            "application/json": {
                "example": {"detail": "Test history 'test_123' not found"}
            }
        }
    },
    500: {
        "description": "Failed to update metadata.",
        "content": {
            "application/json": {
                "example": {"detail": "Failed to update metadata: Permission denied"}
            }
        }
    }
})
async def update_history_metadata(name: str, metadata: TestMetaData) -> None:
    """
    Update metadata for a test history.
    """
    from core.services.test_manager import TEST_DATA_DIR
    from dataclasses import asdict
    import json
    
    test_dir = os.path.join(TEST_DATA_DIR, name)
    if not os.path.exists(test_dir):
        raise HTTPException(status_code=404, detail=f"Test history '{name}' not found")
    
    metadata_file = os.path.join(test_dir, "metadata.json")
    try:
        with open(metadata_file, 'w') as f:
            json.dump(asdict(metadata), f, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update metadata: {str(e)}")


@router.get("/{name}/description", responses={
    404: {
        "description": "Test history or description not found.",
        "content": {
            "application/json": {
                "example": {"detail": "Description not found for test test_123"}
            }
        }
    }
})
async def get_description(name: str) -> dict:
    """
    Get the description.md content for a test history.
    Returns the markdown content as plain text.
    """
    try:
        content = test_manager.get_description(name)
        return {"content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Description not found for test {name}")


@router.put("/{name}/description", status_code=204, responses={
    404: {
        "description": "Test history not found.",
        "content": {
            "application/json": {
                "example": {"detail": "Test history 'test_123' not found"}
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
async def update_description(name: str, payload: dict) -> None:
    """
    Update the description.md content for a test history.
    
    Request body:
    ```json
    {
        "content": "# My Test Description\n\nThis is a markdown file."
    }
    ```
    """
    content = payload.get("content", "")
    if not test_manager.set_description(name, content):
        raise HTTPException(status_code=404, detail=f"Test history '{name}' not found")
