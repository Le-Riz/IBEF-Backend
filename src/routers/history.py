from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from typing import Any
import io
from schemas import HistoryList, EmptyResponse, FieldsResponse

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/list", response_model=HistoryList)
async def list_histories() -> HistoryList:
    # placeholder: return available history names
    return HistoryList(list=["X"])


@router.delete("/{name}", response_model=EmptyResponse)
async def delete_history(name: str) -> EmptyResponse:
    return EmptyResponse()


@router.put("/{name}", response_model=EmptyResponse)
async def put_history(name: str) -> EmptyResponse:
    return EmptyResponse()


@router.post("/{name}", response_model=EmptyResponse)
async def post_history(name: str, payload: list[dict] | None = None) -> EmptyResponse:
    return EmptyResponse()


@router.get("/{name}", response_model=FieldsResponse)
async def get_history(name: str, download: bool = Query(False)):
    if download:
        # return a fake zip stream for now
        buf = io.BytesIO()
        buf.write(b"PK\x03\x04")
        buf.seek(0)
        return StreamingResponse(buf, media_type="application/zip", headers={"Content-Disposition": f"attachment; filename=\"{name}.zip\""})
    # otherwise return fields
    return FieldsResponse(fields=[])
