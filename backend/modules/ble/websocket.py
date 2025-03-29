"""WebSocket handler for BLE notifications."""

import asyncio
import json
import logging
import uuid
from typing import Dict, Set, Optional, List
from fastapi import WebSocket, WebSocketDisconnect

from backend.modules.ble.events import ble_event_bus

logger = logging.getLogger(__name__)

class BleNotificationManager:
    """Manages BLE notification WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # client_id -> set of characteristic UUIDs
        
        # Subscribe to BLE events
        ble_event_bus.on('notification', self.handle_ble_notification)
        ble_event_bus.on('connection', self.handle_ble_connection)
        ble_event_bus.on('disconnection', self.handle_ble_disconnection)
        ble_event_bus.on('error', self.handle_ble_error)
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """
        Connect a new client.
        
        Args:
            websocket: The WebSocket connection
            client_id: Unique identifier for the client
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.subscriptions[client_id] = set()
        
        logger.info(f"Client {client_id} connected via WebSocket")
    
    def disconnect(self, client_id: str):
        """
        Disconnect a client.
        
        Args:
            client_id: Unique identifier for the client
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            
        if client_id in self.subscriptions:
            del self.subscriptions[client_id]
            
        logger.info(f"Client {client_id} disconnected")
    
    def subscribe(self, client_id: str, characteristic_uuid: str):
        """
        Subscribe a client to characteristic notifications.
        
        Args:
            client_id: Unique identifier for the client
            characteristic_uuid: UUID of the characteristic to subscribe to
        """
        if client_id not in self.subscriptions:
            self.subscriptions[client_id] = set()
        
        self.subscriptions[client_id].add(characteristic_uuid.lower())
        logger.info(f"Client {client_id} subscribed to {characteristic_uuid}")
    
    def unsubscribe(self, client_id: str, characteristic_uuid: str):
        """
        Unsubscribe a client from characteristic notifications.
        
        Args:
            client_id: Unique identifier for the client
            characteristic_uuid: UUID of the characteristic to unsubscribe from
        """
        if client_id in self.subscriptions:
            self.subscriptions[client_id].discard(characteristic_uuid.lower())
            logger.info(f"Client {client_id} unsubscribed from {characteristic_uuid}")
    
    async def handle_ble_notification(self, data):
        """
        Handle BLE notifications from the event bus.
        
        Args:
            data: Notification data
        """
        try:
            characteristic_uuid = data['characteristic']
            value = data['value']
            device_address = data.get('device')
            
            await self.broadcast_notification(characteristic_uuid, value, device_address)
        except Exception as e:
            logger.error(f"Error handling notification event: {e}", exc_info=True)
            
    async def handle_ble_connection(self, data):
        """
        Handle BLE connection events from the event bus.
        
        Args:
            data: Connection data
        """
        try:
            device_address = data['device']
            await self.send_connection_event(device_address, True)
        except Exception as e:
            logger.error(f"Error handling connection event: {e}", exc_info=True)
            
    async def handle_ble_disconnection(self, data):
        """
        Handle BLE disconnection events from the event bus.
        
        Args:
            data: Disconnection data
        """
        try:
            device_address = data['device']
            await self.send_connection_event(device_address, False)
        except Exception as e:
            logger.error(f"Error handling disconnection event: {e}", exc_info=True)
            
    async def handle_ble_error(self, data):
        """
        Handle BLE error events from the event bus.
        
        Args:
            data: Error data
        """
        try:
            error_message = data['message']
            context = data.get('context')
            await self.broadcast_error(error_message, context)
        except Exception as e:
            logger.error(f"Error handling error event: {e}", exc_info=True)
            
    async def broadcast_notification(self, characteristic_uuid: str, value, device_address: Optional[str] = None):
        """
        Broadcast a notification to all subscribed clients.
        
        Args:
            characteristic_uuid: UUID of the characteristic that was notified
            value: The notification value
            device_address: Optional device address
        """
        char_uuid = characteristic_uuid.lower()
        
        # Convert value to base64 if it's binary
        if isinstance(value, (bytes, bytearray)):
            import base64
            value_to_send = base64.b64encode(value).decode('ascii')
            encoding = 'base64'
        else:
            value_to_send = value
            encoding = 'text'
        
        # Prepare the message
        message = {
            "type": "ble.notification",
            "characteristic": char_uuid,
            "value": value_to_send,
            "encoding": encoding
        }
        
        if device_address:
            message["device"] = device_address
        
        # Send to all subscribed clients
        disconnected_clients = []
        
        for client_id, subscriptions in self.subscriptions.items():
            if char_uuid in subscriptions and client_id in self.active_connections:
                try:
                    await self.active_connections[client_id].send_json(message)
                except Exception as e:
                    logger.error(f"Error sending notification to client {client_id}: {e}")
                    disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)

    async def send_connection_event(self, device_address: str, connected: bool):
        """
        Broadcast a connection/disconnection event to all clients.
        
        Args:
            device_address: Device address
            connected: True if connected, False if disconnected
        """
        message = {
            "type": "ble.connection" if connected else "ble.disconnect",
            "device": device_address,
            "timestamp": str(asyncio.get_event_loop().time())
        }
        
        # Send to all clients
        disconnected_clients = []
        
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending connection event to client {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    async def broadcast_error(self, error_message: str, context: Optional[Dict] = None):
        """
        Broadcast an error message to all clients.
        
        Args:
            error_message: The error message
            context: Optional contextual information
        """
        message = {
            "type": "ble.error",
            "message": error_message,
            "timestamp": str(asyncio.get_event_loop().time())
        }
        
        if context:
            message["context"] = context
        
        # Send to all clients
        disconnected_clients = []
        
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending error message to client {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)

# Singleton instance
notification_manager = BleNotificationManager()

async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for BLE notifications.
    
    Args:
        websocket: The WebSocket connection
    """
    # We can't use FastAPI's Depends here since it causes circular imports
    # Instead, we'll get the service directly
    from backend.dependencies import get_ble_service
    ble_service = get_ble_service()
    
    client_id = str(uuid.uuid4())
    await notification_manager.connect(websocket, client_id)
    
    try:
        # Send initial connection status
        if ble_service.is_connected():
            await websocket.send_json({
                "type": "ble.connection",
                "device": ble_service.get_connected_device_address(),
                "timestamp": str(asyncio.get_event_loop().time())
            })
        
        # Main message loop
        while True:
            # Wait for messages from the client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                if message.get("type") == "subscribe" and "characteristic" in message:
                    char_uuid = message["characteristic"]
                    notification_manager.subscribe(client_id, char_uuid)
                    
                    # If notifications aren't already enabled, enable them
                    if ble_service.is_connected():
                        try:
                            await ble_service.start_notify(char_uuid)
                        except Exception as e:
                            logger.error(f"Error starting notifications for {char_uuid}: {e}")
                            await websocket.send_json({
                                "type": "error",
                                "characteristic": char_uuid,
                                "message": f"Failed to enable notifications: {str(e)}"
                            })
                    
                    await websocket.send_json({
                        "type": "subscription",
                        "status": "subscribed",
                        "characteristic": char_uuid
                    })
                
                elif message.get("type") == "unsubscribe" and "characteristic" in message:
                    char_uuid = message["characteristic"]
                    notification_manager.unsubscribe(client_id, char_uuid)
                    
                    # Check if we need to disable notifications
                    should_disable = True
                    for subs in notification_manager.subscriptions.values():
                        if char_uuid in subs:
                            should_disable = False
                            break
                    
                    if should_disable and ble_service.is_connected():
                        try:
                            await ble_service.stop_notify(char_uuid)
                        except Exception as e:
                            logger.error(f"Error stopping notifications for {char_uuid}: {e}")
                    
                    await websocket.send_json({
                        "type": "subscription",
                        "status": "unsubscribed",
                        "characteristic": char_uuid
                    })
                    
                elif message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Unknown message type"
                    })
                    
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
                
    except WebSocketDisconnect:
        notification_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        notification_manager.disconnect(client_id)