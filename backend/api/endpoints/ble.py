from fastapi import APIRouter, HTTPException, Body, WebSocket, WebSocketDisconnect, Depends, status
from typing import Dict, Any, List, Optional
import logging
from backend.logging.logging_config import get_api_logger
from backend.models import ErrorResponse, SuccessResponse, StatusResponse, BLEDeviceInfo, BLECharacteristic
from ..utils import handle_errors
from backend.ws.manager import manager
from backend.ws.factory import websocket_factory
from backend.ws.events import create_event
from backend.auth import get_current_user
from bleak import BleakScanner
from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from backend.domain.services.ble_service import BleService
from backend.core.dependencies import get_ble_service
from backend.modules.monitors import monitoring_manager
from backend.modules.monitoring import BLEDeviceMonitor

# Initialize logger
logger = get_api_logger()

# Define router
router = APIRouter(
    prefix="/api/ble",
    tags=["bluetooth"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)

class BleServiceAdapter:
    """Adapter to make BleService compatible with the monitor."""
    
    def __init__(self, ble_service: BleService):
        self.service = ble_service
        self.device = None  # Will be set when connected
        
    async def connect_device(self, address):
        result = await self.service.connect_device(address)
        if result:
            self.device = address
        return result
        
    async def scan_devices(self, timeout):
        return await self.service.scan_devices(timeout)
        
    async def disconnect_device(self):
        if self.device:
            result = await self.service.disconnect_device(self.device)
            if result:
                self.device = None
            return result
        return True

# Dependency for the adapter
def get_ble_adapter(ble_service: BleService = Depends(get_ble_service)):
    """Get a BLE adapter instance for the current request context."""
    return BleServiceAdapter(ble_service)

# Store active device connections - shared state
_active_devices = {}

# Create WebSocket endpoint
ble_endpoint = websocket_factory.create_endpoint(
    path="/ws/ble",
    name="ble_socket",
    description="BLE characteristic notifications",
    auto_join_room="ble_notifications"
)

# WebSocket message handlers
async def subscribe_to_characteristic(websocket: WebSocket, payload: dict, 
                                     ble_service: BleService = Depends(get_ble_service),
                                     ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)):
    """Subscribe to notifications for a specific BLE characteristic."""
    char_uuid = payload.get("char_uuid")
    if not char_uuid:
        await manager.send_error(websocket, "Characteristic UUID is required")
        return

    try:
        client_id = manager.get_client_id(websocket)
        
        # Store adapter's device in shared state for the callback
        if ble_adapter.device:
            _active_devices[client_id] = ble_adapter.device
        
        # Use a callback function that doesn't need dependency injection
        def notification_callback(char_uuid, value):
            # Create an async task to handle the notification
            import asyncio
            asyncio.create_task(broadcast_notification_task(char_uuid, value, client_id))
        
        # For now use the adapter
        success = await ble_adapter.service.start_notify(char_uuid, notification_callback)
        
        if success:
            await manager.send_message(websocket, create_event(
                "ble.characteristic_subscription",
                char_uuid=char_uuid,
                status="subscribed"
            ))
        else:
            await manager.send_error(websocket, f"Failed to subscribe to characteristic {char_uuid}")
    except Exception as e:
        logger.error(f"Error subscribing to characteristic: {str(e)}")
        await manager.send_error(websocket, f"Error subscribing to characteristic: {str(e)}")

async def unsubscribe_from_characteristic(websocket: WebSocket, payload: dict, 
                                         ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)):
    """Unsubscribe from notifications for a specific BLE characteristic."""
    char_uuid = payload.get("char_uuid")
    if not char_uuid:
        await manager.send_error(websocket, "Characteristic UUID is required")
        return

    try:
        # For now use the adapter
        success = await ble_adapter.service.stop_notify(char_uuid)
        
        if success:
            await manager.send_message(websocket, create_event(
                "ble.characteristic_subscription",
                char_uuid=char_uuid,
                status="unsubscribed"
            ))
        else:
            await manager.send_error(websocket, f"Failed to unsubscribe from characteristic {char_uuid}")
    except Exception as e:
        logger.error(f"Error unsubscribing from characteristic: {str(e)}")
        await manager.send_error(websocket, f"Error unsubscribing from characteristic: {str(e)}")

# This function doesn't use dependency injection because it's called from a callback
async def broadcast_notification_task(char_uuid: str, value: bytes, client_id: str):
    """Broadcast a characteristic notification to subscribed clients."""
    try:
        # Get device from shared state
        device_address = _active_devices.get(client_id, "unknown")
        
        event = create_event(
            "ble.characteristic",
            address=device_address,
            service="unknown",  # You can enhance this to include the service UUID
            characteristic=char_uuid,
            value=value.hex(),
            value_hex=value.hex()
        )
        # Broadcast to the "ble_notifications" room, excluding the client that triggered the subscription
        await manager.broadcast_to_room("ble_notifications", event, exclude=None)
    except Exception as e:
        logger.error(f"Error broadcasting notification for {char_uuid}: {str(e)}")

