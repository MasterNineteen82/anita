from fastapi import APIRouter, HTTPException, Body, WebSocket, WebSocketDisconnect, Depends, status
from typing import Dict, Any, List, Optional
import logging
from backend.logging.logging_config import get_api_logger
from backend.models import ErrorResponse, SuccessResponse, StatusResponse, BLEDeviceInfo, BLECharacteristic
from backend.modules.monitors import monitoring_manager
from backend.modules.monitoring import BLEDeviceMonitor
from ..utils import handle_errors
from backend.ws.manager import manager
from backend.ws.factory import websocket_factory
from backend.ws.events import create_event
from backend.auth import get_current_user
from bleak import BleakScanner
from backend.domain.services.ble_service import BleService
from backend.core.dependencies import get_ble_service
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class BLEDeviceInfo(BaseModel):
    name: Optional[str]
    address: str
    rssi: Optional[int]

# Define BleServiceAdapter
class BleServiceAdapter:
    def __init__(self, service: BleService):
        self.service = service
        self.device = None  # or some default value

# Define dependency function to inject BleServiceAdapter
def get_ble_adapter(ble_service: BleService = Depends(get_ble_service)):
    return BleServiceAdapter(ble_service)

router = APIRouter(
    prefix="/api/ble",
    tags=["bluetooth"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
logger = get_api_logger()

# Create WebSocket endpoint for BLE notifications
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
        
        # Check if the device is connected before subscribing
        if not ble_adapter.device:
            await manager.send_error(websocket, "No device connected")
            return
        
        success = await ble_adapter.service.start_notify(char_uuid, lambda char_uuid, value: broadcast_notification(char_uuid, value, client_id, ble_adapter))
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
                                         ble_service: BleService = Depends(get_ble_service),
                                         ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)):
    """Unsubscribe from notifications for a specific BLE characteristic."""
    char_uuid = payload.get("char_uuid")
    if not char_uuid:
        await manager.send_error(websocket, "Characteristic UUID is required")
        return

    try:
        # Check if the device is connected before unsubscribing
        if not ble_adapter.device:
            await manager.send_error(websocket, "No device connected")
            return
        
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

async def broadcast_notification(char_uuid: str, value: bytes, client_id: str, ble_adapter: BleServiceAdapter):
    """Broadcast a characteristic notification to subscribed clients."""
    try:
        # Check if the device is connected before broadcasting
        if not ble_adapter.device:
            logger.warning("No device connected, cannot broadcast notification")
            return
        
        event = create_event(
            "ble.characteristic",
            address=ble_adapter.device,
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
        
        # Ensure devices is a list of dictionaries
        device_list = []
        for device in devices:
            device_info = {
                "name": device.name if hasattr(device, 'name') else "Unknown Device",
                "address": device.address,
                "rssi": device.advertisement_data.rssi if hasattr(device, 'advertisement_data') and hasattr(device.advertisement_data, 'rssi') else None
            }
            device_list.append(device_info)
        
        return device_list
    except Exception as e:
        logger.error(f"Failed to scan BLE devices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")

@router.post("/connect/{address}", response_model=StatusResponse)
async def connect_to_device(address: str, 
                          ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)):
    try:
        # Validate the address format
        if not address:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid device address")
        
        # Call the service and get the actual connection result
        connection_success = await ble_adapter.service.connect_device(address)
        
        # Only update device state if connection actually succeeded
        if connection_success:
            ble_adapter.device = address
            logger.info(f"Connected to BLE device at address {address}")
            return {"status": "connected", "message": f"Connected to device at {address}"}
        else:
            # Return appropriate error if connection failed
            logger.error(f"Failed to connect to device at {address}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to connect to device at {address}")
    except Exception as e:
        logger.error(f"Error connecting to BLE device: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Connection failed: {str(e)}")

@router.post("/disconnect", response_model=StatusResponse)
async def disconnect_device(ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)):
    try:
        # Check if a device is actually connected
        if not ble_adapter.device:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No device connected")
        
        await ble_adapter.service.disconnect_device()
        ble_adapter.device = None  # Clear the device after disconnection
        logger.info("Disconnected from BLE device")
        return {"status": "disconnected", "message": "Disconnected from device"}
    except HTTPException as http_exc:
        raise http_exc  # Re-raise HTTPExceptions
    except Exception as e:
        logger.error(f"Error disconnecting from BLE device: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Disconnection failed: {str(e)}")

@router.get("/read/{char_uuid}")
async def read_characteristic(char_uuid: str, ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)):
    try:
        # Validate UUID format
        if not char_uuid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid characteristic UUID")
        
        value = await ble_adapter.service.read_characteristic(char_uuid)
        if value is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Characteristic not found or couldn't be read")
        return {"value": value.hex()}
    except HTTPException as http_exc:
        raise http_exc  # Re-raise HTTPExceptions
    except Exception as e:
        logger.error(f"Error reading characteristic: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Read failed: {str(e)}")

@router.post("/write/{char_uuid}")
async def write_characteristic(char_uuid: str, data: str = Body(...), ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)):
    try:
        # Validate UUID format
        if not char_uuid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid characteristic UUID")
        
        data_bytes = bytes.fromhex(data)
        success = await ble_adapter.service.write_characteristic(char_uuid, data_bytes)
        if not success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Write failed")
        return {"status": "success"}
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid data format")
    except HTTPException as http_exc:
        raise http_exc  # Re-raise HTTPExceptions
    except Exception as e:
        logger.error(f"Error writing characteristic: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Write failed: {str(e)}")

@router.get("/services", response_model=List[dict])
async def get_services(ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)):
    try:
        if not ble_adapter.device:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No device connected")
        services = await ble_adapter.service.get_services()
        if not services:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No services found")
        logger.info(f"Retrieved {len(services)} services from device")
        return services
    except HTTPException as http_exc:
        raise http_exc  # Re-raise HTTPExceptions
    except Exception as e:
        logger.error(f"Error getting services: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get services: {str(e)}")

@router.get("/services/{service_uuid}/characteristics", response_model=List[dict])
async def get_characteristics(service_uuid: str, ble_adapter: BleServiceAdapter = Depends(get_ble_adapter)):
    try:
        if not ble_adapter.device:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No device connected")
        characteristics = await ble_adapter.service.get_characteristics(service_uuid)
        if not characteristics:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No characteristics found")
        logger.info(f"Retrieved {len(characteristics)} characteristics for service {service_uuid}")
        return characteristics
    except HTTPException as http_exc:
        raise http_exc  # Re-raise HTTPExceptions
    except Exception as e:
        logger.error(f"Error getting characteristics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get characteristics: {str(e)}")