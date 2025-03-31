"""
BLE Communication Module.

This package provides communication interfaces for the BLE module:
- WebSocket functionality for real-time BLE operations and notifications
- Client connection management
- Message handling and dispatching

Usage:
    from backend.modules.ble.comms import websocket_endpoint
    from backend.modules.ble.comms import websocket_manager
    
    # In FastAPI app:
    app.add_websocket_route("/ws/ble", websocket_endpoint)
    
    # To broadcast a message from anywhere in your code:
    await websocket_manager.broadcast({"type": "scan_result", "devices": devices})
    
    # Or with a model:
    from backend.modules.ble.models.ble_models import ScanResultMessage
    result = ScanResultMessage(devices=devices, count=len(devices))
    await broadcast_model(result)
"""

from typing import Dict, Any, Union, Optional, List
from fastapi import WebSocket

# Import key components from the websocket module
from .websocket import (
    websocket_endpoint,
    websocket_manager,
    BleWebSocketManager
)

# Export the primary interfaces
__all__ = [
    "websocket_endpoint",
    "websocket_manager",
    "BleWebSocketManager",
    "send_notification",
    "broadcast_message",
    "broadcast_model",
    "find_client",
    "get_active_connections",
]

# Re-export the WebSocket manager once to avoid repeated imports
_ws_manager = websocket_manager

def get_active_connections() -> List[WebSocket]:
    """
    Get all active WebSocket connections.
    
    Returns:
        List of active WebSocket connections
    """
    return list(_ws_manager.active_connections)

def find_client(client_id: str) -> Optional[WebSocket]:
    """
    Find a client connection by ID.
    
    Args:
        client_id: The client identifier
    
    Returns:
        WebSocket connection if found, None otherwise
    """
    for connection in _ws_manager.active_connections:
        conn_id = getattr(connection, "client_id", None)
        if conn_id == client_id:
            return connection
    return None

async def send_notification(
    client_id: str, 
    message_type: str, 
    data: Dict[str, Any]
) -> bool:
    """
    Send a notification to a specific client.
    
    Args:
        client_id: The client identifier
        message_type: The type of message to send
        data: The message data
    
    Returns:
        True if the message was sent, False if client not found
    """
    connection = find_client(client_id)
    if connection:
        await _ws_manager.send_message(connection, {
            "type": message_type,
            "data": data
        })
        return True
    return False

async def broadcast_message(
    message_type: str, 
    data: Dict[str, Any]
) -> bool:
    """
    Broadcast a message to all connected clients.
    
    Args:
        message_type: The type of message to send
        data: The message data
    
    Returns:
        True if the message was broadcast
    """
    await _ws_manager.broadcast({
        "type": message_type,
        "data": data
    })
    return True

async def broadcast_model(model: Any) -> bool:
    """
    Broadcast a Pydantic model to all connected clients.
    
    The model should have a 'type' attribute that will be used as the message type.
    This function handles proper serialization of Pydantic models.
    
    Args:
        model: A Pydantic model to broadcast
    
    Returns:
        True if the message was broadcast
    """
    # Simply pass the model to the broadcast function
    # It will handle model serialization
    await _ws_manager.broadcast(model)
    return True

# Convenience functions for common message types
async def broadcast_scan_results(devices: List[Dict[str, Any]]) -> bool:
    """
    Broadcast scan results to all clients.
    
    Args:
        devices: List of device information dictionaries
    
    Returns:
        True if the message was broadcast
    """
    return await broadcast_message("scan_result", {
        "devices": devices,
        "count": len(devices)
    })

async def broadcast_connection_status(
    status: str, 
    device_address: Optional[str] = None,
    error: Optional[str] = None
) -> bool:
    """
    Broadcast connection status to all clients.
    
    Args:
        status: Connection status (connecting, connected, disconnected, error)
        device_address: Address of the device (if applicable)
        error: Error message (if applicable)
    
    Returns:
        True if the message was broadcast
    """
    message = {
        "status": status
    }
    
    if device_address:
        message["device"] = device_address
    
    if error:
        message["error"] = error
    
    return await broadcast_message("connection_status", message)