"""Maps BLE API routes to implementations."""
import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException

from backend.modules.ble.core.ble_service_factory import get_ble_service
from backend.modules.ble.core.ble_service import BleService
# Update imports to use Pydantic models
from backend.modules.ble.models.ble_models import (
    BLEDeviceInfo, ScanParams, ScanResult, ConnectionResult, ConnectionStatus
)

# Get logger
logger = logging.getLogger(__name__)

# Create frontend-facing router
frontend_api_router = APIRouter(prefix="/ble", tags=["bluetooth"])

@frontend_api_router.post("/scan")
async def scan_devices(params: ScanParams, ble_service: BleService = Depends(get_ble_service)):
    """Start scanning for BLE devices."""
    try:
        scan_time = params.scan_time
        active = params.active
        service_uuids = params.service_uuids
        mock = params.mock
        real_scan = params.real_scan
        
        # Perform scan using the service
        devices = await ble_service.scan_devices(
            scan_time=scan_time,
            active=active,
            service_uuids=service_uuids,
            mock=mock,
            real_scan=real_scan
        )
        
        # Convert to Pydantic models if they aren't already
        device_models = []
        for device in devices:
            # If it's already a dict (but not a model), create a model
            if isinstance(device, dict):
                device_models.append(BLEDeviceInfo(**device))
            # If it's already a model, use it directly
            elif isinstance(device, BLEDeviceInfo):
                device_models.append(device)
            # Otherwise try to convert it
            else:
                device_dict = device.to_dict() if hasattr(device, 'to_dict') else device.__dict__
                device_models.append(BLEDeviceInfo(**device_dict))
        
        # Create scan result with the models and convert to dict for response
        result = ScanResult(
            devices=[model.model_dump() for model in device_models],
            count=len(device_models),
            scan_time=scan_time,
            active=active,
            mock=any(device.isMock for device in device_models)
        )
        
        return result.model_dump()
    except Exception as e:
        logger.error(f"Error scanning for devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

"""Frontend API route mapping for BLE module."""

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse

# Create router for frontend-specific BLE API endpoints
frontend_api_router = APIRouter(prefix="/frontend/api/ble", tags=["BLE Frontend API"])

@frontend_api_router.get("/status")
async def ble_status():
    """Get BLE module status for frontend."""
    try:
        # Import BLE dependencies here to avoid circular imports
        from backend.modules.ble.core.ble_service import get_ble_service
        
        ble_service = get_ble_service()
        
        # Get basic status information
        return {
            "status": "active",
            "available": True,
            "supported": True,
            "message": "BLE module is active"
        }
    except Exception as e:
        return {
            "status": "error",
            "available": False,
            "supported": True,
            "message": f"BLE module error: {str(e)}"
        }

@frontend_api_router.get("/adapter/info")
async def get_frontend_adapter_info():
    """Get adapter information formatted for frontend use."""
    try:
        # Import BLE dependencies here to avoid circular imports
        from backend.modules.ble.core.ble_service import get_ble_service
        
        ble_service = get_ble_service()
        adapters = await ble_service.get_adapters()
        
        return {
            "status": "success",
            "adapters": adapters,
            "count": len(adapters)
        }
    except Exception as e:
        # Return a friendly error response
        return {
            "status": "error",
            "message": f"Failed to get adapter information: {str(e)}",
            "adapters": [],
            "count": 0
        }

# Add this function to create the alternative endpoint
@frontend_api_router.get("/adapter-info")
async def get_frontend_adapter_info_alt():
    """Alternative endpoint for adapter information to match frontend expectations."""
    return await get_frontend_adapter_info()
