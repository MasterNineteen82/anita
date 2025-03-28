from fastapi import APIRouter, HTTPException, Body, Depends, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from typing import Dict, Any, List, Optional
import asyncio
import os
import time
import platform
import bleak
import subprocess
from httpx import get
from pydantic import BaseModel, Field
import logging
import pkg_resources
import json
from datetime import datetime

from backend.logging.logging_config import get_api_logger
# from backend.modules.ble.ble_manager import BLEManager as BleService
from backend.modules.monitors import monitoring_manager
from backend.ws.manager import manager
from backend.ws.events import create_event
from bleak.exc import BleakError

from backend.modules.ble.ble_persistence import BLEDeviceStorage
from backend.modules.ble.ble_models import BLEDeviceConnection
from backend.modules.ble.ble_recovery import BleErrorRecovery
from backend.modules.ble.ble_metrics import BleMetricsCollector
from backend.modules.ble.ble_persistence import get_persistence_service
from backend.modules.ble.ble_service import get_ble_service
from backend.modules.ble.ble_service import BleService

# Import all the Pydantic models
from backend.modules.ble.ble_models import (
    ScanOptions, WriteOptions, StatusResponse, ErrorResponse, 
    BLEDeviceInfo, ServiceInfo, CharacteristicInfo, CharacteristicValue, ConnectionResponse, ConnectionParams, BLEDeviceStorage,
)

router = APIRouter(
    prefix="/api/ble",
    tags=["bluetooth"],
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
templates = Jinja2Templates(directory=os.getenv("TEMPLATE_DIR", "frontend/templates"))
logger = get_api_logger()

def get_ble_metrics():
    """Dependency for BLE metrics collector."""
    # Check if BleMetricsCollector accepts a logger parameter
    try:
        return BleMetricsCollector(logger=get_api_logger())
    except TypeError:
        return BleMetricsCollector()

def get_ble_recovery():
    """Dependency for BLE error recovery."""
    # Check if BleErrorRecovery accepts a logger parameter
    try:
        return BleErrorRecovery(logger=get_api_logger())
    except TypeError:
        return BleErrorRecovery()

async def get_device_storage() -> BLEDeviceStorage:
    """Dependency to get BLE device storage service."""
    # Initialize with logging
    logger = get_api_logger()
    return BLEDeviceStorage(logger=logger)

class BleServiceAdapter:
    def __init__(self, service: BleService, 
             recovery: BleErrorRecovery = None, 
             metrics: BleMetricsCollector = None):
        self.service = service
        self.device_address = None
        self.client = None  # Initialize client to None
        self._reconnect_task = None
        self.auto_reconnect = False
        
        # Initialize recovery with fallback
        if recovery:
            self.recovery = recovery
        else:
            try:
                self.recovery = BleErrorRecovery(logger=get_api_logger())
            except TypeError:
                self.recovery = BleErrorRecovery()
        
        # Initialize metrics with fallback
        if metrics:
            self.metrics = metrics
        else:
            try:
                self.metrics = BleMetricsCollector(logger=get_api_logger())
            except TypeError:
                self.metrics = BleMetricsCollector()
        
        # Get logger
        self.logger = get_api_logger()
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.update_device_address())
            else:
                self.logger.warning("No running event loop, adapter may have limited functionality")
        except RuntimeError:
            self.logger.warning("No running event loop, cannot update device address")
    
    async def enable_auto_reconnect(self, enable: bool = True):
        """Enable or disable auto-reconnect functionality."""
        self.auto_reconnect = enable
        
        # If enabling and we're already connected, store the current address for reconnect
        if enable and self.device_address:
            logger.info(f"Auto-reconnect enabled for device {self.device_address}")
            
            # Cancel any existing reconnect task
            if self._reconnect_task and not self._reconnect_task.done():
                self._reconnect_task.cancel()
                
            # Start monitoring connection status for reconnection
            self._reconnect_task = asyncio.create_task(self._monitor_connection())
        elif not enable and self._reconnect_task and not self._reconnect_task.done():
            # Cancel the reconnect task if disabling
            logger.info("Auto-reconnect disabled")
            self._reconnect_task.cancel()
            self._reconnect_task = None
    
    async def _monitor_connection(self):
        """Monitor connection status and reconnect if needed."""
        last_address = self.device_address
        try:
            while self.auto_reconnect and last_address:
                # Check connection status every 5 seconds
                await asyncio.sleep(5)
                
                # If client is None or not connected, attempt reconnection
                if not self.client or not self.client.is_connected:
                    self.logger.info(f"Auto-reconnect: Connection lost to {last_address}, attempting reconnection")
                    try:
                        success = await self.service.connect_device(last_address)
                        if success:
                            await self.update_device_address()
                            self.logger.info(f"Auto-reconnect: Successfully reconnected to {last_address}")
                        else:
                            self.logger.warning(f"Auto-reconnect: Failed to reconnect to {last_address}")
                    except Exception as e:
                        self.logger.error(f"Auto-reconnect: Error during reconnection: {e}")
        except asyncio.CancelledError:
            self.logger.info("Connection monitoring cancelled")
        except Exception as e:
            self.logger.error(f"Error in connection monitoring: {e}")

    async def connect_with_recovery(self, address: str, max_attempts: int = 3) -> bool:
        """
        Connect to a device with error recovery.
        
        Args:
            address: Device address to connect to
            max_attempts: Maximum number of connection attempts
            
        Returns:
            bool: Whether connection was successful
        """
        op_id = self.metrics.record_connect_start(address)
        
        try:
            # First attempt
            success = await self.service.connect_device(address)
            
            if success:
                await self.update_device_address()
                self.metrics.record_connect_complete(op_id, address, True)
                return True
                
            # If failed, try recovery
            logger.info(f"Initial connection to {address} failed, attempting recovery")
            
            # Use error recovery for subsequent attempts
            success = await self.recovery.recover_connection(
                address, 
                lambda: self.service.connect_device(address)
            )
            
            if success:
                await self.update_device_address()
                self.metrics.record_connect_complete(op_id, address, True)
                return True
                
            # If all recovery attempts failed, try resetting the adapter as last resort
            logger.warning(f"Connection recovery failed for {address}, attempting adapter reset")
            reset_success = await self.recovery.reset_adapter()
            
            if reset_success:
                # One final attempt after reset
                success = await self.service.connect_device(address)
                if success:
                    await self.update_device_address()
                    self.metrics.record_connect_complete(op_id, address, True)
                    return True
            
            # All attempts failed
            self.metrics.record_connect_complete(op_id, address, False)
            return False
            
        except Exception as e:
            logger.error(f"Error during connection with recovery: {e}")
            self.metrics.record_connect_error(address, type(e).__name__)
            self.metrics.record_connect_complete(op_id, address, False)
            return False

