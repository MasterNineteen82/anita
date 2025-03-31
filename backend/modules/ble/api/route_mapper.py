"""Maps BLE API routes to implementations."""
import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException

from backend.dependencies import get_ble_service
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
            devices=[model.dict() for model in device_models],
            count=len(device_models),
            scan_time=scan_time,
            active=active,
            mock=any(device.isMock for device in device_models)
        )
        
        return result.dict()
    except Exception as e:
        logger.error(f"Error scanning for devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))