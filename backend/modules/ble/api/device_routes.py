"""Bluetooth device-related routes."""
import logging
import asyncio
import json
from bleak import BleakScanner
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path, Response
from pydantic import BaseModel, Field

from backend.dependencies import get_ble_service, get_ble_metrics
from backend.modules.ble.core.ble_service import BleService
from backend.modules.ble.core.ble_metrics import BleMetricsCollector
from backend.modules.ble.models.ble_models import (
    BLEDeviceInfo, ConnectionParams, ConnectionResult, ConnectionStatus,
    WriteRequest, NotificationRequest, ServiceFilterRequest,
    DevicePairRequest, DeviceBondRequest, ScanParams,
    CharacteristicValue, ReadResult
)
from backend.modules.ble.models.ble_models import DeviceResponse

# Create a single router definition
device_router = APIRouter(prefix="/devices", tags=["BLE Devices"])

# Get logger
logger = logging.getLogger(__name__)

# Device list and scanning endpoints
@device_router.get("/", response_model=List[DeviceResponse])
async def get_devices(
    ble_service: BleService = Depends(get_ble_service),
    filter_name: Optional[str] = Query(None, description="Filter devices by name")
):
    """Get a list of BLE devices."""
    try:
        devices = await ble_service.get_devices()
        
        # Apply filter if provided
        if filter_name:
            devices = [d for d in devices if filter_name.lower() in d.get("name", "").lower()]
            
        return devices
    except Exception as e:
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

@device_router.post("/scan", response_model=None)
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
        
        return Response(content=json.dumps({
            "devices": devices,
            "count": len(devices),
            "mock": params.mock,
            "real_scan": real_scan
        }, default=str), media_type="application/json")
    except Exception as e:
        logger.error(f"Error during scan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.post("/scan", response_model=None)
async def start_scan(
    params: ScanParams = Body(default_factory=lambda: ScanParams()),
    ble_service: BleService = Depends(get_ble_service)
):
    """Start a BLE device scan."""
    try:
        # Start the scan with parameters
        result = await ble_service.start_scan(
            timeout=params.timeout,
            service_uuids=params.service_uuids,
            continuous=params.continuous
        )
        
        return Response(content=json.dumps({
            "status": "started",
            "message": "Scan started successfully",
            "timeout": params.timeout,
            "continuous": params.continuous
        }, default=str), media_type="application/json")
    except Exception as e:
        logger.error(f"Error starting scan: {e}", exc_info=True)
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
            "devices": [model.dict() for model in device_models],
            "count": len(device_models)
        }, default=str), media_type="application/json")
    except Exception as e:
        logger.error(f"Error listing devices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Device connection and management endpoints
@device_router.post("/connect", response_model=None)
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
        
        return Response(content=json.dumps(connection_result.dict(), default=str), media_type="application/json")
    except Exception as e:
        logger.error(f"Error connecting to device: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.post("/disconnect", response_model=None)
async def disconnect_device(ble_service: BleService = Depends(get_ble_service)):
    """Disconnect from the currently connected device."""
    try:
        if not ble_service.is_connected():
            return Response(content=json.dumps({"status": "not_connected", "message": "No device is currently connected"}, default=str), media_type="application/json")
        
        device_address = ble_service.get_connected_device_address()
        await ble_service.disconnect_device()
        
        return Response(content=json.dumps({"status": "disconnected", "device": device_address}, default=str), media_type="application/json")
    except Exception as e:
        logger.error(f"Disconnect error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@device_router.get("/status", response_model=None)
async def check_connection_status(ble_service: BleService = Depends(get_ble_service)):
    """Check if a device is currently connected."""
    try:
        is_connected = ble_service.is_connected()
        device_address = ble_service.get_connected_device_address() if is_connected else None
        uptime = ble_service.get_connection_uptime() if is_connected else None
        
        return Response(content=json.dumps({
            "connected": is_connected,
            "device": device_address,
            "uptime": uptime
        }, default=str), media_type="application/json")
    except Exception as e:
        logger.error(f"Error checking connection status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error checking connection status: {str(e)}")

@device_router.get("/{device_id}/exists", response_model=None)
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
        if not ble_service.is_connected():
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
        if not ble_service.is_connected():
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
            
            return Response(content=json.dumps(result.dict(), default=str), media_type="application/json")
        
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
        if not ble_service.is_connected():
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
        if not ble_service.is_connected():
            raise HTTPException(status_code=400, detail="No device connected")
        
        info = await ble_service.get_device_info()
        return Response(content=json.dumps(info, default=str), media_type="application/json")
    except Exception as e:
        logger.error(f"Error getting device info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))