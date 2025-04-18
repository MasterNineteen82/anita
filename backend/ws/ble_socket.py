import logging
from typing import Dict, List, Optional
import time
from fastapi import WebSocket, APIRouter, Depends

from backend.ws.manager import manager
from backend.ws.factory import websocket_factory
from backend.ws.events import create_event
from backend.modules.monitoring import monitoring_manager
from backend.services.ble_service import BLEService
from backend.repositories.ble_repository import BLERepository

logger = logging.getLogger(__name__)

# Create BLE dependencies
ble_repository = BLERepository()
ble_service = BLEService()

# Create router
router = APIRouter()

# Create BLE WebSocket endpoint with explicit authentication setting
ble_endpoint = websocket_factory.create_endpoint(
    path="/ws/ble",
    name="ble_socket",
    description="BLE device communication and scanning",
    requires_auth=False,  # Changed from True to False to match uwb_socket
    auto_join_room="ble"
)

# Register handlers
async def start_ble_scan(websocket: WebSocket, payload: dict):
    """Start a BLE device scan."""
    scan_time = payload.get("scan_time", 5)
    active = payload.get("active", True)
    name_prefix = payload.get("name_prefix")
    service_uuids = payload.get("service_uuids")
    
    try:
        result = await ble_service.start_scan(
            scan_time=scan_time,
            active=active,
            name_prefix=name_prefix,
            service_uuids=service_uuids
        )
        await manager.send_personal_message({
            "type": "ble_scan_started",
            "data": {
                "status": "starting",
                "scan_id": result.get("scan_id") if isinstance(result, dict) else str(result),
                "config": {
                    "scan_time": scan_time,
                    "active": active,
                    "name_prefix": name_prefix,
                    "service_uuids": service_uuids
                }
            }
        }, websocket)
    except Exception as e:
        await manager.send_error(websocket, f"Failed to start BLE scan: {str(e)}")

async def get_discovered_devices(websocket: WebSocket, payload: dict):
    """Get list of discovered BLE devices."""
    scan_id = payload.get("scan_id")
    try:
        devices = await ble_service.get_discovered_devices(scan_id)
        await manager.send_personal_message({
            "type": "ble_devices",
            "data": {
                "devices": devices
            }
        }, websocket)
    except Exception as e:
        await manager.send_error(websocket, f"Failed to get discovered devices: {str(e)}")

async def connect_ble_device(websocket: WebSocket, payload: dict):
    """Connect to a specific BLE device."""
    device_id = payload.get("device_id")
    if not device_id:
        await manager.send_error(websocket, "Device ID is required")
        return
    try:
        result = await ble_service.connect_device(device_id)
        await manager.send_personal_message({
            "type": "ble_device_connection",
            "data": {
                "device_id": device_id,
                "status": "connected" if result else "failed"
            }
        }, websocket)
    except Exception as e:
        await manager.send_error(websocket, f"Failed to connect to BLE device: {str(e)}")

async def disconnect_ble_device(websocket: WebSocket, payload: dict):
    """Disconnect from a specific BLE device."""
    device_id = payload.get("device_id")
    if not device_id:
        await manager.send_error(websocket, "Device ID is required")
        return
    try:
        result = await ble_service.disconnect_device(device_id)
        await manager.send_personal_message({
            "type": "ble_device_disconnection",
            "data": {
                "device_id": device_id,
                "status": "disconnected" if result else "failed"
            }
        }, websocket)
    except Exception as e:
        await manager.send_error(websocket, f"Failed to disconnect from BLE device: {str(e)}")

async def get_ble_device_services(websocket: WebSocket, payload: dict):
    """Get services of a connected BLE device."""
    device_id = payload.get("device_id")
    if not device_id:
        await manager.send_error(websocket, "Device ID is required")
        return
    try:
        services = await ble_service.get_device_services(device_id)
        await manager.send_personal_message({
            "type": "ble_device_services",
            "data": {
                "device_id": device_id,
                "services": services
            }
        }, websocket)
    except Exception as e:
        await manager.send_error(websocket, f"Failed to get BLE device services: {str(e)}")

