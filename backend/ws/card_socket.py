import logging
from typing import Dict, List, Optional

from fastapi import WebSocket, APIRouter

from backend.ws.manager import manager
from backend.ws.factory import websocket_factory

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Create Card WebSocket endpoint
card_endpoint = websocket_factory.create_endpoint(
    path="/ws/card",
    name="card_socket",
    description="Card device communication and notifications",
    requires_auth=False,  # Changed from True to False to match uwb_socket
    auto_join_room="card"
)

# Register handlers
async def get_active_readers(websocket: WebSocket, payload: dict):
    """Get list of active card readers."""
    try:
        # Mock data for now
        readers = [
            {"id": "card-001", "type": "smartcard", "status": "active"},
            {"id": "card-002", "type": "nfc", "status": "active"},
            {"id": "card-003", "type": "mifare", "status": "idle"}
        ]
        
        await manager.send_personal_message({
            "type": "card_readers",
            "data": {
                "readers": readers
            }
        }, websocket)
    except Exception as e:
        await manager.send_error(websocket, f"Failed to get active readers: {str(e)}")

async def listen_for_cards(websocket: WebSocket, payload: dict):
    """Start listening for card events."""
    try:
        await manager.send_personal_message({
            "type": "card_listening",
            "data": {
                "status": "started"
            }
        }, websocket)
    except Exception as e:
        await manager.send_error(websocket, f"Failed to start card listening: {str(e)}")

async def handle_ping(websocket: WebSocket, payload: dict):
    """Handle ping messages and respond with pong."""
    try:
        logger.info("Received ping from card WebSocket, sending pong")
        await manager.send_personal_message({
            "type": "pong",
            "data": {
                "timestamp": payload.get("timestamp", 0)
            }
        }, websocket)
    except Exception as e:
        logger.error(f"Error sending pong response: {str(e)}")

# Register message handlers
websocket_factory.register_handler("card_socket", "get_active_readers", get_active_readers)
websocket_factory.register_handler("card_socket", "listen_for_cards", listen_for_cards)
websocket_factory.register_handler("card_socket", "ping", handle_ping)
