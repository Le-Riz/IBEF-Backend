from fastapi import APIRouter
from typing import Any
from schemas import Point, PointsList

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/point/{sensor_id}", response_model=Point)
async def get_point(sensor_id: str) -> Point:
    # placeholder implementation
    return Point(time=0.0, value=0.0)


@router.get("/list/{sensor_id}", response_model=PointsList)
async def get_list(sensor_id: str, time: float | None = None) -> PointsList:
    # placeholder: return a list of recent points
    sample = [Point(time=0.0, value=0.0), Point(time=1.0, value=1.0)]
    return PointsList(list=sample)
