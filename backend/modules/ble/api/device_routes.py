"""Bluetooth device-related routes."""
import logging
import asyncio
from bleak import BleakScanner
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path
from pydantic import BaseModel, Field

from backend.dependencies import get_ble_service, get_ble_metrics
from backend.modules.ble.core.ble_service import BleService
from backend.modules.ble.core.ble_metrics import BleMetricsCollector
# Import all Pydantic models from the central models file
from backend.modules.ble.models.ble_models import (
    BLEDeviceInfo, ConnectionParams, ConnectionResult, ConnectionStatus,
    WriteRequest, NotificationRequest, ServiceFilterRequest,
    DevicePairRequest, DeviceBondRequest, ScanParams,
    CharacteristicValue, ReadResult
)

# Create router
device_router = APIRouter(prefix="/device", tags=["BLE Devices"])

# Get logger
logger = logging.getLogger(__name__)

# Device list and scanning endpoints
@device_router.get("/bonded")
async def list_bonded_devices(ble_service: BleService = Depends(get_ble_service)):
    """Get a list of bonded/paired devices."""
    try:
        devices = await ble_service.get_bonded_devices()
        if not devices:
            return {"devices": [], "count": 0, "message": "No bonded devices found"}
        return {"devices": devices, "count": len(devices)}
    except Exception as e:
        logger.error(f"Error retrieving bonded devices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving bonded devices: {str(e)}")

@device_router.post("/scan")
async def scan_devices(
    params: ScanParams = Body(...),
    ble_service: BleService = Depends(get_ble_service)
):
    """Scan for BLE devices."""
    try:
        # Use the model's property for consistent access
        real_scan = params.effective_real_scan
        
        # Log exact parameters
        logger.info(f"Scan request received with params: scanTime={params.effective_scan_time}, active={params.active}, mock={params.mock}, real_scan={real_scan}")
        
        # Perform the scan
        devices = await ble_service.scan_for_devices(
            scan_time=params.effective_scan_time,
            active=params.active,
            mock=params.mock,
            real_scan=real_scan
        )
        
        return {
            "devices": devices,
            "count": len(devices),
            "mock": params.mock,
            "real_scan": real_scan
        }
    except Exception as e:
        logger.error(f"Error during scan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.post("/scan/real_only")
async def scan_real_only(
    scan_time: float = Body(10.0, description="Scan duration in seconds")
):
    """
    Scan ONLY for real devices, never return mocks.
    This is a diagnostic endpoint that bypasses normal logic.
    """
    try:
        logger.info("🧪 Testing REAL-ONLY device scan")
        
        # Create a standalone scanner
        devices_found = []
        
        def detection_callback(device, advertisement_data):
            logger.info(f"Found device: {device.address} - {device.name or 'Unknown'}")
            devices_found.append({
                "address": device.address,
                "name": device.name or "Unknown Device",
                "rssi": advertisement_data.rssi,
                "isReal": True
            })
        
        # Create scanner with callback
        scanner = BleakScanner(detection_callback=detection_callback)
        
        # Start scanning
        await scanner.start()
        logger.info(f"Real-only scanner started for {scan_time} seconds")
        
        # Wait for scan_time
        await asyncio.sleep(scan_time)
        
        # Stop scanning
        await scanner.stop()
        logger.info("Real-only scanner stopped")
        
        # Return results
        return {
            "devices": devices_found,
            "count": len(devices_found),
            "scan_time": scan_time,
            "test_type": "real_only"
        }
    except Exception as e:
        logger.error(f"Error during real-only scan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.get("/list")
async def list_devices(
    cached: bool = Query(True, description="Whether to return cached devices"),
    ble_service: BleService = Depends(get_ble_service)
):
    """Get a list of previously discovered BLE devices."""
    try:
        devices = await ble_service.get_discovered_devices(cached=cached)
        
        # Convert to Pydantic models to ensure consistent formatting
        device_models = []
        for device in devices:
            # If it's a dict, create a model
            if isinstance(device, dict):
                device_models.append(BLEDeviceInfo(**device))
            # If it's already a model, use it directly
            elif isinstance(device, BLEDeviceInfo):
                device_models.append(device)
            # Otherwise try to convert it
            else:
                device_dict = device.to_dict() if hasattr(device, 'to_dict') else device.__dict__
                device_models.append(BLEDeviceInfo(**device_dict))
        
        return {
            "devices": [model.dict() for model in device_models],
            "count": len(device_models)
        }
    except Exception as e:
        logger.error(f"Error listing devices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Device connection and management endpoints
@device_router.post("/connect")
async def connect_device(
    params: ConnectionParams,
    ble_service: BleService = Depends(get_ble_service)
):
    """Connect to a BLE device."""
    try:
        result = await ble_service.connect_device(
            address=params.address,
            timeout=params.timeout
        )
        
        # Convert result to Pydantic model
        connection_result = ConnectionResult(
            status=ConnectionStatus(result.get("status", "error")),
            address=result.get("address", ""),
            services=result.get("services", []),
            service_count=result.get("service_count", 0),
            error=result.get("error")
        )
        
        return connection_result.dict()
    except Exception as e:
        logger.error(f"Error connecting to device: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.post("/disconnect")
async def disconnect_device(ble_service: BleService = Depends(get_ble_service)):
    """Disconnect from the currently connected device."""
    try:
        if not ble_service.is_connected():
            return {"status": "not_connected", "message": "No device is currently connected"}
        
        device_address = ble_service.get_connected_device_address()
        await ble_service.disconnect_device()
        
        return {"status": "disconnected", "device": device_address}
    except Exception as e:
        logger.error(f"Disconnect error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.get("/status")
async def check_connection_status(ble_service: BleService = Depends(get_ble_service)):
    """Check if a device is currently connected."""
    try:
        is_connected = ble_service.is_connected()
        device_address = ble_service.get_connected_device_address() if is_connected else None
        uptime = ble_service.get_connection_uptime() if is_connected else None
        
        return {
            "connected": is_connected,
            "device": device_address,
            "uptime": uptime
        }
    except Exception as e:
        logger.error(f"Error checking connection status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error checking connection status: {str(e)}")

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
        if not services:
            return {"services": [], "count": 0, "message": "No services found"}
        
        return {"services": services, "count": len(services)}
    except Exception as e:
        logger.error(f"Error getting services: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting services: {str(e)}")

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
            char_value = CharacteristicValue(
                hex=value.hex(),
                text=value.decode('utf-8', errors='replace'),
                bytes=[b for b in value]
            )
            
            result = ReadResult(
                characteristic_uuid=characteristic,
                value=char_value
            )
            
            return result.dict()
        
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
    request: NotificationRequest,  # Use NotificationRequest instead of NotifyRequest
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