def get_ble_adapter(
    ble_service: get_ble_service = Depends(get_ble_service),
    recovery: BleErrorRecovery = Depends(get_ble_recovery),
    metrics: BleMetricsCollector = Depends(get_ble_metrics)
):
    """Get a BLE adapter with error recovery and metrics included."""
    return BleServiceAdapter(
        service=ble_service,
        recovery=recovery,
        metrics=metrics
    )

# WebSocket handler functions
async def subscribe_to_characteristic(websocket, payload: dict, ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)):
    char_uuid = payload.get("char_uuid")
    if not char_uuid:
        await manager.send_error(websocket, "Characteristic UUID is required")
        return
        
    try:
        client_id = manager.get_client_id(websocket)
        if not ble_adapter.device_address:
            await manager.send_error(websocket, "No device connected")
            return
            
        success = await ble_adapter.service.start_notify(char_uuid, lambda char_uuid, value: asyncio.create_task(broadcast_notification(char_uuid, value, client_id, ble_adapter)))
        if success:
            await manager.send_message(websocket, create_event("ble.characteristic_subscription", char_uuid=char_uuid, status="subscribed"))
        else:
            await manager.send_error(websocket, f"Failed to subscribe to characteristic {char_uuid}")
    except Exception as e:
        logger.error(f"Error subscribing to characteristic: {str(e)}")
        await manager.send_error(websocket, f"Error subscribing: {str(e)}")

async def unsubscribe_from_characteristic(websocket, payload: dict, ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)):
    char_uuid = payload.get("char_uuid")
    if not char_uuid:
        await manager.send_error(websocket, "Characteristic UUID is required")
        return
        
    try:
        if not ble_adapter.device_address:
            await manager.send_error(websocket, "No device connected")
            return
            
        success = await ble_adapter.service.stop_notify(char_uuid)
        if success:
            await manager.send_message(websocket, create_event("ble.characteristic_subscription", char_uuid=char_uuid, status="unsubscribed"))
        else:
            await manager.send_error(websocket, f"Failed to unsubscribe from characteristic {char_uuid}")
    except Exception as e:
        logger.error(f"Error unsubscribing from characteristic: {str(e)}")
        await manager.send_error(websocket, f"Error unsubscribing: {str(e)}")

async def broadcast_notification(char_uuid: str, value: bytes, client_id: str, ble_adapter: BleServiceAdapter):
    try:
        if not ble_adapter.device_address:
            logger.warning("No device connected, cannot broadcast notification")
            return
            
        service_uuid = ble_adapter.service.get_service_for_characteristic(char_uuid) or "unknown"
        
        # Try to decode value for common characteristics
        decoded_value = None
        try:
            # Simple decoding for common characteristics
            if char_uuid.lower() == "00002a19-0000-1000-8000-00805f9b34fb":  # Battery Level
                decoded_value = int(value[0])
            elif char_uuid.lower() == "00002a29-0000-1000-8000-00805f9b34fb":  # Manufacturer Name
                decoded_value = value.decode('utf-8')
            else:
                # Default to hex representation for unknown characteristics
                decoded_value = value.hex()
        except Exception as e:
            logger.warning(f"Error decoding characteristic value: {e}")
            decoded_value = value.hex()  # Fall back to hex representation
        
        # Create and send notification event to client
        event = create_event(
            "ble.notification", 
            char_uuid=char_uuid,
            service_uuid=service_uuid,
            value=value.hex(),
            decoded_value=decoded_value
        )
        
        # Send to specific client or broadcast to all if client_id is None
        if client_id:
            await manager.send_to_client(client_id, event)
        else:
            await manager.broadcast(event, room="ble_notifications")
            
    except Exception as e:
        logger.error(f"Error broadcasting notification: {e}")

