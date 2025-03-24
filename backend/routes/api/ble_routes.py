from fastapi import APIRouter, HTTPException, Body, WebSocket
from typing import Dict, Any, List, Optional
import logging
from backend.modules.ble_manager import BLEManager
from backend.logging.logging_config import get_api_logger
from backend.models import ErrorResponse, SuccessResponse, StatusResponse, BLEDeviceInfo, BLECharacteristic
from backend.modules.monitors import monitoring_manager
from backend.modules.monitoring import BLEDeviceMonitor
from ..utils import handle_errors
from backend.ws.manager import manager  # Should already be updated
from backend.ws.factory import websocket_factory  # Should already be updated
from backend.ws.events import create_event  # Should already be updated

router = APIRouter(
    prefix="/api/ble",
    tags=["bluetooth"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
logger = get_api_logger()
ble_manager = BLEManager()

# Create BLE device monitor and register it with the global monitoring_manager
ble_monitor = BLEDeviceMonitor(ble_manager, interval=5.0)
monitoring_manager.register_monitor(ble_monitor)

# Create WebSocket endpoint for BLE notifications
ble_endpoint = websocket_factory.create_endpoint(
    path="/ws/ble",
    name="ble_socket",
    description="BLE characteristic notifications",
    auto_join_room="ble_notifications"
)

# WebSocket message handlers
async def subscribe_to_characteristic(websocket: WebSocket, payload: dict):
    """Subscribe to notifications for a specific BLE characteristic."""
    char_uuid = payload.get("char_uuid")
    if not char_uuid:
        await manager.send_error(websocket, "Characteristic UUID is required")
        return

    try:
        client_id = manager.get_client_id(websocket)
        success = await ble_manager.start_notify(char_uuid, lambda char_uuid, value: broadcast_notification(char_uuid, value, client_id))
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

async def unsubscribe_from_characteristic(websocket: WebSocket, payload: dict):
    """Unsubscribe from notifications for a specific BLE characteristic."""
    char_uuid = payload.get("char_uuid")
    if not char_uuid:
        await manager.send_error(websocket, "Characteristic UUID is required")
        return

    try:
        success = await ble_manager.stop_notify(char_uuid)
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

async def broadcast_notification(char_uuid: str, value: bytes, client_id: str):
    """Broadcast a characteristic notification to subscribed clients."""
    try:
        event = create_event(
            "ble.characteristic",
            address=ble_manager.device,
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
async def scan_for_devices(scan_time: int = 5):
    try:
        devices = await ble_manager.scan_devices(scan_time)
        logger.info(f"Found {len(devices)} BLE devices")
        return [
            {
                "name": device.name or "Unknown Device",
                "address": device.address,
                "rssi": device.rssi
            } for device in devices
        ]
    except Exception as e:
        logger.error(f"Error scanning BLE devices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")

@router.post("/connect/{address}", response_model=StatusResponse)
async def connect_to_device(address: str):
    try:
        await ble_manager.connect_device(address)
        logger.info(f"Connected to BLE device at address {address}")
        return {"status": "connected", "message": f"Connected to device at {address}"}
    except Exception as e:
        logger.error(f"Error connecting to BLE device: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")

@router.post("/disconnect", response_model=StatusResponse)
async def disconnect_device():
    try:
        await ble_manager.disconnect_device()
        logger.info("Disconnected from BLE device")
        return {"status": "disconnected", "message": "Disconnected from device"}
    except Exception as e:
        logger.error(f"Error disconnecting from BLE device: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Disconnection failed: {str(e)}")

@router.get("/read/{char_uuid}")
async def read_characteristic(char_uuid: str):
    try:
        value = await ble_manager.read_characteristic(char_uuid)
        if value is None:
            raise HTTPException(status_code=404, detail="Characteristic not found or couldn't be read")
        return {"value": value.hex()}
    except Exception as e:
        logger.error(f"Error reading characteristic: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Read failed: {str(e)}")

@router.post("/write/{char_uuid}")
async def write_characteristic(char_uuid: str, data: str = Body(...)):
    try:
        data_bytes = bytes.fromhex(data)
        success = await ble_manager.write_characteristic(char_uuid, data_bytes)
        if not success:
            raise HTTPException(status_code=400, detail="Write failed")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error writing characteristic: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Write failed: {str(e)}")

@router.get("/services", response_model=List[dict])
async def get_services():
    try:
        if not ble_manager.client or not ble_manager.client.is_connected:
            raise HTTPException(status_code=400, detail="No device connected")
        services = await ble_manager.get_services()
        if not services:
            raise HTTPException(status_code=404, detail="No services found")
        logger.info(f"Retrieved {len(services)} services from device")
        return services
    except Exception as e:
        logger.error(f"Error getting services: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get services: {str(e)}")

@router.get("/services/{service_uuid}/characteristics", response_model=List[dict])
async def get_characteristics(service_uuid: str):
    try:
        if not ble_manager.client or not ble_manager.client.is_connected:
            raise HTTPException(status_code=400, detail="No device connected")
        characteristics = await ble_manager.get_characteristics(service_uuid)
        if not characteristics:
            raise HTTPException(status_code=404, detail="No characteristics found")
        logger.info(f"Retrieved {len(characteristics)} characteristics for service {service_uuid}")
        return characteristics
    except Exception as e:
        logger.error(f"Error getting characteristics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get characteristics: {str(e)}")