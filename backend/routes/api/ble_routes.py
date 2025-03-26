from fastapi import APIRouter, HTTPException, Body, Depends, WebSocket, status, Request  # noqa: F401
from fastapi.templating import Jinja2Templates
from typing import Dict, Any, List, Optional, Set  # noqa: F401
import logging  # noqa: F401
import asyncio
import os
from pydantic import BaseModel, Field
from backend.logging.logging_config import get_api_logger
from backend.modules.ble_manager import BLEManager as BleService
from backend.modules.monitors import monitoring_manager, BLEDeviceMonitor  # noqa: F401
from backend.ws.manager import manager
from backend.ws.factory import websocket_factory  # noqa: F401
from backend.ws.events import create_event
from bleak.exc import BleakError

# Import all the Pydantic models
from backend.routes.api.ble_models import (
    ScanOptions, ConnectionOptions, WriteOptions, BatteryInfo,  # noqa: F401
    StatusResponse, ErrorResponse, BLEDeviceInfo, ServiceInfo,
    CharacteristicInfo, CharacteristicValue
)

from backend.modules.ble_persistence import BLEDeviceStorage
from backend.modules.ble_recovery import BleErrorRecovery
from backend.modules.ble_metrics import BleMetricsCollector

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

def get_ble_service():
    return BleService(logger=get_api_logger())

def get_ble_metrics():
    """Dependency for BLE metrics collector."""
    return BleMetricsCollector(logger=get_api_logger())

def get_ble_recovery():
    """Dependency for BLE error recovery."""
    return BleErrorRecovery(logger=get_api_logger())

class BleServiceAdapter:
    def __init__(self, service: BleService, 
                 recovery: BleErrorRecovery = None, 
                 metrics: BleMetricsCollector = None):
        self.service = service
        self.device_address = None
        self.client = None  # Initialize client to None
        self._reconnect_task = None
        self.auto_reconnect = False
        self.recovery = recovery or BleErrorRecovery(logger=get_api_logger())
        self.metrics = metrics or BleMetricsCollector(logger=get_api_logger())
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.update_device_address())
            else:
                logger.warning("No running event loop, adapter may have limited functionality")
        except RuntimeError:
            logger.warning("No running event loop, cannot update device address")

    async def update_device_address(self):
        """Update internal client and device address properties."""
        try:
            if self.service.client and self.service.client.is_connected:
                self.client = self.service.client
                self.device_address = self.service.device_address
                self.logger.info(f"Updated device address to {self.device_address}")
            else:
                self.client = None
                self.device_address = None
                self.logger.info("Cleared device address (no active connection)")
        except Exception as e:
            self.logger.error(f"Error updating device address: {e}")
            self.device_address = None
            self.client = None
    
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
    ble_service: BleService = Depends(get_ble_service),
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

# HTTP route handlers
@router.get("/scan", response_model=List[BLEDeviceInfo])
async def scan_for_devices(
    scan_time: int = 5, 
    active: bool = True, 
    ble_service: BleService = Depends(get_ble_service)
):
    """
    Scan for nearby BLE devices using GET parameters.
    
    This is the original scan endpoint that accepts query parameters.
    """
    logger.info(f"Starting BLE device scan (mode: {'active' if active else 'passive'})...")
    try:
        devices = await ble_service.scan_devices(scan_time, active)
        return devices
    except Exception as e:
        logger.error(f"Failed to scan BLE devices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scan", response_model=List[BLEDeviceInfo])
async def scan_ble_devices(
    options: ScanOptions,
    ble_service: BleService = Depends(get_ble_service)
):
    """Scan for BLE devices with custom options provided in the request body."""
    try:
        logger.info(f"Starting BLE scan (duration: {options.duration}s, active: {options.activeMode})")
        
        devices = await ble_service.scan_devices(options.duration, options.activeMode)
        return devices
    except BleakError as e:
        logger.error(f"BLE scan error: {e}")
        raise HTTPException(status_code=500, detail=f"BLE scan failed: {str(e)}")
    except Exception as e:
        logger.error(f"Error during BLE scan: {e}")
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")

@router.post("/connect/{address}", response_model=StatusResponse)
async def connect_to_device(
    address: str, 
    options: ConnectionOptions = Body(default=ConnectionOptions()),
    ble_adapter: BleServiceAdapter = Depends(get_ble_adapter),
    metrics: BleMetricsCollector = Depends(get_ble_metrics),
    recovery: BleErrorRecovery = Depends(get_ble_recovery)
):
    """
    Connect to a BLE device with the specified address.
    Uses error recovery for improved reliability.
    """
    try:
        if not address:
            raise HTTPException(status_code=400, detail="Invalid device address")
        
        # Record metrics for this connection attempt
        op_id = metrics.record_connect_start(address)
        
        # Use the enhanced connection method with recovery
        success = await ble_adapter.connect_with_recovery(address)
            
        if success:
            # Enable auto-reconnect if requested
            if options.autoReconnect:
                await ble_adapter.enable_auto_reconnect(True)
                
            logger.info(f"Connected to BLE device at {address}")
            
            # Record successful connection in metrics
            metrics.record_connect_complete(op_id, address, True)
            
            # Check device bonding status and update metrics if needed
            storage = BLEDeviceStorage(logger=get_api_logger())
            device_info = storage.get_device(address)
            if device_info and device_info.get("bonded", False):
                metrics.record_bonded_connection(address)
            
            return StatusResponse(status="connected", message=f"Connected to device at {address}")
        
        # If connection failed even with recovery
        metrics.record_connect_complete(op_id, address, False)
        recovery.record_error("ConnectionError", f"Failed to connect to {address} after recovery attempts")
        
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to connect to device at {address} after multiple attempts"
        )
    except BleakError as e:
        # Record specific BLE errors for analysis
        metrics.record_connect_error(address, "BleakError")
        recovery.record_error("BleakError", str(e))
        logger.error(f"BLE error connecting to device: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"BLE connection failed: {str(e)}")
    except Exception as e:
        # Record general errors
        metrics.record_connect_error(address, type(e).__name__)
        recovery.record_error(type(e).__name__, str(e))
        logger.error(f"Error connecting to BLE device: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")

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
    """Dependency for BLE device storage."""
    return BLEDeviceStorage(logger=get_api_logger())

@router.get("/devices/bonded", response_model=List[BLEDeviceInfo])
async def get_bonded_devices(
    storage: BLEDeviceStorage = Depends(get_device_storage)
):
    """Get all bonded BLE devices."""
    return storage.get_bonded_devices()

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
    ble_service: BleService = Depends(get_ble_service)
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
async def reset_adapter(
    recovery: BleErrorRecovery = Depends(get_ble_recovery)
):
    """Reset the Bluetooth adapter to recover from serious errors."""
    try:
        success = await recovery.reset_adapter()
        
        if success:
            return StatusResponse(
                status="success",
                message="Bluetooth adapter reset successfully"
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to reset Bluetooth adapter"
            )
    except Exception as e:
        logger.error(f"Error resetting Bluetooth adapter: {e}")
        raise HTTPException(status_code=500, detail=str(e))