# WebSocket endpoint
async def ble_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for BLE notifications."""
    await manager.connect(websocket)
    
    try:
        # Register handlers for this specific endpoint
        handlers = {
            "subscribe_to_characteristic": subscribe_to_characteristic,
            "unsubscribe_from_characteristic": unsubscribe_from_characteristic,
            "ping": lambda ws, _: asyncio.create_task(manager.send_message(ws, {"type": "pong"}))
        }
        
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type in handlers:
                # Call the appropriate handler
                await handlers[message_type](websocket, data)
            else:
                # Unknown message type
                await manager.send_error(websocket, f"Unknown message type: {message_type}")
                
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        await manager.disconnect(websocket)

@router.post("/scan", response_model=dict)
async def scan_for_devices(
    options: ScanOptions = Body(default=None),  # Optional structured options
    scan_params: dict = Body(default=None),     # Optional free-form params
    ble_service: BleService = Depends(get_ble_service),
    metrics: BleMetricsCollector = Depends(get_ble_metrics)
):
    """
    Scan for BLE devices with flexible parameters.
    
    Args:
        options: Structured scan options (ScanOptions model)
        scan_params: Dict with scan parameters (alternative to options)
        
    Returns:
        dict containing devices list, scan duration, and parameters used
    """
    try:
        # Record scan start for metrics
        scan_start_id = metrics.record_scan_start()
        
        # Determine parameters from either options or scan_params
        if options and scan_params:
            raise HTTPException(
                status_code=400,
                detail="Provide either options or scan_params, not both"
            )
            
        # Extract and validate parameters
        if options:
            duration = options.duration
            active = options.activeMode
            name_prefix = getattr(options, 'name_prefix', '')
            services = getattr(options, 'services', [])
            params_source = "structured"
        else:
            scan_params = scan_params or {}
            duration = scan_params.get('duration', 5)
            active = scan_params.get('active', True)
            name_prefix = scan_params.get('name_prefix', '')
            services = scan_params.get('services', [])
            params_source = "dict"

        # Validate duration to avoid excessive scans
        if duration < 1:
            duration = 1
        elif duration > 30:
            duration = 30  # Limit maximum scan time

        # Log scan start
        logger.info(
            f"Starting BLE scan (duration: {duration}s, "
            f"active: {active}, source: {params_source})"
        )
        
        # Record scan start time
        start_time = time.time()
        
        # Create a filtered dict of supported parameters only
        # This avoids the "unexpected keyword argument" error
        scan_params_filtered = {
            "scan_time": duration,
            "active": active
        }
        
        # Only add optional parameters if they have values
        if name_prefix:
            scan_params_filtered["name_prefix"] = name_prefix
        if services:
            scan_params_filtered["services"] = services
        
        # Explicitly *don't* include allow_duplicates
        
        # Perform the scan with only supported parameters
        devices = await ble_service.scan_devices(**scan_params_filtered)
        
        # Process devices into a consistent format
        processed_devices = []
        for device in devices:
            # Handle different types of device objects
            if isinstance(device, str):
                processed_devices.append({
                    "address": device,
                    "name": "Unknown Device",
                    "rssi": -100
                })
            elif isinstance(device, dict):
                # If it's a dict, extract data directly
                processed_devices.append({
                    "address": device.get("address", "Unknown"),
                    "name": device.get("name", "Unknown Device"),
                    "rssi": device.get("rssi", -100),
                    "manufacturer_data": device.get("manufacturer_data", {}),
                    "service_data": device.get("service_data", {}),
                    "services": device.get("services", [])
                })
            else:
                # For object-based device representation
                if not hasattr(device, 'address'):
                    logger.warning(f"Device missing address: {device}")
                    continue
                    
                processed_devices.append({
                    "address": device.address,
                    "name": getattr(device, 'name', "Unknown Device"),
                    "rssi": getattr(device, 'rssi', -100),
                    "manufacturer_data": getattr(device, 'manufacturer_data', {}),
                    "service_data": getattr(device, 'service_data', {}),
                    "services": getattr(device, 'services', [])
                })
        
        # Calculate duration
        scan_duration = time.time() - start_time
        
        # Record metrics with detailed information
        metrics.record_scan_complete(scan_start_id, len(processed_devices))
        metrics.record_scan(scan_duration, len(processed_devices))
        
        # Log results (limit log size for large scans)
        if len(processed_devices) > 10:
            device_log = f"{len(processed_devices)} devices (showing first 10): {processed_devices[:10]}"
        else:
            device_log = f"{len(processed_devices)} devices: {processed_devices}"
            
        logger.info(
            f"BLE scan completed. Found {len(processed_devices)} "
            f"device(s) in {scan_duration:.2f}s"
        )
        logger.debug(f"Devices found: {device_log}")
        
        # Return detailed response
        return {
            "devices": processed_devices,
            "scan_time": scan_duration,
            "count": len(processed_devices),
            "parameters_used": {
                "duration": duration,
                "active": active,
                "name_prefix": name_prefix,
                "services": services
            }
        }
        
    except Exception as e:
        # Log the full exception with traceback
        logger.exception(f"Scan failed: {str(e)}")
        
        # Record metrics for the error
        if 'scan_start_id' in locals():
            metrics.record_scan_error(type(e).__name__)
        
        # Specific error handling
        error_str = str(e).lower()
        if "cannot find any bluetooth adapter" in error_str or "adapter not found" in error_str:
            raise HTTPException(
                status_code=503,
                detail="Bluetooth adapter not available"
            )
        elif "access denied" in error_str or "permission" in error_str:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions to access Bluetooth adapter"
            )
        elif "timeout" in error_str:
            raise HTTPException(
                status_code=504,
                detail=f"Scan timed out: {str(e)}"
            )
        elif "already in progress" in error_str or "busy" in error_str:
            raise HTTPException(
                status_code=409,
                detail="Another scan is already in progress"
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Scan failed: {str(e)}"
            )

#...
@router.post("/connect", response_model=BLEDeviceConnection)
async def connect_to_last_device(
    connection_params: ConnectionParams = Body(default=ConnectionParams(timeout=10, autoReconnect=True, retryCount=2)),
    ble_service: BleService = Depends(get_ble_service),
    metrics: BleMetricsCollector = Depends(get_ble_metrics),
    recovery: BleErrorRecovery = Depends(get_ble_recovery),
    storage: BLEDeviceStorage = Depends(get_device_storage)
):
    """
    Connect to the last used BLE device or return an error if no last device is available.
    
    Args:
        connection_params: Connection parameters (timeout, autoReconnect, retryCount)
    """
    try:
        logger = get_api_logger()
        logger.info("Attempting to connect to last used device")
        
        # Try to get the last used device address from storage
        last_device = await storage.get_last_device()
        
        if not last_device or "address" not in last_device:
            logger.warning("No last device found to connect to")
            raise HTTPException(
                status_code=404, 
                detail="No previously connected device available. Please specify an address."
            )
            
        # Use the address from the last device
        address = last_device["address"]
        logger.info(f"Connecting to last used device with address: {address}")
        
        # Start metrics recording
        op_id = metrics.record_connect_start(address)
        
        # Try to connect
        success = await ble_service.connect_device(address)
        
        if success:
            # Update metrics
            metrics.record_connect_complete(op_id, address, True)
            
            # Get device info
            device_info = {
                "address": address,
                "name": await ble_service.get_device_name() if hasattr(ble_service, "get_device_name") else "Unknown Device",
                "connected": True,
                "auto_reconnect": connection_params.autoReconnect
            }
            
            # Set auto-reconnect if requested
            if connection_params.autoReconnect and hasattr(ble_service, "enable_auto_reconnect"):
                await ble_service.enable_auto_reconnect(True)
            
            # Return device connection info
            return BLEDeviceConnection(**device_info)
        else:
            # If direct connection failed, try recovery
            logger.info(f"Initial connection to {address} failed, attempting recovery")
            
            # Use error recovery
            adapter = BleServiceAdapter(
                service=ble_service,
                recovery=recovery,
                metrics=metrics
            )
            
            recovery_success = await adapter.connect_with_recovery(address, max_attempts=connection_params.retryCount)
            
            if recovery_success:
                device_info = {
                    "address": address,
                    "name": await ble_service.get_device_name() if hasattr(ble_service, "get_device_name") else "Unknown Device",
                    "connected": True,
                    "auto_reconnect": connection_params.autoReconnect
                }
                return BLEDeviceConnection(**device_info)
            else:
                metrics.record_connect_complete(op_id, address, False)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to connect to device at {address} after recovery attempts"
                )
        
    except HTTPException:
        raise
    except Exception as e:
        logger = get_api_logger()
        logger.error(f"Unexpected error connecting to last device: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to connect to last device: {str(e)}"
        )

# Add this helper function to check if device exists in recent scans
async def device_exists(address: str, ble_adapter: BleServiceAdapter) -> bool:
    """Check if a device with the given address exists by doing a quick scan."""
    try:
        # Do a quick scan to see if the device is around
        devices = await ble_adapter.service.scan_devices(scan_time=2, active=True)
        return any(d.get("address") == address for d in devices)
    except Exception as e:
        logger.warning(f"Error checking for device existence: {e}")
        # Default to true so we at least try to connect
        return True

@router.post("/disconnect", response_model=StatusResponse)
async def disconnect_ble_device(ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)):
    """
    Disconnect from the connected BLE device.
    """
    if not ble_adapter.client or not ble_adapter.client.is_connected:
        raise HTTPException(status_code=400, detail="Not connected to a device")
        
    try:
        # Disable auto-reconnect first
        await ble_adapter.enable_auto_reconnect(False)
        
        # Then disconnect
        await ble_adapter.service.disconnect_device()
        return StatusResponse(status="success", message="Disconnected from device")
    except Exception as e:
        logger.error(f"Error disconnecting: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/services", response_model=List[ServiceInfo])
async def get_ble_services(ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)):
    """
    Retrieve the services offered by the connected BLE device.
    """
    if not ble_adapter.client or not ble_adapter.client.is_connected:
        raise HTTPException(status_code=400, detail="Not connected to a device")
        
    try:
        services = await ble_adapter.service.get_services()
        return services
    except Exception as e:
        logger.error(f"Error getting services: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/services/{service_uuid}/characteristics", response_model=List[CharacteristicInfo])
async def get_service_characteristics(
    service_uuid: str,
    ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)
):
    """
    Retrieve characteristics for a specific service.
    """
    if not ble_adapter.client or not ble_adapter.client.is_connected:
        raise HTTPException(status_code=400, detail="Not connected to a device")
        
    try:
        characteristics = await ble_adapter.service.get_characteristics(service_uuid)
        return characteristics
    except Exception as e:
        logger.error(f"Error getting characteristics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/characteristics/{char_uuid}/read", response_model=CharacteristicValue)
async def read_characteristic(
    char_uuid: str,
    ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)
):
    """
    Read value from a specific characteristic.
    """
    if not ble_adapter.client or not ble_adapter.client.is_connected:
        raise HTTPException(status_code=400, detail="Not connected to a device")
        
    try:
        value = await ble_adapter.service.read_characteristic(char_uuid)
        
        # Try to decode the value for common characteristics
        decoded = None
        try:
            # Decode based on characteristic UUID
            if char_uuid.lower() == "00002a19-0000-1000-8000-00805f9b34fb":  # Battery Level
                decoded = int(value[0])
            elif char_uuid.lower() == "00002a29-0000-1000-8000-00805f9b34fb":  # Manufacturer Name
                decoded = value.decode('utf-8')
            else:
                # Default to hex string for unknown characteristics
                decoded = value.hex()
        except Exception:
            decoded = value.hex()
        
        return CharacteristicValue(
            uuid=char_uuid,
            value=value.hex(),
            decoded=decoded
        )
    except Exception as e:
        logger.error(f"Error reading characteristic {char_uuid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/characteristics/{char_uuid}/write", response_model=StatusResponse)
async def write_characteristic(
    char_uuid: str,
    options: WriteOptions,
    ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)
):
    """Write a value to a specific characteristic."""
    if not ble_adapter.client or not ble_adapter.client.is_connected:
        raise HTTPException(status_code=400, detail="Not connected to a device")
        
    try:
        # Convert hex string to bytes
        value_bytes = bytes.fromhex(options.value)
        
        # Write to the characteristic
        success = await ble_adapter.service.write_characteristic(
            char_uuid, 
            value_bytes, 
            with_response=options.withResponse
        )
        
        if success:
            return StatusResponse(
                status="success", 
                message=f"Value written to characteristic {char_uuid}"
            )
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to write to characteristic {char_uuid}"
            )
    except ValueError as e:
        # Handle invalid hex string
        raise HTTPException(status_code=400, detail=f"Invalid hex value: {str(e)}")
    except Exception as e:
        logger.error(f"Error writing to characteristic {char_uuid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def get_device_storage():
    """Get the device storage singleton."""
    persistence = get_persistence_service()
    return persistence

@router.get("/devices/bonded", response_model=list)
async def get_bonded_devices():
    """Get a list of bonded BLE devices."""
    try:
        # Mock bonded devices (replace with actual bonded device retrieval logic)
        bonded_devices = [
            {"address": "00:11:22:33:44:55", "name": "Device 1"},
            {"address": "66:77:88:99:AA:BB", "name": "Device 2"}
        ]
        return bonded_devices
    except Exception as e:
        logger.error(f"Failed to get bonded devices: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/devices/{address}/bond", response_model=StatusResponse)
async def bond_device(
    address: str,
    storage: BLEDeviceStorage = Depends(get_device_storage),
    ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)
):
    """Bond with a BLE device."""
    try:
        # First ensure we're connected
        if not ble_adapter.client or not ble_adapter.client.is_connected or ble_adapter.device_address != address:
            # Connect if not already connected
            connected = await ble_adapter.service.connect_device(address)
            if not connected:
                raise HTTPException(status_code=400, detail=f"Failed to connect to device at {address}")
            await ble_adapter.update_device_address()

        # Store bonding information
        storage.set_bonded(address, True)
        
        return StatusResponse(
            status="bonded",
            message=f"Successfully bonded with device at {address}"
        )
    except Exception as e:
        logger.error(f"Error bonding with device: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/devices/{address}/bond", response_model=StatusResponse)
async def unbond_device(
    address: str,
    storage: BLEDeviceStorage = Depends(get_device_storage)
):
    """Remove bond with a BLE device."""
    try:
        storage.set_bonded(address, False)
        return StatusResponse(
            status="unbonded",
            message=f"Successfully removed bond with device at {address}"
        )
    except Exception as e:
        logger.error(f"Error removing bond: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class MTUOptions(BaseModel):
    """Options for MTU negotiation."""
    size: int = Field(default=217, ge=23, le=517, description="MTU size to negotiate")

class ConnectionParamOptions(BaseModel):
    """Options for connection parameters."""
    minInterval: float = Field(default=7.5, ge=7.5, le=4000.0, description="Minimum connection interval (ms)")
    maxInterval: float = Field(default=30.0, ge=7.5, le=4000.0, description="Maximum connection interval (ms)")
    latency: int = Field(default=0, ge=0, le=500, description="Slave latency (connection events)")
    timeout: int = Field(default=500, ge=100, le=32000, description="Supervision timeout (ms)")

@router.post("/mtu", response_model=Dict[str, int])
async def negotiate_mtu(
    options: MTUOptions,
    ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)
):
    """Negotiate MTU with connected device."""
    if not ble_adapter.client or not ble_adapter.client.is_connected:
        raise HTTPException(status_code=400, detail="Not connected to a device")
        
    try:
        mtu = await ble_adapter.service.negotiate_mtu(options.size)
        return {"mtu": mtu}
    except Exception as e:
        logger.error(f"Error negotiating MTU: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/connection-parameters", response_model=Dict[str, Any])
async def set_connection_parameters(
    options: ConnectionParamOptions,
    ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)
):
    """Set connection parameters for the current connection."""
    if not ble_adapter.client or not ble_adapter.client.is_connected:
        raise HTTPException(status_code=400, detail="Not connected to a device")
        
    try:
        success = await ble_adapter.service.set_connection_parameters(
            min_interval=options.minInterval,
            max_interval=options.maxInterval,
            latency=options.latency,
            timeout=options.timeout
        )
        
        if success:
            # Get the actual parameters after setting
            params = await ble_adapter.service.get_connection_parameters()
            return params
        else:
            raise HTTPException(
                status_code=400, 
                detail="Failed to set connection parameters"
            )
    except Exception as e:
        logger.error(f"Error setting connection parameters: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/connection-parameters", response_model=Dict[str, Any])
async def get_connection_parameters(
    ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)
):
    """Get current connection parameters."""
    if not ble_adapter.client or not ble_adapter.client.is_connected:
        raise HTTPException(status_code=400, detail="Not connected to a device")
        
    try:
        params = await ble_adapter.service.get_connection_parameters()
        return params
    except Exception as e:
        logger.error(f"Error getting connection parameters: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scan-filtered", response_model=List[BLEDeviceInfo])
async def scan_with_filters(
    service_uuids: List[str] = Body(default=None),
    name_filter: str = Body(default=None),
    address_filter: str = Body(default=None),
    scan_time: int = Body(default=5),
    active: bool = Body(default=True),
    ble_service: get_ble_service = Depends(get_ble_service)
):
    """Scan for BLE devices with filters."""
    try:
        logger.info(f"Starting filtered BLE scan (duration: {scan_time}s)")
        
        devices = await ble_service.scan_with_filters(
            service_uuids=service_uuids,
            name_filter=name_filter,
            address_filter=address_filter,
            scan_time=scan_time,
            active=active
        )
        return devices
    except Exception as e:
        logger.error(f"Error during filtered BLE scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Add these routes at the end of the file

@router.get("/metrics", response_model=Dict[str, Any])
async def get_ble_metrics(
    metrics: BleMetricsCollector = Depends(get_ble_metrics),
    recovery: BleErrorRecovery = Depends(get_ble_recovery)
):
    """Get comprehensive BLE metrics and error statistics."""
    try:
        metrics_data = metrics.get_metrics_summary()
        error_stats = recovery.get_error_statistics()
        
        return {
            "metrics": metrics_data,
            "error_statistics": error_stats
        }
    except Exception as e:
        logger.error(f"Error retrieving BLE metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics/summary", response_model=Dict[str, Any])
async def get_ble_metrics_summary(
    metrics: BleMetricsCollector = Depends(get_ble_metrics)
):
    """Get a summary of BLE metrics."""
    return metrics.get_metrics_summary()

@router.get("/metrics/detailed", response_model=Dict[str, Any])
async def get_ble_metrics_detailed(
    metrics: BleMetricsCollector = Depends(get_ble_metrics)
):
    """Get detailed BLE metrics for advanced analysis."""
    return metrics.get_detailed_metrics()

@router.get("/errors/statistics", response_model=Dict[str, Any])
async def get_error_statistics(
    recovery: BleErrorRecovery = Depends(get_ble_recovery)
):
    """Get statistics about BLE errors and recovery attempts."""
    return recovery.get_error_statistics()

@router.post("/recovery/reset-adapter", response_model=StatusResponse)
async def recovery_reset_adapter(
    recovery: BleErrorRecovery = Depends(get_ble_recovery)
):
    """Reset the Bluetooth adapter to recover from serious errors."""
    try:
        # Call the reset adapter method with proper error handling
        result = await recovery.reset_adapter()
        
        if result["status"] == "success":
            return StatusResponse(
                status="success",
                message=result["message"]
            )
        else:
            # Provide detailed error message
            raise HTTPException(
                status_code=500,
                detail=result["message"]
            )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error resetting Bluetooth adapter: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to reset Bluetooth adapter: {str(e)}")

@router.post("/reset-adapter", response_model=Dict[str, Any])
async def reset_adapter(
    ble_service: get_ble_service = Depends(get_ble_service)
):
    """Reset the Bluetooth adapter."""
    try:
        # First get the current adapter state
        adapter_info_before = await ble_service.get_adapter_info()
        
        # In a real implementation, we would reset the adapter here
        # For Windows, this might involve disabling and re-enabling the adapter
        # For Linux, this might involve running 'hciconfig hci0 reset'
        # For macOS, this might involve restarting the Bluetooth service
        
        system_platform = platform.system()
        reset_success = False
        
        try:
            if system_platform == "Windows":
                # This is a mock implementation
                # In reality, we'd use PowerShell or WMI to reset the adapter
                logger.info("Simulating Windows Bluetooth adapter reset")
                await asyncio.sleep(1)  # Simulate reset time
                reset_success = True
                
            elif system_platform == "Linux":
                # In Linux we can actually try to reset the adapter
                logger.info("Attempting Linux Bluetooth adapter reset")
                subprocess.run(["sudo", "hciconfig", "hci0", "reset"], check=False)
                await asyncio.sleep(1)  # Give it time to reset
                reset_success = True
                
            elif system_platform == "Darwin":  # macOS
                # For macOS we'd need admin privileges to restart the service
                logger.info("Simulating macOS Bluetooth service reset")
                await asyncio.sleep(1)  # Simulate reset time
                reset_success = True
        except Exception as e:
            logger.error(f"Error during adapter reset: {e}")
            reset_success = False
        
        # Get the new adapter state
        adapter_info_after = await ble_service.get_adapter_info()
        
        return {
            "success": reset_success,
            "before": adapter_info_before,
            "after": adapter_info_after,
            "message": "Adapter reset successfully" if reset_success else "Adapter reset failed"
        }
    except Exception as e:
        logger.error(f"Error resetting adapter: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/adapter-info", response_model=dict)
async def get_adapter_info(ble_service: BleService = Depends(get_ble_service)):
    """Get information about the BLE adapter."""
    try:
        # Get adapter info from the BleService
        adapter_info = await ble_service.get_adapter_info()
        return adapter_info
    except Exception as e:
        logger = get_api_logger()
        logger.error(f"Failed to get adapter info: {str(e)}", exc_info=True)
        return {
            "available": False,
            "name": "Unknown",
            "address": "Unknown",
            "error": str(e)
        }

@router.get("/device-exists/{device_id}", response_model=Dict[str, bool])
async def check_device_exists(
    device_id: str,
    ble_service: get_ble_service = Depends(get_ble_service)
):
    """Check if a device with the given address exists and is in range."""
    try:
        # First check if device is already connected
        if ble_service.client and ble_service.device_address == device_id and ble_service.client.is_connected:
            return {"exists": True}
            
        # Check cached devices first (faster than scanning)
        cached_device = ble_service.get_cached_device(device_id) if hasattr(ble_service, 'get_cached_device') else None
        if cached_device:
            return {"exists": True}
            
        # Do a quick scan to check if the device is visible
        logger.info(f"Performing quick scan to find device {device_id}")
        devices = await ble_service.scan_devices(scan_time=2, active=True)
        
        # Check if the given address is in the scan results
        exists = any(device.get("address") == device_id for device in devices)
        logger.info(f"Device {device_id} {'found' if exists else 'not found'} in scan")
        
        return {"exists": exists}
    except Exception as e:
        logger.error(f"Error checking device existence: {e}", exc_info=True)
        # Don't raise an exception, just return not found
        return {"exists": False}

@router.get("/adapter", response_model=dict)
async def get_adapter_basic_info(
    ble_service: get_ble_services = Depends(get_ble_service)
):
    """Get basic information about the BLE adapter (fallback endpoint)"""
    try:
        adapter_info = await ble_service.get_adapter_info()
        # Return only basic info for this endpoint
        return {
            "available": adapter_info.get("available", False),
            "name": adapter_info.get("name", "Unknown"),
            "address": adapter_info.get("address", "Unknown")
        }
    except Exception as e:
        logger.error(f"Failed to get basic adapter info: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/services/{device_id}", response_model=List[ServiceInfo])
async def get_services(device_id: str, ble_service: get_ble_services = Depends(get_ble_service)):
    try:
        services = await ble_service.get_services(device_id)
        return services
    except Exception as e:
        logger.error(f"Error fetching services for device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch services: {str(e)}")

# Add this route to register the WebSocket endpoint
@router.websocket("/ws/ble")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for BLE notifications and real-time updates."""
    try:
        await websocket.accept()
        # Add the client to connected clients list
        manager.add_connection(websocket)
        
        try:
            # Keep the connection alive and handle messages
            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    await handle_websocket_message(websocket, message)
                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid JSON data received"
                    })
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}", exc_info=True)
            try:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Server error: {str(e)}"
                })
            except:
                pass
        finally:
            # Remove the client from connected clients
            manager.remove_connection(websocket)
    except Exception as e:
        logger.error(f"WebSocket accept error: {str(e)}", exc_info=True)

    