# Register WebSocket handlers
websocket_factory.register_handler("ble_socket", "subscribe_to_characteristic", subscribe_to_characteristic)
websocket_factory.register_handler("ble_socket", "unsubscribe_from_characteristic", unsubscribe_from_characteristic)

# Existing REST endpoints
@router.get("/scan", response_model=List[BLEDeviceInfo])
async def scan_for_devices(scan_time: int = 5, ble_service: BleService = Depends(get_ble_service)):
    try:
        logger.info("📱 Starting BLE device scan...")
        devices = await ble_service.scan_devices(scan_time)
        logger.info(f"🔍 Found {len(devices)} BLE devices")
        return [
            {
                "name": device.name or "Unknown Device",
                "address": device.address,
                # Use advertisement_data.rssi instead of device.rssi (deprecated)
                "rssi": device.advertisement_data.rssi if hasattr(device, 'advertisement_data') else None
            } for device in devices
        ]
    except Exception as e:
        logger.error(f"Failed to scan BLE devices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")

@router.post("/connect/{address}", response_model=StatusResponse)
async def connect_to_device(address: str, 
                          ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)):
    try:
        await ble_adapter.service.connect_device(address)
        # Update the adapter's device address
        ble_adapter.device = address
        logger.info(f"Connected to BLE device at address {address}")
        return {"status": "connected", "message": f"Connected to device at {address}"}
    except Exception as e:
        logger.error(f"Error connecting to BLE device: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")

@router.post("/disconnect", response_model=StatusResponse)
async def disconnect_device(
    ble_service: BleService = Depends(get_ble_service),
    ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)
):
    try:
        device_address = ble_adapter.device  # Store address for the message
        if device_address:
            await ble_service.disconnect_device(device_address)
            # Update adapter state
            ble_adapter.device = None
            logger.info(f"Disconnected from BLE device {device_address}")
            return {"status": "disconnected", "message": f"Disconnected from device {device_address}"}
        else:
            return {"status": "disconnected", "message": "No device was connected"}
    except Exception as e:
        logger.error(f"Error disconnecting from BLE device: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Disconnection failed: {str(e)}")

@router.get("/read/{char_uuid}")
async def read_characteristic(
    char_uuid: str, 
    ble_service: BleService = Depends(get_ble_service),
    ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)
):
    try:
        # TODO: Add read_characteristic to BleService
        # For now we use the adapter for compatibility
        value = await ble_adapter.service.read_characteristic(char_uuid)
        if value is None:
            raise HTTPException(status_code=404, detail="Characteristic not found or couldn't be read")
        return {"value": value.hex()}
    except Exception as e:
        logger.error(f"Error reading characteristic: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Read failed: {str(e)}")

@router.post("/write/{char_uuid}")
async def write_characteristic(
    char_uuid: str, 
    data: str = Body(...), 
    ble_service: BleService = Depends(get_ble_service),
    ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)
):
    try:
        data_bytes = bytes.fromhex(data)
        # TODO: Add write_characteristic to BleService
        # For now we use the adapter for compatibility
        success = await ble_adapter.service.write_characteristic(char_uuid, data_bytes)
        if not success:
            raise HTTPException(status_code=400, detail="Write failed")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error writing characteristic: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Write failed: {str(e)}")

@router.get("/services", response_model=List[dict])
async def get_services(
    ble_service: BleService = Depends(get_ble_service),
    ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)
):
    try:
        # TODO: Add get_services to BleService
        # For now we use the adapter for compatibility
        if not ble_adapter.device:
            raise HTTPException(status_code=400, detail="No device connected")
        services = await ble_adapter.service.get_services()
        if not services:
            raise HTTPException(status_code=404, detail="No services found")
        logger.info(f"Retrieved {len(services)} services from device")
        return services
    except Exception as e:
        logger.error(f"Error getting services: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get services: {str(e)}")

@router.get("/services/{service_uuid}/characteristics", response_model=List[dict])
async def get_characteristics(
    service_uuid: str, 
    ble_service: BleService = Depends(get_ble_service),
    ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)
):
    try:
        # TODO: Add get_characteristics to BleService
        # For now we use the adapter for compatibility
        if not ble_adapter.device:
            raise HTTPException(status_code=400, detail="No device connected")
        characteristics = await ble_adapter.service.get_characteristics(service_uuid)
        if not characteristics:
            raise HTTPException(status_code=404, detail="No characteristics found")
        logger.info(f"Retrieved {len(characteristics)} characteristics for service {service_uuid}")
        return characteristics
    except Exception as e:
        logger.error(f"Error getting characteristics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get characteristics: {str(e)}")

# Fix the monitor initialization
@router.on_event("startup")
async def startup_event():
    """Initialize BLE monitor on startup."""
    try:
        # Check if monitor is already registered first
        if not monitoring_manager.is_registered("ble_device_monitor"):
            ble_service = get_ble_service()
            ble_adapter = BleServiceAdapter(ble_service)
            ble_monitor = BLEDeviceMonitor(ble_adapter, interval=5.0)
            monitoring_manager.register_monitor(ble_monitor)
            logger.info("BLE monitor initialized")
        else:
            logger.info("BLE monitor already initialized")
    except Exception as e:
        logger.error(f"Error initializing BLE monitor: {str(e)}")