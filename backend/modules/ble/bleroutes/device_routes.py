"""Bluetooth device-related routes."""
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field

from backend.dependencies import get_ble_service, get_ble_metrics
from backend.modules.ble.ble_service import BleService
from backend.modules.ble.ble_metrics import BleMetricsCollector

# Create router
device_router = APIRouter(prefix="/device", tags=["BLE Devices"])

# Get logger
logger = logging.getLogger(__name__)

# Data models
class ConnectRequest(BaseModel):
    address: str
    timeout: Optional[float] = 10.0
    auto_reconnect: Optional[bool] = True

class WriteRequest(BaseModel):
    characteristic: str
    value: str
    value_type: Optional[str] = "auto"
    response: Optional[bool] = True

class NotifyRequest(BaseModel):
    characteristic: str
    enable: bool = True

class ServiceFilterRequest(BaseModel):
    services: List[str] = Field(default_factory=list, description="List of service UUIDs to filter by")

class DevicePairRequest(BaseModel):
    address: str
    timeout: Optional[float] = 10.0

class DeviceBondRequest(BaseModel):
    address: str
    name: Optional[str] = None
    device_type: Optional[str] = None
    is_trusted: bool = True

# Device list and scanning endpoints
@device_router.get("/bonded")
async def list_bonded_devices(ble_service: BleService = Depends(get_ble_service)):
    """Get a list of bonded/paired devices"""
    try:
        devices = await ble_service.get_bonded_devices()
        return {"devices": devices, "count": len(devices)}
    except Exception as e:
        logger.error(f"Error retrieving bonded devices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.post("/scan")
async def scan_for_devices(
    scan_time: float = Query(5.0, description="Duration of scan in seconds"),
    active: bool = Query(True, description="Use active scanning"),
    filter_request: ServiceFilterRequest = Body(ServiceFilterRequest(), description="Service filters"),
    ble_service: BleService = Depends(get_ble_service),
    ble_metrics: BleMetricsCollector = Depends(get_ble_metrics)
):
    """Scan for BLE devices.
    
    Args:
        scan_time: Duration of scan in seconds
        active: Use active scanning (includes device names)
        filter_request: Optional service UUIDs to filter by
    """
    try:
        # Record operation start if metrics collector has the method
        scan_id = None
        if hasattr(ble_metrics, "record_scan_start"):
            scan_id = ble_metrics.record_scan_start()
        
        # Perform scan
        devices = await ble_service.scan_devices(
            scan_time=scan_time, 
            active=active,
            service_uuids=filter_request.services if filter_request.services else None
        )
        
        # Record operation completion if metrics collector has the method
        if scan_id and hasattr(ble_metrics, "record_scan_complete"):
            ble_metrics.record_scan_complete(
                scan_id, 
                success=True, 
                device_count=len(devices)
            )
        
        return {"devices": devices, "count": len(devices)}
    except Exception as e:
        # Record failure if metrics collector has the method
        if scan_id and hasattr(ble_metrics, "record_scan_complete"):
            ble_metrics.record_scan_complete(scan_id, success=False, error=str(e))
        
        logger.error(f"Scan failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")

# Device connection and management endpoints
@device_router.post("/connect")
async def connect_device(
    request: ConnectRequest,
    ble_service: BleService = Depends(get_ble_service),
    ble_metrics: BleMetricsCollector = Depends(get_ble_metrics)
):
    """Connect to a BLE device.
    
    Args:
        request: Connection request parameters
    """
    try:
        # Record connection start
        op_id = None
        if hasattr(ble_metrics, "record_connect_start"):
            op_id = ble_metrics.record_connect_start(request.address)
        
        # Connect to device
        connected = await ble_service.connect_device(
            request.address, 
            timeout=request.timeout,
            auto_reconnect=request.auto_reconnect
        )
        
        # Record connection completion
        if op_id and hasattr(ble_metrics, "record_connect_complete"):
            ble_metrics.record_connect_complete(
                op_id, 
                request.address, 
                success=connected
            )
        
        if connected:
            return {"status": "connected", "device": request.address}
        else:
            raise HTTPException(status_code=400, detail="Failed to connect to device")
    except Exception as e:
        # Record connection error
        if hasattr(ble_metrics, "record_connect_error"):
            ble_metrics.record_connect_error(request.address, str(e))
        
        logger.error(f"Connection error: {e}", exc_info=True)
        
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Device not found: {str(e)}")
        else:
            raise HTTPException(status_code=500, detail=f"Connection error: {str(e)}")

@device_router.post("/disconnect")
async def disconnect_device(ble_service: BleService = Depends(get_ble_service)):
    """Disconnect from the currently connected device."""
    try:
        if not ble_service.is_connected():
            return {"status": "not_connected", "message": "No device is currently connected"}
        
        # Get the address before disconnecting
        device_address = ble_service.get_connected_device_address()
        
        # Disconnect
        await ble_service.disconnect_device()
        
        return {"status": "disconnected", "device": device_address}
    except Exception as e:
        logger.error(f"Disconnect error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Disconnect error: {str(e)}")

@device_router.get("/status")
async def check_connection_status(ble_service: BleService = Depends(get_ble_service)):
    """Check if a device is currently connected."""
    try:
        is_connected = ble_service.is_connected()
        device_address = ble_service.get_connected_device_address() if is_connected else None
        
        return {
            "connected": is_connected,
            "device": device_address,
            "uptime": ble_service.get_connection_uptime() if is_connected else None
        }
    except Exception as e:
        logger.error(f"Error checking connection status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.get("/{device_id}/exists")
async def check_device_exists(
    device_id: str,
    scan_time: float = Query(2.0, description="Duration of scan to check for device"),
    ble_service: BleService = Depends(get_ble_service)
):
    """Check if a specific device exists/is in range."""
    try:
        # Check if already connected to this device
        if ble_service.is_connected():
            current_device = ble_service.get_connected_device_address()
            if current_device == device_id:
                return {"exists": True, "connected": True}
        
        # Scan for the device
        devices = await ble_service.scan_devices(scan_time=scan_time)
        
        for device in devices:
            if isinstance(device, dict) and device.get("address") == device_id:
                return {"exists": True, "connected": False}
            elif hasattr(device, "address") and device.address == device_id:
                return {"exists": True, "connected": False}
        
        return {"exists": False, "connected": False}
    except Exception as e:
        logger.error(f"Error checking device existence: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Service and characteristic discovery endpoints
@device_router.get("/services")
async def get_device_services(ble_service: BleService = Depends(get_ble_service)):
    """Get services from the connected device."""
    try:
        if not ble_service.is_connected():
            raise HTTPException(status_code=400, detail="No device connected")
        
        services = await ble_service.get_services()
        return {"services": services, "count": len(services)}
    except Exception as e:
        logger.error(f"Error getting services: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.get("/services/{service_uuid}/characteristics")
async def get_service_characteristics(
    service_uuid: str,
    ble_service: BleService = Depends(get_ble_service)
):
    """Get characteristics for a specific service."""
    try:
        if not ble_service.is_connected():
            raise HTTPException(status_code=400, detail="No device connected")
        
        characteristics = await ble_service.get_characteristics(service_uuid)
        return {"characteristics": characteristics, "count": len(characteristics)}
    except Exception as e:
        logger.error(f"Error getting characteristics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Data exchange endpoints
@device_router.get("/read/{characteristic}")
async def read_characteristic(
    characteristic: str,
    ble_service: BleService = Depends(get_ble_service)
):
    """Read a value from a characteristic."""
    try:
        if not ble_service.is_connected():
            raise HTTPException(status_code=400, detail="No device connected")
        
        # Read the value
        value = await ble_service.read_characteristic(characteristic)
        
        # Return both hex and string representations if it's binary data
        if isinstance(value, bytes):
            return {
                "value": value.hex(),
                "value_str": value.decode('utf-8', errors='replace'),
                "value_bytes": [b for b in value]
            }
        
        return {"value": value}
    except Exception as e:
        logger.error(f"Error reading characteristic: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.post("/write")
async def write_characteristic(
    request: WriteRequest,
    ble_service: BleService = Depends(get_ble_service)
):
    """Write a value to a characteristic."""
    try:
        if not ble_service.is_connected():
            raise HTTPException(status_code=400, detail="No device connected")
        
        # Write the value
        result = await ble_service.write_characteristic(
            request.characteristic, 
            request.value, 
            value_type=request.value_type,
            with_response=request.response
        )
        
        return {"status": "success", "written": request.value}
    except Exception as e:
        logger.error(f"Error writing characteristic: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.post("/notify")
async def enable_notifications(
    request: NotifyRequest,
    ble_service: BleService = Depends(get_ble_service)
):
    """Enable or disable notifications for a characteristic."""
    try:
        if not ble_service.is_connected():
            raise HTTPException(status_code=400, detail="No device connected")
        
        if request.enable:
            result = await ble_service.start_notify(request.characteristic)
            status = "enabled"
        else:
            result = await ble_service.stop_notify(request.characteristic)
            status = "disabled"
        
        return {
            "status": status, 
            "characteristic": request.characteristic,
            "success": result
        }
    except Exception as e:
        logger.error(f"Error with notifications: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.post("/pair")
async def pair_device(
    request: DevicePairRequest,
    ble_service: BleService = Depends(get_ble_service)
):
    """Initiate pairing with a device."""
    try:
        result = await ble_service.pair_device(request.address, timeout=request.timeout)
        
        if result:
            return {"status": "paired", "device": request.address}
        else:
            raise HTTPException(status_code=400, detail=f"Failed to pair with device {request.address}")
    except Exception as e:
        logger.error(f"Pairing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.post("/bond")
async def bond_device(
    request: DeviceBondRequest,
    ble_service: BleService = Depends(get_ble_service)
):
    """Create a persistent bond with a device."""
    try:
        result = await ble_service.bond_device(
            request.address, 
            name=request.name,
            device_type=request.device_type,
            is_trusted=request.is_trusted
        )
        
        if result:
            return {"status": "bonded", "device": request.address}
        else:
            raise HTTPException(status_code=400, detail=f"Failed to bond with device {request.address}")
    except Exception as e:
        logger.error(f"Bonding error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.delete("/bond/{address}")
async def remove_bonded_device(
    address: str,
    ble_service: BleService = Depends(get_ble_service)
):
    """Remove a bonded device."""
    try:
        result = await ble_service.remove_bonded_device(address)
        
        if result:
            return {"status": "removed", "device": address}
        else:
            raise HTTPException(status_code=400, detail=f"Failed to remove bonded device {address}")
    except Exception as e:
        logger.error(f"Error removing bond: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.get("/info")
async def get_device_info(ble_service: BleService = Depends(get_ble_service)):
    """Get information about the connected device."""
    try:
        if not ble_service.is_connected():
            raise HTTPException(status_code=400, detail="No device connected")
        
        info = await ble_service.get_device_info()
        return info
    except Exception as e:
        logger.error(f"Error getting device info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))