@router.get("/devices/cached", response_model=List[BLEDeviceInfo])
async def get_cached_devices(
    ble_service: get_ble_services = Depends(get_ble_service)
):
    """Get the list of recently discovered devices without performing a new scan."""
    logger.info("Getting cached devices...")
    try:
        devices = ble_service.get_cached_devices()
        logger.info(f"Cached devices: {devices}")
        return devices
    except Exception as e:
        logger.error(f"Error retrieving cached devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
async def handle_websocket_message(websocket: WebSocket, message: dict, ble_adapter: BleServiceAdapter = None):
    """Handle incoming WebSocket messages and route to appropriate handlers."""
    if not ble_adapter:
        # Get adapter if not provided
        ble_adapter = BleServiceAdapter(service=get_ble_service())
    
    message_type = message.get("type", "unknown")
    
    # Map message types to handler functions
    handlers = {
        "subscribe_to_characteristic": subscribe_to_characteristic,
        "unsubscribe_from_characteristic": unsubscribe_from_characteristic,
        "ping": lambda ws, _: asyncio.create_task(manager.send_message(ws, {"type": "pong"}))
    }
    
    if message_type in handlers:
        # Call the appropriate handler
        await handlers[message_type](websocket, message, ble_adapter)
    else:
        # Unknown message type
        await manager.send_error(websocket, f"Unknown message type: {message_type}")

@router.get("/device/{address}", response_model=BLEDeviceInfo)
async def get_device_info(
    address: str,
    ble_service: get_ble_services = Depends(get_ble_service)
):
    """Get detailed information about a specific BLE device."""
    try:
        # First check if device is connected
        if ble_service.client and ble_service.device_address == address and ble_service.client.is_connected:
            # Get connected device info
            device_info = {
                "address": address,
                "name": await ble_service.get_device_name(),
                "rssi": None,  # RSSI not available for connected devices
                "services": await ble_service.get_services()
            }
            return device_info
            
        # If not connected, check cached devices
        cached_device = ble_service.get_cached_device(address)
        if cached_device:
            return cached_device
            
        # If not in cache, do a quick scan to find it
        devices = await ble_service.scan_devices(scan_time=2, active=True, address_filter=address)
        matching_device = next((d for d in devices if d.get("address") == address), None)
        
        if matching_device:
            return matching_device
        else:
            raise HTTPException(status_code=404, detail=f"Device with address {address} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving device info: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/characteristics/{char_uuid}/subscribe", response_model=StatusResponse)
async def subscribe_to_characteristic_http(
    char_uuid: str,
    ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)
):
    """Subscribe to notifications from a specific characteristic."""
    if not ble_adapter.client or not ble_adapter.client.is_connected:
        raise HTTPException(status_code=400, detail="Not connected to a device")
        
    try:
        success = await ble_adapter.service.start_notify(
            char_uuid, 
            lambda c_uuid, value: asyncio.create_task(
                broadcast_notification(c_uuid, value, None, ble_adapter)
            )
        )
        
        if success:
            return StatusResponse(
                status="success", 
                message=f"Subscribed to characteristic {char_uuid}"
            )
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to subscribe to characteristic {char_uuid}"
            )
    except Exception as e:
        logger.error(f"Error subscribing to characteristic: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/api/ble/diagnostics", response_model=dict)
