"""Bluetooth device-related routes."""
import logging
import asyncio
import json
import time
from bleak import BleakScanner
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path, Response
from pydantic import BaseModel, Field

from backend.dependencies import get_ble_metrics
from backend.modules.ble.core.ble_service import BleService
from backend.modules.ble.core.ble_metrics import BleMetricsCollector
from backend.modules.ble.models.ble_models import (
    BLEDeviceInfo, ConnectionParams, ConnectionResult, ConnectionStatus,
    WriteRequest, NotificationRequest, ServiceFilterRequest,
    DevicePairRequest, DeviceBondRequest, ScanParams,
    CharacteristicValue, ReadResult
)
from backend.modules.ble.models.ble_models import DeviceResponse
from backend.modules.ble.core.ble_service_factory import get_ble_service

# Create a single router definition
device_router = APIRouter(prefix="/device", tags=["BLE Devices"])  # Change from "/devices" to "/device"

# Get logger
logger = logging.getLogger(__name__)

# Device list and scanning endpoints
@device_router.get("/", response_model=List[DeviceResponse])
async def get_devices(
    ble_service: BleService = Depends(get_ble_service),
    filter_name: Optional[str] = Query(None, description="Filter devices by name")
):
    """Get a list of BLE devices (discovered/cached)."""
    try:
        # Use get_discovered_devices which likely represents the general device list
        devices = await ble_service.get_discovered_devices()
        
        # Apply filter if provided
        if filter_name:
            # Assuming devices is List[Dict], filter based on 'name' key
            devices = [d for d in devices if filter_name.lower() in d.get("name", "").lower()]
            
        # Return the list of device dicts directly
        return devices 
    except Exception as e:
        logger.error(f"Failed to get devices: {e}", exc_info=True) # Log the actual error
        raise HTTPException(status_code=500, detail=f"Failed to get devices: {str(e)}")

