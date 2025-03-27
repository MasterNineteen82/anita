from fastapi import APIRouter, HTTPException, Body, Depends, WebSocket
from fastapi.templating import Jinja2Templates
from typing import Dict, Any, List, Optional
import asyncio
import os
import time
import platform
import bleak
import subprocess
from pydantic import BaseModel, Field

from backend.logging.logging_config import get_api_logger
from backend.modules.ble.ble_manager import BLEManager as BleService
from backend.modules.monitors import monitoring_manager
from backend.ws.manager import manager
from backend.ws.events import create_event
from bleak.exc import BleakError

from backend.modules.ble.ble_persistence import BLEDeviceStorage
from backend.modules.ble.ble_models import BLEDeviceConnection
from backend.modules.ble.ble_recovery import BleErrorRecovery
from backend.modules.ble.ble_metrics import BleMetricsCollector

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

def get_ble_service():
    return BleService(logger=get_api_logger())

def get_ble_metrics():
    """Dependency for BLE metrics collector."""
    return BleMetricsCollector(logger=get_api_logger())

def get_ble_recovery():
    """Dependency for BLE error recovery."""
    return BleErrorRecovery(logger=get_api_logger())

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
        self.recovery = recovery or BleErrorRecovery(logger=get_api_logger())
        self.metrics = metrics or BleMetricsCollector(logger=get_api_logger())
        self.logger = get_api_logger()  # Add this line
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.update_device_address())
            else:
                self.logger.warning("No running event loop, adapter may have limited functionality")
        except RuntimeError:
            self.logger.warning("No running event loop, cannot update device address")

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
    ble_service: BleService = Depends(get_ble_service),
    metrics: BleMetricsCollector = Depends(get_ble_metrics)
):
    """
    Scan for BLE devices in range.
    
    Args:
        scan_time: Duration of scan in seconds
        active: Whether to use active scanning
    """
    try:
        logger.info(f"Starting BLE device scan (mode: {'active' if active else 'passive'})...")
        
        # Record scan start time for metrics
        start_time = time.time()
        
        # Perform the scan
        devices = await ble_service.scan_devices(scan_time=scan_time, active=active)
        
        # Calculate scan duration and record metrics
        duration = time.time() - start_time
        metrics.record_scan(duration, len(devices))
        
        # Log scan results summary
        device_count = len(devices)
        logger.info(f"BLE scan completed. Found {device_count} device(s) in {duration:.2f}s")
        
        # Return the device list - make sure it's serializable
        return devices
    except Exception as e:
        # Log detailed error for debugging
        logger.error(f"Error during BLE scan: {e}", exc_info=True)
        
        # Return a more useful error to the client
        error_details = str(e)
        if "cannot find any bluetooth adapter" in error_details.lower():
            raise HTTPException(status_code=503, detail="Bluetooth adapter not available")
        elif "access denied" in error_details.lower() or "permission" in error_details.lower():
            raise HTTPException(status_code=403, detail="Insufficient permissions to access Bluetooth adapter")
        else:
            raise HTTPException(status_code=500, detail=f"Scan error: {str(e)}")

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

