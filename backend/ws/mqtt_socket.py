import logging
from typing import Dict, List, Optional
import time

from fastapi import WebSocket, APIRouter

from backend.ws.manager import manager
from backend.ws.factory import websocket_factory

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Create MQTT WebSocket endpoint
mqtt_endpoint = websocket_factory.create_endpoint(
    path="/ws/mqtt",
    name="mqtt_socket",
    description="MQTT communication and topic subscription",
    requires_auth=False,  # Changed from True to False to match uwb_socket
    auto_join_room="mqtt"
)

# Register handlers
async def get_active_topics(websocket: WebSocket, payload: dict):
    """Get list of active MQTT topics."""
    try:
        # Mock data for now
        topics = [
            {"id": "sensors/temperature", "subscribers": 2, "messages_per_min": 10},
            {"id": "sensors/humidity", "subscribers": 1, "messages_per_min": 5},
            {"id": "alerts/critical", "subscribers": 3, "messages_per_min": 1}
        ]
        
        await manager.send_personal_message({
            "type": "mqtt_topics",
            "data": {
                "topics": topics
            }
        }, websocket)
    except Exception as e:
        await manager.send_error(websocket, f"Failed to get active topics: {str(e)}")

async def subscribe_topic(websocket: WebSocket, payload: dict):
    """Subscribe to an MQTT topic."""
    topic = payload.get("topic")
    if not topic:
        await manager.send_error(websocket, "Topic is required")
        return
        
    try:
        await manager.send_personal_message({
            "type": "mqtt_subscription",
            "data": {
                "topic": topic,
                "status": "subscribed"
            }
        }, websocket)
    except Exception as e:
        await manager.send_error(websocket, f"Failed to subscribe to topic: {str(e)}")

async def publish_message(websocket: WebSocket, payload: dict):
    """Publish a message to an MQTT topic."""
    topic = payload.get("topic")
    message = payload.get("message")
    
    if not topic or message is None:
        await manager.send_error(websocket, "Topic and message are required")
        return
        
    try:
        await manager.send_personal_message({
            "type": "mqtt_publish",
            "data": {
                "topic": topic,
                "status": "published"
            }
        }, websocket)
    except Exception as e:
        await manager.send_error(websocket, f"Failed to publish message: {str(e)}")

async def handle_ping(websocket: WebSocket, payload: dict):
    """Handle ping messages and respond with pong."""
    try:
        logger.info("Received ping from MQTT WebSocket, sending pong")
        await manager.send_personal_message({
            "type": "pong",
            "data": {
                "timestamp": payload.get("timestamp", 0),
                "server_time": int(time.time() * 1000)
            }
        }, websocket)
    except Exception as e:
        logger.error(f"Error sending pong response: {str(e)}")

# Register message handlers
websocket_factory.register_handler("mqtt_socket", "get_active_topics", get_active_topics)
websocket_factory.register_handler("mqtt_socket", "subscribe_topic", subscribe_topic)
websocket_factory.register_handler("mqtt_socket", "publish_message", publish_message)
websocket_factory.register_handler("mqtt_socket", "ping", handle_ping)