@device_router.get("/bonded", response_model=None)
async def list_bonded_devices(ble_service: BleService = Depends(get_ble_service)):
    """Get list of bonded/saved devices."""
    try:
        devices = await ble_service.get_saved_devices()
        return Response(content=json.dumps(devices, default=str), media_type="application/json")
    except Exception as e:
        logger.error(f"Error getting bonded devices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

def get_mock_devices():
    """Generate realistic mock BLE devices for testing."""
    return [
        {
            "address": "00:11:22:33:44:55",
            "name": "Smart Watch XR3",
            "rssi": -65,
            "is_real": False,
            "metadata": {
                "manufacturer_data": {"76": "1403010b13187164"},
                "service_uuids": ["1800", "1801", "180a"]
            }
        },
        {
            "address": "11:22:33:44:55:66",
            "name": "BLE Sensor 2.0",
            "rssi": -72,
            "is_real": False,
            "metadata": {
                "manufacturer_data": {"106": "07569abcd"},
                "service_uuids": ["181a"]
            }
        },
        {
            "address": "22:33:44:55:66:77",
            "name": "Fitness Tracker Pro",
            "rssi": -58,
            "is_real": False,
            "metadata": {
                "manufacturer_data": {"89": "0300"},
                "service_uuids": ["180d", "180f"]
            }
        }
    ]

@device_router.post("/scan", response_model=None)
async def start_scan(
    params: ScanParams = Body(...),
    ble_service: BleService = Depends(get_ble_service)
):
    """Start scanning for BLE devices."""
    try:
        # If explicitly requesting mock data, just return mock devices
        if params.mock:
            logger.info("Using mock device data as requested")
            devices = get_mock_devices()
            return {"status": "success", "devices": devices}
        
        # Initialize service if needed - this will check for conflicting Bluetooth apps
        if hasattr(ble_service, 'initialize'):
            await ble_service.initialize()
        
        # Try real scanning
        try:
            devices = await ble_service.scan_devices(
                scan_time=params.scan_time,
                active=params.active,
                name_prefix=params.name_prefix,
                services=params.service_uuids
            )
            
            # If no real devices found and mock is not explicitly disabled, add mock devices
            if not devices and params.mock is not False:
                logger.info("No real devices found, adding mock data")
                devices = get_mock_devices()
            
            return {"status": "success", "devices": devices}
        except Exception as e:
            # If real scanning failed and mock is not explicitly disabled, return mock devices
            if params.mock is not False:
                logger.warning(f"Real scan failed, falling back to mock data: {e}")
                devices = get_mock_devices()
                return {"status": "success", "devices": devices}
            else:
                logger.error(f"Error starting scan: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error in scan endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.get("/discovered", response_model=Dict[str, List[Dict]])
async def get_discovered_devices(
    ble_service: BleService = Depends(get_ble_service),
    mock: bool = Query(None, description="Whether to include mock devices if real ones not available")
):
    """Get all discovered BLE devices without scanning again."""
    try:
        # Try to get real discovered devices
        devices = await ble_service.get_discovered_devices()
        
        # If no devices and mock is not explicitly disabled, add mock data
        if (not devices or len(devices) == 0) and mock is not False:
            logger.info("No real discovered devices found, providing mock data")
            devices = get_mock_devices()
            
        # Return in the standardized format
        return {"status": "success", "devices": devices}
    except Exception as e:
        logger.error(f"Error getting discovered devices: {e}", exc_info=True)
        
        # If there's an error but mock is not explicitly disabled, return mock data
        if mock is not False:
            logger.info("Error retrieving real devices, falling back to mock data")
            return {"status": "success", "devices": get_mock_devices()}
        else:
            # Only raise exception if mock is explicitly disabled
            raise HTTPException(status_code=500, detail=str(e))

@device_router.post("/scan/real_only", response_model=None)
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
        return Response(content=json.dumps({
            "devices": devices_found,
            "count": len(devices_found),
            "scan_time": scan_time,
            "test_type": "real_only"
        }, default=str), media_type="application/json")
    except Exception as e:
        logger.error(f"Error during real-only scan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.get("/list", response_model=None)
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
        
        return Response(content=json.dumps({
            "devices": [model.model_dump() for model in device_models],
            "count": len(device_models)
        }, default=str), media_type="application/json")
    except Exception as e:
        logger.error(f"Error listing devices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Device connection and management endpoints
@device_router.get("/connection", response_model=Dict[str, Any])
async def check_connection_status(ble_service: BleService = Depends(get_ble_service)):
    """Check the current BLE connection status."""
    try:
        is_connected, connected_address = await ble_service.is_connected()
        return {"connected": is_connected, "device_address": connected_address}
    except Exception as e:
        logger.error(f"Error checking connection status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.post("/connect", response_model=None)
async def connect_device(
    params: ConnectionParams = Body(...),
    ble_service: BleService = Depends(get_ble_service)
):
    """Connect to a BLE device."""
    try:
        result = await ble_service.connect_device(address=params.address)
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Error connecting to device: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Pydantic model for disconnect request body
class DisconnectRequest(BaseModel):
    address: str

@device_router.post("/disconnect", response_model=None)
async def disconnect_device(
    request_data: DisconnectRequest,  
    ble_service: BleService = Depends(get_ble_service)
):
    """Disconnect from the currently connected device."""
    logger.debug(f"Received disconnect request with address: {request_data.address}")
    try:
        # Pass the address from the model to the service
        result = await ble_service.disconnect_device(request_data.address)
        logger.debug(f"Disconnect result: {result}")
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Error disconnecting from device: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.get("/{device_id}/exists", response_model=None)
async def check_device_exists(
    device_id: str,
    scan_time: float = Query(2.0, description="Duration of scan to check for device"),
    ble_service: BleService = Depends(get_ble_service)
):
    """Check if a specific device exists/is in range."""
    try:
        # Check if already connected to this device
        if await ble_service.is_connected():
            current_device = ble_service.get_connected_device_address()
            if current_device == device_id:
                return Response(content=json.dumps({"exists": True, "connected": True}, default=str), media_type="application/json")
        
        # Scan for the device
        devices = await ble_service.scan_devices(scan_time=scan_time)
        
        for device in devices:
            if isinstance(device, dict) and device.get("address") == device_id:
                return Response(content=json.dumps({"exists": True, "connected": False}, default=str), media_type="application/json")
            elif hasattr(device, "address") and device.address == device_id:
                return Response(content=json.dumps({"exists": True, "connected": False}, default=str), media_type="application/json")
        
        return Response(content=json.dumps({"exists": False, "connected": False}, default=str), media_type="application/json")
    except Exception as e:
        logger.error(f"Error checking device existence: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Service and characteristic discovery endpoints
@device_router.get("/services", response_model=None)
async def get_device_services(ble_service: BleService = Depends(get_ble_service)):
    """Get services from the connected device."""
    try:
        is_connected, _ = await ble_service.is_connected()
        if not is_connected:
            raise HTTPException(status_code=400, detail="No device connected")
        
        services = await ble_service.get_services()
        if not services:
            return Response(content=json.dumps({"services": [], "count": 0, "message": "No services found"}, default=str), media_type="application/json")
        
        return Response(content=json.dumps({"services": services, "count": len(services)}, default=str), media_type="application/json")
    except Exception as e:
        logger.error(f"Error getting services: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting services: {str(e)}")

@device_router.get("/services/{service_uuid}/characteristics", response_model=None)
async def get_service_characteristics(
    service_uuid: str,
    ble_service: BleService = Depends(get_ble_service)
):
    """Get characteristics for a specific service."""
    try:
        is_connected, _ = await ble_service.is_connected()
        if not is_connected:
            raise HTTPException(status_code=400, detail="No device connected")
        
        characteristics = await ble_service.get_characteristics(service_uuid)
        return Response(content=json.dumps({"characteristics": characteristics, "count": len(characteristics)}, default=str), media_type="application/json")
    except Exception as e:
        logger.error(f"Error getting characteristics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Data exchange endpoints
@device_router.get("/read/{characteristic}", response_model=None)
async def read_characteristic(
    characteristic: str,
    ble_service: BleService = Depends(get_ble_service)
):
    """Read a value from a characteristic."""
    try:
        is_connected, _ = await ble_service.is_connected()
        if not is_connected:
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
            
            return Response(content=json.dumps(result.model_dump(), default=str), media_type="application/json")
        
        return Response(content=json.dumps({"value": value}, default=str), media_type="application/json")
    except Exception as e:
        logger.error(f"Error reading characteristic: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.post("/write", response_model=None)
async def write_characteristic(
    request: WriteRequest,
    ble_service: BleService = Depends(get_ble_service)
):
    """Write a value to a characteristic."""
    try:
        is_connected, _ = await ble_service.is_connected()
        if not is_connected:
            raise HTTPException(status_code=400, detail="No device connected")
        
        # Write the value
        result = await ble_service.write_characteristic(
            request.characteristic, 
            request.value, 
            value_type=request.value_type,
            with_response=request.response
        )
        
        return Response(content=json.dumps({"status": "success", "written": request.value}, default=str), media_type="application/json")
    except Exception as e:
        logger.error(f"Error writing characteristic: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.post("/notify", response_model=None)
async def enable_notifications(
    request: NotificationRequest,  
    ble_service: BleService = Depends(get_ble_service)
):
    """Enable or disable notifications for a characteristic."""
    try:
        is_connected, _ = await ble_service.is_connected()
        if not is_connected:
            raise HTTPException(status_code=400, detail="No device connected")
        
        if request.enable:
            result = await ble_service.start_notify(request.characteristic)
            status = "enabled"
        else:
            result = await ble_service.stop_notify(request.characteristic)
            status = "disabled"
        
        return Response(content=json.dumps({
            "status": status, 
            "characteristic": request.characteristic,
            "success": result
        }, default=str), media_type="application/json")
    except Exception as e:
        logger.error(f"Error with notifications: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.post("/pair", response_model=None)
async def pair_device(
    request: DevicePairRequest,
    ble_service: BleService = Depends(get_ble_service)
):
    """Initiate pairing with a device."""
    try:
        result = await ble_service.pair_device(request.address, timeout=request.timeout)
        
        if result:
            return Response(content=json.dumps({"status": "paired", "device": request.address}, default=str), media_type="application/json")
        else:
            raise HTTPException(status_code=400, detail=f"Failed to pair with device {request.address}")
    except Exception as e:
        logger.error(f"Pairing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.post("/bond", response_model=None)
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
            return Response(content=json.dumps({"status": "bonded", "device": request.address}, default=str), media_type="application/json")
        else:
            raise HTTPException(status_code=400, detail=f"Failed to bond with device {request.address}")
    except Exception as e:
        logger.error(f"Bonding error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.delete("/bond/{address}", response_model=None)
async def remove_bonded_device(
    address: str,
    ble_service: BleService = Depends(get_ble_service)
):
    """Remove a bonded device."""
    try:
        result = await ble_service.remove_bonded_device(address)
        
        if result:
            return Response(json.dumps({"status": "removed", "device": address}, default=str), media_type="application/json")
        else:
            raise HTTPException(status_code=400, detail=f"Failed to remove bonded device {address}")
    except Exception as e:
        logger.error(f"Error removing bond: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.get("/info", response_model=None)
async def get_device_info(ble_service: BleService = Depends(get_ble_service)):
    """Get information about the connected device."""
    try:
        is_connected, connected_address = await ble_service.is_connected()
        if not is_connected:
            raise HTTPException(status_code=400, detail="No device connected")
        
        info = await ble_service.get_device_info()
        return Response(content=json.dumps(info, default=str), media_type="application/json")
    except Exception as e:
        logger.error(f"Error getting device info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.post("/scan/stop", response_model=None)
async def stop_scan(ble_service: BleService = Depends(get_ble_service)):
    """Stop an ongoing BLE scan."""
    try:
        logger.info("Request to stop scan received")
        result = await ble_service.stop_scan()
        
        # Send WebSocket update if possible
        try:
            from backend.modules.ble.comms.websocket import broadcast_message
            await broadcast_message({
                "type": "scan_status",
                "status": "stopped",
                "message": "Scan stopped by user request",
                "timestamp": int(time.time() * 1000)
            })
        except Exception as ws_err:
            logger.warning(f"Could not broadcast scan stop event: {ws_err}")
        
        return Response(content=json.dumps(result, default=str), 
                        media_type="application/json")
    except Exception as e:
        logger.error(f"Error stopping scan: {e}", exc_info=True)
        return Response(
            content=json.dumps({
                "status": "error",
                "message": f"Failed to stop scan: {str(e)}"
            }, default=str),
            media_type="application/json",
            status_code=500
        )