# Update connect_to_device endpoint to handle connection errors better
@router.post("/connect/{address}", response_model=BLEDeviceConnection)
async def connect_to_device(
    address: str,
    connection_params: ConnectionParams = Body(
        ConnectionParams(timeout=10, autoReconnect=True, retryCount=2)
    ),
    ble_service: BleService = Depends(get_ble_service),
    metrics: BleMetricsCollector = Depends(get_ble_metrics),
    recovery: BleErrorRecovery = Depends(get_ble_recovery),
    storage: BLEDeviceStorage = Depends(get_device_storage)
):
    """
    Connect to a BLE device.
    
    Args:
        address: MAC address of the device
        connection_params: Connection parameters
    """
    try:
        logger.info(f"Attempting to connect to device: {address}")
        
        # Record connection attempt for metrics
        metrics.record_connection_attempt(address)
        
        # Check if device is already connected
        if ble_service.client and ble_service.device_address == address and ble_service.client.is_connected:
            logger.info(f"Already connected to {address}")
            
            # Record successful connection for metrics
            metrics.record_connection_success(address)
            
            # Format connection data
            services = await ble_service.get_services()
            
            return BLEDeviceConnection(
                address=address,
                status="already_connected",
                services=services,
                mtu=ble_service.mtu,
                message="Already connected to this device"
            )
        
        # Attempt to connect to the device
        start_time = time.time()
        retry_count = 0
        max_retries = connection_params.retryCount
        
        while retry_count <= max_retries:
            try:
                # Attempt connection
                success = await ble_service.connect_to_device(
                    device_address=address,
                    timeout=connection_params.timeout,
                    auto_reconnect=connection_params.autoReconnect
                )
                
                if success:
                    # Mark device as bonded in storage
                    await storage.add_bonded_device(address)
                    
                    # Get MTU if available
                    try:
                        mtu = await ble_service.get_mtu()
                    except Exception as e:
                        logger.warning(f"Failed to get MTU: {e}")
                        mtu = 23  # Default MTU
                    
                    # Attempt to discover services
                    try:
                        services = await ble_service.get_services()
                    except Exception as e:
                        logger.error(f"Service discovery failed: {e}")
                        services = {}
                    
                    # Record successful connection
                    metrics.record_connection_success(address)
                    connection_time = time.time() - start_time
                    metrics.record_connection_time(address, connection_time)
                    
                    # Return connection response
                    return BLEDeviceConnection(
                        address=address,
                        status="connected",
                        services=services,
                        mtu=mtu,
                        message="Successfully connected"
                    )
                else:
                    # Connection attempt failed without exception
                    logger.warning(f"Connection attempt {retry_count+1}/{max_retries+1} failed without exception")
                    retry_count += 1
                    
                    if retry_count > max_retries:
                        # Record connection failure if all retries exhausted
                        metrics.record_connection_failure(address, "Connection failed without specific error")
                        raise BleakError("Connection failed for unknown reason")
                    else:
                        # Wait before retry
                        await asyncio.sleep(1)
                    
            except Exception as e:
                logger.warning(f"Connection attempt {retry_count+1}/{max_retries+1} failed: {e}")
                retry_count += 1
                
                if retry_count <= max_retries:
                    # Wait before retry
                    await asyncio.sleep(1)  
                else:
                    # Record connection failure
                    metrics.record_connection_failure(address, str(e))
                    
                    # Attempt recovery if recovery flag is set
                    if getattr(connection_params, 'recovery', False):
                        try:
                            logger.info(f"Attempting connection recovery for {address}")
                            result = await recovery.recover_connection(ble_service, address)
                            if result["status"] == "success":
                                logger.info(f"Recovery succeeded for {address}")
                                return BLEDeviceConnection(
                                    address=address,
                                    status="connected_after_recovery",
                                    services={},  # Service discovery happens later
                                    mtu=23,       # Default MTU
                                    message="Connected after recovery"
                                )
                        except Exception as recovery_error:
                            logger.error(f"Error during connection recovery: {recovery_error}")
                    
                    # If we get here, all retries and recovery failed
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Failed to connect to device at {address} after multiple attempts"
                    )
        
        # This should never be reached due to the logic above
        raise HTTPException(status_code=500, detail="Unexpected connection flow - this is a bug")
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except BleakError as e:
        logger.error(f"Bleak connection error: {e}")
        metrics.record_connection_failure(address, f"BleakError: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Connection error: {e}")
        # Record connection failure
        metrics.record_connection_failure(address, str(e))
        raise HTTPException(status_code=500, detail=f"Unexpected error during connection: {str(e)}")

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
    ble_service: BleService = Depends(get_ble_service)
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

@router.get("/adapter-info", response_model=Dict[str, Any])
async def get_adapter_info(
    ble_service: BleService = Depends(get_ble_service)
):
    """Get information about the Bluetooth adapter."""
    try:
        adapter_info = await ble_service.get_adapter_info()
        return adapter_info
    except Exception as e:
        logger.error(f"Error getting adapter info: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/device-exists/{address}", response_model=Dict[str, bool])
async def check_device_exists(
    address: str,
    ble_service: BleService = Depends(get_ble_service)
):
    """Check if a device with the given address exists with a quick scan."""
    try:
        # Do a quick scan to check if the device is visible
        devices = await ble_service.scan_devices(scan_time=2, active=True)
        
        # Check if the given address is in the scan results
        exists = any(device.get("address") == address for device in devices)
        
        return {"exists": exists}
    except Exception as e:
        logger.error(f"Error checking device existence: {e}")
        # Don't raise an exception, just return not found
        return {"exists": False}