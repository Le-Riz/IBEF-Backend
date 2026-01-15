from fastapi import APIRouter, Path, HTTPException
from fastapi.responses import StreamingResponse
import io
import base64
from core.services.test_manager import test_manager

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/{sensor_name}", response_class=StreamingResponse)
async def get_graphique(
    sensor_name: str = Path(..., description="Sensor name: DISP_1 or ARC")
):
    """
    Get the current test graphique as PNG image.
    
    Args:
        sensor_name: Either 'DISP_1' or 'ARC' for X-axis sensor
    
    Y-axis: FORCE
    Points are added in real-time as data is processed.
    """
    if sensor_name not in ['DISP_1', 'ARC']:
        raise HTTPException(status_code=400, detail="sensor_name must be 'DISP_1' or 'ARC'")
    
    png_data = test_manager.get_graphique_png(sensor_name)
    
    return StreamingResponse(
        io.BytesIO(png_data),
        media_type="image/png",
        headers={"Content-Disposition": f"inline; filename=graph_{sensor_name}.png"}
    )


@router.get("/{sensor_name}/base64")
async def get_graphique_base64(
    sensor_name: str = Path(..., description="Sensor name: DISP_1 or ARC")
):
    """
    Get the current test graphique as base64-encoded PNG.
    
    Args:
        sensor_name: Either 'DISP_1' or 'ARC' for X-axis sensor
    
    Useful for embedding in frontend applications.
    Returns: {"data": "data:image/png;base64,..."}
    """
    if sensor_name not in ['DISP_1', 'ARC']:
        raise HTTPException(status_code=400, detail="sensor_name must be 'DISP_1' or 'ARC'")
    
    png_data = test_manager.get_graphique_png(sensor_name)
    base64_data = base64.b64encode(png_data).decode('utf-8')
    
    return {
        "data": f"data:image/png;base64,{base64_data}"
    }
