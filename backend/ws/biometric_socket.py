import logging
from typing import Dict, List, Optional

from fastapi import WebSocket, APIRouter

from backend.ws.manager import manager
from backend.ws.factory import websocket_factory

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Create Biometric WebSocket endpoint
biometric_endpoint = websocket_factory.create_endpoint(
    path="/ws/biometric",
    name="biometric_socket",
    description="Biometric device communication and notifications",
    requires_auth=False,  # Changed from True to False to match uwb_socket
    auto_join_room="biometric"
)

# Register handlers
async def get_active_devices(websocket: WebSocket, payload: dict):
    """Get list of active biometric devices."""
    try:
        # Mock data for now
        devices = [
            {"id": "bio-001", "type": "fingerprint", "status": "active"},
            {"id": "bio-002", "type": "facial", "status": "active"},
            {"id": "bio-003", "type": "iris", "status": "idle"}
        ]
        
        await manager.send_personal_message({
            "type": "biometric_devices",
            "data": {
                "devices": devices
            }
        }, websocket)
    except Exception as e:
        await manager.send_error(websocket, f"Failed to get active devices: {str(e)}")

async def handle_ping(websocket: WebSocket, payload: dict):
    """Handle ping messages and respond with pong."""
    try:
        logger.info("Received ping from biometric WebSocket, sending pong")
        await manager.send_personal_message({
            "type": "pong",
            "data": {
                "timestamp": payload.get("timestamp", 0)
            }
        }, websocket)
    except Exception as e:
        logger.error(f"Error sending pong response: {str(e)}")

# Register message handlers
websocket_factory.register_handler("biometric_socket", "get_active_devices", get_active_devices)
websocket_factory.register_handler("biometric_socket", "ping", handle_ping)
