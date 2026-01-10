from fastapi import APIRouter
from schemas import Point

router = APIRouter(prefix="/raw", tags=["raw"])


@router.get("/point/{sensor_id}", response_model=Point)
async def get_raw_point(sensor_id: str) -> Point:
    # placeholder returning same shape as /data/point
    return Point(time=0.0, value=0.0)
