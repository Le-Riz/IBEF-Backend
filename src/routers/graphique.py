from fastapi import APIRouter, Path, HTTPException
from fastapi.responses import StreamingResponse
import io
import base64
from core.services.test_manager import test_manager
from core.sensor_reconnection import sensor_reconnection_manager

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/{sensor_name}", response_class=StreamingResponse, responses={
    400: {
        "description": "Invalid sensor_name provided.",
        "content": {
            "application/json": {
                "example": {"detail": "sensor_name must be 'DISP_1' or 'ARC'"}
            }
        }
    },
    503: {
        "description": "Sensor is not currently connected.",
        "content": {
            "application/json": {
                "example": {"detail": "Sensor FORCE is not connected"}
            }
        }
    }
})
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
    
    # For DISP_1 X-axis, check DISP_1 connection
    if sensor_name == 'DISP_1':
        if not sensor_reconnection_manager.is_sensor_connected('DISP_1'):
            raise HTTPException(status_code=503, detail="Sensor DISP_1 is not connected")
    # For ARC X-axis, check DISP_2 and DISP_3 connection (ARC is calculated from DISP_2, DISP_3)
    else:  # sensor_name == 'ARC'
        if not sensor_reconnection_manager.is_sensor_connected('DISP_2') or not sensor_reconnection_manager.is_sensor_connected('DISP_3'):
            raise HTTPException(status_code=503, detail="Sensors DISP_2 and DISP_3 are not connected (required for ARC calculation)")
    
    # Also check FORCE connection (Y-axis)
    if not sensor_reconnection_manager.is_sensor_connected('FORCE'):
        raise HTTPException(status_code=503, detail="Sensor FORCE is not connected")
    
    png_data = test_manager.get_graphique_png(sensor_name)
    
    return StreamingResponse(
        io.BytesIO(png_data),
        media_type="image/png",
        headers={"Content-Disposition": f"inline; filename=graph_{sensor_name}.png"}
    )


@router.get("/{sensor_name}/base64", responses={
    400: {
        "description": "Invalid sensor_name provided.",
        "content": {
            "application/json": {
                "example": {"detail": "sensor_name must be 'DISP_1' or 'ARC'"}
            }
        }
    },
    503: {
        "description": "Sensor is not currently connected.",
        "content": {
            "application/json": {
                "example": {"detail": "Sensor FORCE is not connected"}
            }
        }
    }
})
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
    
    # For DISP_1 X-axis, check DISP_1 connection
    if sensor_name == 'DISP_1':
        if not sensor_reconnection_manager.is_sensor_connected('DISP_1'):
            raise HTTPException(status_code=503, detail="Sensor DISP_1 is not connected")
    # For ARC X-axis, check DISP_2 and DISP_3 connection (ARC is calculated from DISP_2, DISP_3)
    else:  # sensor_name == 'ARC'
        if not sensor_reconnection_manager.is_sensor_connected('DISP_2') or not sensor_reconnection_manager.is_sensor_connected('DISP_3'):
            raise HTTPException(status_code=503, detail="Sensors DISP_2 and DISP_3 are not connected (required for ARC calculation)")
    
    # Also check FORCE connection (Y-axis)
    if not sensor_reconnection_manager.is_sensor_connected('FORCE'):
        raise HTTPException(status_code=503, detail="Sensor FORCE is not connected")
    
    png_data = test_manager.get_graphique_png(sensor_name)
    base64_data = base64.b64encode(png_data).decode('utf-8')
    
    return {
        "data": f"data:image/png;base64,{base64_data}"
    }