async def read_ble_characteristic(websocket: WebSocket, payload: dict):
    """Read a characteristic value from a BLE device."""
    device_id = payload.get("device_id")
    service_uuid = payload.get("service_uuid")
    characteristic_uuid = payload.get("characteristic_uuid")
    if not all([device_id, service_uuid, characteristic_uuid]):
        await manager.send_error(websocket, "Device ID, Service UUID, and Characteristic UUID are required")
        return
    try:
        value = await ble_service.read_characteristic(device_id, service_uuid, characteristic_uuid)
        await manager.send_personal_message({
            "type": "ble_characteristic_value",
            "data": {
                "device_id": device_id,
                "service_uuid": service_uuid,
                "characteristic_uuid": characteristic_uuid,
                "value": value
            }
        }, websocket)
    except Exception as e:
        await manager.send_error(websocket, f"Failed to read BLE characteristic: {str(e)}")

async def write_ble_characteristic(websocket: WebSocket, payload: dict):
    """Write a value to a BLE device characteristic."""
    device_id = payload.get("device_id")
    service_uuid = payload.get("service_uuid")
    characteristic_uuid = payload.get("characteristic_uuid")
    value = payload.get("value")
    if not all([device_id, service_uuid, characteristic_uuid, value]):
        await manager.send_error(websocket, "Device ID, Service UUID, Characteristic UUID, and Value are required")
        return
    try:
        result = await ble_service.write_characteristic(device_id, service_uuid, characteristic_uuid, value)
        await manager.send_personal_message({
            "type": "ble_characteristic_write_result",
            "data": {
                "device_id": device_id,
                "service_uuid": service_uuid,
                "characteristic_uuid": characteristic_uuid,
                "success": result
            }
        }, websocket)
    except Exception as e:
        await manager.send_error(websocket, f"Failed to write to BLE characteristic: {str(e)}")

async def subscribe_ble_characteristic(websocket: WebSocket, payload: dict):
    """Subscribe to notifications from a BLE characteristic."""
    device_id = payload.get("device_id")
    service_uuid = payload.get("service_uuid")
    characteristic_uuid = payload.get("characteristic_uuid")
    if not all([device_id, service_uuid, characteristic_uuid]):
        await manager.send_error(websocket, "Device ID, Service UUID, and Characteristic UUID are required")
        return
    try:
        result = await ble_service.subscribe_characteristic(device_id, service_uuid, characteristic_uuid)
        await manager.send_personal_message({
            "type": "ble_characteristic_subscription",
            "data": {
                "device_id": device_id,
                "service_uuid": service_uuid,
                "characteristic_uuid": characteristic_uuid,
                "success": result
            }
        }, websocket)
    except Exception as e:
        await manager.send_error(websocket, f"Failed to subscribe to BLE characteristic: {str(e)}")

async def handle_ping(websocket: WebSocket, payload: dict):
    """Handle ping messages and respond with pong."""
    try:
        logger.info("Received ping, sending pong")
        await manager.send_personal_message({
            "type": "pong",
            "data": {
                "timestamp": payload.get("timestamp", 0),
                "server_time": int(time.time() * 1000)
            }
        }, websocket)
    except Exception as e:
        logger.error(f"Error sending pong response: {str(e)}")

async def get_connection_status(websocket: WebSocket, payload: dict):
    """Get the current status of all BLE connections."""
    try:
        connections = await ble_service.get_all_connections()
        await manager.send_personal_message({
            "type": "ble_connections",
            "data": {
                "connections": connections
            }
        }, websocket)
    except Exception as e:
        await manager.send_error(websocket, f"Failed to get BLE connections: {str(e)}")

# Register handlers with the factory
websocket_factory.register_handler("ble_socket", "start_scan", start_ble_scan)
websocket_factory.register_handler("ble_socket", "get_discovered_devices", get_discovered_devices)
websocket_factory.register_handler("ble_socket", "connect_device", connect_ble_device)
websocket_factory.register_handler("ble_socket", "disconnect_device", disconnect_ble_device)
websocket_factory.register_handler("ble_socket", "get_device_services", get_ble_device_services)
websocket_factory.register_handler("ble_socket", "read_characteristic", read_ble_characteristic)
websocket_factory.register_handler("ble_socket", "write_characteristic", write_ble_characteristic)
websocket_factory.register_handler("ble_socket", "subscribe_characteristic", subscribe_ble_characteristic)
websocket_factory.register_handler("ble_socket", "get_connection_status", get_connection_status)
websocket_factory.register_handler("ble_socket", "ping", handle_ping)

# Register global handlers that work on any socket
# Fixed: The register_handler method requires endpoint_name, method_name, and handler
# websocket_factory.register_handler("ping", handle_ping)
