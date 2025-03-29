"""Bluetooth API routes."""

import logging
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException

# Create router
router = APIRouter()

# Import the consolidated router
from backend.modules.ble.bleroutes import ble_router

# Include all routes from the consolidated router
router.include_router(ble_router)

# Get logger
logger = logging.getLogger(__name__)

# Import dependencies for WebSocket handling
from backend.ws.manager import manager
from backend.ws.events import create_event
from backend.dependencies import get_ble_service, get_ble_metrics
from backend.modules.ble.ble_metrics import BleMetricsCollector, SystemMonitor

# Maintain WebSocket functionality in the main file
@router.websocket("/ws/ble")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for BLE notifications and real-time updates."""
    await manager.connect(websocket)
    client_id = manager.get_client_id(websocket)
    logger.info(f"BLE WebSocket client {client_id} connected")
    
    try:
        # Initialize services
        ble_service = get_ble_service()
        metrics = get_ble_metrics()
        
        # Send initial connection event
        await manager.send_message(
            websocket,
            create_event("ble.connection", status="connected", client_id=client_id)
        )
        
        # Handle incoming messages
        while True:
            # Wait for messages from the client
            message = await websocket.receive_json()
            
            if not message or not isinstance(message, dict):
                continue
                
            # Get message type
            message_type = message.get("type", "")
            
            # Handle different message types
            if message_type == "subscribe":
                await handle_subscription(websocket, message, ble_service)
                
            elif message_type == "unsubscribe":
                await handle_unsubscription(websocket, message, ble_service)
                
            elif message_type == "scan":
                await handle_scan_request(websocket, message, ble_service, metrics)
                
            elif message_type == "connect":
                await handle_connect_request(websocket, message, ble_service, metrics)
                
            elif message_type == "disconnect":
                await handle_disconnect_request(websocket, ble_service)
                
            elif message_type == "read":
                await handle_read_request(websocket, message, ble_service)
                
            elif message_type == "write":
                await handle_write_request(websocket, message, ble_service)
                
            elif message_type == "ping":
                # Simple ping to keep connection alive
                await manager.send_message(
                    websocket,
                    create_event("ble.pong", timestamp=asyncio.get_event_loop().time())
                )
            
            else:
                await manager.send_error(
                    websocket, 
                    f"Unknown message type: {message_type}",
                    code="unknown_type"
                )
    
    except WebSocketDisconnect:
        logger.info(f"BLE WebSocket client {client_id} disconnected")
        manager.disconnect(websocket)
        
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await manager.send_error(
                websocket,
                f"Internal error: {str(e)}",
                code="internal_error"
            )
        except:
            pass
        manager.disconnect(websocket)

# WebSocket message handlers
async def handle_subscription(websocket: WebSocket, message: dict, ble_service):
    """Handle subscription requests."""
    char_uuid = message.get("characteristic")
    if not char_uuid:
        await manager.send_error(websocket, "Characteristic UUID required", code="missing_parameter")
        return
    
    if not ble_service.is_connected():
        await manager.send_error(websocket, "No device connected", code="not_connected")
        return
    
    # Create notification handler
    client_id = manager.get_client_id(websocket)
    
    async def notification_handler(sender, data):
        """Handle BLE notifications."""
        try:
            # Format data based on type
            formatted_data = None
            if isinstance(data, bytes):
                formatted_data = {
                    "hex": data.hex(),
                    "bytes": [b for b in data],
                    "text": data.decode('utf-8', errors='replace')
                }
            else:
                formatted_data = str(data)
            
            # Send notification event
            await manager.send_message(
                websocket,
                create_event(
                    "ble.notification",
                    characteristic=str(sender),
                    data=formatted_data,
                    timestamp=asyncio.get_event_loop().time()
                )
            )
        except Exception as e:
            logger.error(f"Error in notification handler: {e}", exc_info=True)
    
    # Start notifications
    try:
        success = await ble_service.start_notify(char_uuid, notification_handler)
        
        if success:
            await manager.send_message(
                websocket,
                create_event(
                    "ble.subscription",
                    status="subscribed",
                    characteristic=char_uuid
                )
            )
        else:
            await manager.send_error(
                websocket,
                f"Failed to subscribe to {char_uuid}",
                code="subscription_failed"
            )
    except Exception as e:
        logger.error(f"Error starting notifications: {e}", exc_info=True)
        await manager.send_error(
            websocket,
            f"Error: {str(e)}",
            code="notification_error"
        )

async def handle_unsubscription(websocket: WebSocket, message: dict, ble_service):
    """Handle unsubscription requests."""
    char_uuid = message.get("characteristic")
    if not char_uuid:
        await manager.send_error(websocket, "Characteristic UUID required", code="missing_parameter")
        return
    
    if not ble_service.is_connected():
        await manager.send_error(websocket, "No device connected", code="not_connected")
        return
    
    try:
        success = await ble_service.stop_notify(char_uuid)
        
        if success:
            await manager.send_message(
                websocket,
                create_event(
                    "ble.subscription",
                    status="unsubscribed",
                    characteristic=char_uuid
                )
            )
        else:
            await manager.send_error(
                websocket,
                f"Failed to unsubscribe from {char_uuid}",
                code="unsubscription_failed"
            )
    except Exception as e:
        logger.error(f"Error stopping notifications: {e}", exc_info=True)
        await manager.send_error(
            websocket,
            f"Error: {str(e)}",
            code="notification_error"
        )

async def handle_scan_request(websocket: WebSocket, message: dict, ble_service, metrics):
    """Handle scan requests."""
    scan_time = message.get("scanTime", 5.0)
    active = message.get("active", True)
    service_uuids = message.get("services")
    
    try:
        # Record scan start if metrics available
        scan_id = None
        if hasattr(metrics, "record_scan_start"):
            scan_id = metrics.record_scan_start()
        
        # Send scan starting event
        await manager.send_message(
            websocket,
            create_event("ble.scan", status="started", scanTime=scan_time)
        )
        
        # Perform scan
        devices = await ble_service.scan_devices(
            scan_time=scan_time,
            active=active,
            service_uuids=service_uuids
        )
        
        # Record scan completion if metrics available
        if scan_id and hasattr(metrics, "record_scan_complete"):
            metrics.record_scan_complete(
                scan_id,
                success=True,
                device_count=len(devices)
            )
        
        # Send results
        await manager.send_message(
            websocket,
            create_event(
                "ble.scan",
                status="completed",
                devices=devices,
                count=len(devices)
            )
        )
    except Exception as e:
        logger.error(f"Error handling scan request: {e}", exc_info=True)
        
        # Record scan failure if metrics available
        if scan_id and hasattr(metrics, "record_scan_complete"):
            metrics.record_scan_complete(scan_id, success=False, error=str(e))
        
        await manager.send_error(
            websocket,
            f"Scan error: {str(e)}",
            code="scan_error"
        )

async def handle_connect_request(websocket: WebSocket, message: dict, ble_service, metrics):
    """Handle connection requests."""
    address = message.get("address")
    if not address:
        await manager.send_error(websocket, "Device address required", code="missing_parameter")
        return
    
    timeout = message.get("timeout", 10.0)
    auto_reconnect = message.get("autoReconnect", True)
    
    try:
        # Record connection start if metrics available
        op_id = None
        if hasattr(metrics, "record_connect_start"):
            op_id = metrics.record_connect_start(address)
        
        # Send connecting event
        await manager.send_message(
            websocket,
            create_event("ble.connection", status="connecting", device=address)
        )
        
        # Connect to device
        connected = await ble_service.connect_device(
            address,
            timeout=timeout,
            auto_reconnect=auto_reconnect
        )
        
        # Record connection completion if metrics available
        if op_id and hasattr(metrics, "record_connect_complete"):
            metrics.record_connect_complete(op_id, address, success=connected)
        
        if connected:
            # Get device info
            device_info = await ble_service.get_device_info()
            
            # Send connected event
            await manager.send_message(
                websocket,
                create_event(
                    "ble.connection",
                    status="connected",
                    device=address,
                    info=device_info
                )
            )
        else:
            await manager.send_error(
                websocket,
                f"Failed to connect to {address}",
                code="connection_failed"
            )
    except Exception as e:
        logger.error(f"Error handling connect request: {e}", exc_info=True)
        
        # Record connection failure if metrics available
        if op_id and hasattr(metrics, "record_connect_complete"):
            metrics.record_connect_complete(op_id, address, success=False, error=str(e))
        
        await manager.send_error(
            websocket,
            f"Connection error: {str(e)}",
            code="connection_error"
        )

async def handle_disconnect_request(websocket: WebSocket, ble_service):
    """Handle disconnection requests."""
    if not ble_service.is_connected():
        await manager.send_message(
            websocket,
            create_event("ble.connection", status="not_connected")
        )
        return
    
    device_address = ble_service.get_connected_device_address()
    
    try:
        # Disconnect
        await ble_service.disconnect_device()
        
        # Send disconnected event
        await manager.send_message(
            websocket,
            create_event(
                "ble.connection",
                status="disconnected",
                device=device_address
            )
        )
    except Exception as e:
        logger.error(f"Error handling disconnect request: {e}", exc_info=True)
        await manager.send_error(
            websocket,
            f"Disconnect error: {str(e)}",
            code="disconnect_error"
        )

async def handle_read_request(websocket: WebSocket, message: dict, ble_service):
    """Handle read requests."""
    char_uuid = message.get("characteristic")
    if not char_uuid:
        await manager.send_error(websocket, "Characteristic UUID required", code="missing_parameter")
        return
    
    if not ble_service.is_connected():
        await manager.send_error(websocket, "No device connected", code="not_connected")
        return
    
    try:
        # Read value
        value = await ble_service.read_characteristic(char_uuid)
        
        # Format response based on value type
        formatted_value = None
        if isinstance(value, bytes):
            formatted_value = {
                "hex": value.hex(),
                "bytes": [b for b in value],
                "text": value.decode('utf-8', errors='replace')
            }
        else:
            formatted_value = str(value)
        
        # Send read result
        await manager.send_message(
            websocket,
            create_event(
                "ble.read",
                characteristic=char_uuid,
                value=formatted_value,
                timestamp=asyncio.get_event_loop().time()
            )
        )
    except Exception as e:
        logger.error(f"Error handling read request: {e}", exc_info=True)
        await manager.send_error(
            websocket,
            f"Read error: {str(e)}",
            code="read_error"
        )

async def handle_write_request(websocket: WebSocket, message: dict, ble_service):
    """Handle write requests."""
    char_uuid = message.get("characteristic")
    if not char_uuid:
        await manager.send_error(websocket, "Characteristic UUID required", code="missing_parameter")
        return
    
    value = message.get("value")
    if value is None:
        await manager.send_error(websocket, "Value required", code="missing_parameter")
        return
    
    value_type = message.get("valueType", "auto")
    response = message.get("response", True)
    
    if not ble_service.is_connected():
        await manager.send_error(websocket, "No device connected", code="not_connected")
        return
    
    try:
        # Convert value based on type
        converted_value = value
        
        if value_type == "hex" or (value_type == "auto" and isinstance(value, str) and all(c in "0123456789ABCDEFabcdef" for c in value) and len(value) % 2 == 0):
            converted_value = bytes.fromhex(value)
        elif value_type == "bytes" and isinstance(value, list):
            converted_value = bytes(value)
        elif value_type == "text" and isinstance(value, str):
            converted_value = value.encode('utf-8')
        
        # Write value
        success = await ble_service.write_characteristic(char_uuid, converted_value, response)
        
        # Send write result
        await manager.send_message(
            websocket,
            create_event(
                "ble.write",
                characteristic=char_uuid,
                success=success,
                timestamp=asyncio.get_event_loop().time()
            )
        )
    except Exception as e:
        logger.error(f"Error handling write request: {e}", exc_info=True)
        await manager.send_error(
            websocket,
            f"Write error: {str(e)}",
            code="write_error"
        )

# Add routes for metrics and system info
@router.get("/health")
async def get_bluetooth_health():
    """Get comprehensive Bluetooth health report"""
    try:
        # Get the system monitor
        ble_metrics = get_ble_metrics()
        system_monitor = None
        
        # Check if ble_metrics has system_monitor attribute or create one
        if hasattr(ble_metrics, "system_monitor"):
            system_monitor = ble_metrics.system_monitor
        else:
            from backend.modules.ble.ble_metrics import SystemMonitor
            system_monitor = SystemMonitor()
        
        # Generate health report
        if hasattr(system_monitor, "get_bluetooth_health_report"):
            report = system_monitor.get_bluetooth_health_report()
            return report
        else:
            # Fallback to basic system info
            return {
                "status": "limited",
                "message": "Advanced health reporting not available",
                "system": system_monitor.get_system_info() if hasattr(system_monitor, "get_system_info") else {}
            }
    except Exception as e:
        logger.error(f"Error generating Bluetooth health report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate health report: {str(e)}")

"""Main BLE routes module."""

from .bleroutes import adapter_router, device_router, service_router
from .websocket import websocket_endpoint

ble_router = adapter_router
ble_router.include_router(device_router)
ble_router.include_router(service_router)

# Export the WebSocket endpoint
__all__ = ['ble_router', 'websocket_endpoint']