async def run_ble_diagnostics():
    """Perform diagnostics on the BLE subsystem"""
    try:
        # Get dependencies
        ble_service = get_ble_service()
        persistence_service = get_persistence_service()
        
        diagnostics = {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "services": {
                "ble_manager": True,
                "ble_recovery": True,
                "ble_metrics": True
            },
            "configuration": {},
            "errors": {}
        }
        
        # Check BLE Manager
        try:
            manager_info = await ble_service.get_adapter_info()
            diagnostics["configuration"]["adapter"] = manager_info
        except Exception as e:
            diagnostics["services"]["ble_manager"] = False
            diagnostics["errors"]["ble_manager"] = str(e)
        
        # Check cached devices
        try:
            cached_device_count = len(ble_service.get_cached_devices())
            diagnostics["configuration"]["cached_devices"] = cached_device_count
        except Exception as e:
            diagnostics["errors"]["cached_devices"] = str(e)
            
        # Check bonded devices
        try:
            bonded_devices = await persistence_service.get_bonded_devices()
            diagnostics["configuration"]["bonded_devices"] = len(bonded_devices)
        except Exception as e:
            diagnostics["errors"]["bonded_devices"] = str(e)
            
        return diagnostics
    except Exception as e:
        logger.error(f"Diagnostics failed: {str(e)}", exc_info=True)
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "message": str(e)
        }