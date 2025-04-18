# backend/websockets/manager.py
import asyncio
import json
import logging
from typing import Dict, List, Set, Any, Optional, Callable, Awaitable
import uuid
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect, HTTPException, status
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

# Type definitions for handler functions
WebSocketHandler = Callable[[WebSocket, dict], Awaitable[None]]

class WebSocketClient:
    """Represents a connected WebSocket client."""
    def __init__(self, websocket: WebSocket, client_id: str = None, user_id: str = None):
        self.websocket = websocket
        self.client_id = client_id or str(uuid.uuid4())
        self.user_id = user_id
        self.rooms: Set[str] = set()
        self.connected_at = datetime.now()
        self.last_activity = datetime.now()
        self.metadata: Dict[str, Any] = {}
        
    def update_activity(self):
        """Update the last activity timestamp."""
        self.last_activity = datetime.now()

class WebSocketManager:
    """Enhanced WebSocket connection manager with rooms and authentication."""
    
    def __init__(self):
        # Map of WebSocket objects to client info
        self.active_clients: Dict[WebSocket, WebSocketClient] = {}
        # Map of room names to sets of WebSocket objects
        self.rooms: Dict[str, Set[WebSocket]] = {}
        # Map of message types to handler functions
        self.message_handlers: Dict[str, WebSocketHandler] = {}
        # Metrics
        self.connection_count = 0
        self.message_count = 0
        
    async def connect(self, websocket: WebSocket, client_id: str = None, user_id: str = None) -> str:
        """Accept a WebSocket connection and register the client."""
        await websocket.accept()
        client = WebSocketClient(websocket, client_id, user_id)
        self.active_clients[websocket] = client
        self.connection_count += 1
        logger.info(f"Client {client.client_id} connected. Total connections: {self.connection_count}")
        return client.client_id
        
    async def disconnect(self, websocket: WebSocket) -> None:
        """Disconnect and cleanup a WebSocket client."""
        if websocket in self.active_clients:
            client = self.active_clients[websocket]
            
            # Remove from all rooms
            for room in list(client.rooms):
                await self.leave_room(websocket, room)
            
            # Remove from active clients
            del self.active_clients[websocket]
            self.connection_count -= 1
            
            logger.info(f"Client {client.client_id} disconnected. Total connections: {self.connection_count}")
    
    async def send_message(self, websocket: WebSocket, message: dict) -> bool:
        """Send a message to a specific client."""
        if websocket not in self.active_clients:
            logger.warning("Attempted to send message to disconnected client")
            return False
        
        try:
            await websocket.send_json(message)
            self.active_clients[websocket].update_activity()
            self.message_count += 1
            return True
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            return False
    
    async def broadcast_message(self, message: dict, exclude: WebSocket = None) -> int:
        """Broadcast a message to all connected clients."""
        sent_count = 0
        for client_ws in list(self.active_clients.keys()):
            if client_ws != exclude:
                success = await self.send_message(client_ws, message)
                if success:
                    sent_count += 1
        return sent_count
    
    async def broadcast_to_room(self, room: str, message: dict, exclude: WebSocket = None) -> int:
        """Broadcast a message to all clients in a specific room."""
        if room not in self.rooms:
            logger.warning(f"Attempted to broadcast to non-existent room: {room}")
            return 0
            
        sent_count = 0
        for client_ws in self.rooms[room]:
            if client_ws != exclude and client_ws in self.active_clients:
                success = await self.send_message(client_ws, message)
                if success:
                    sent_count += 1
        return sent_count
    
    async def join_room(self, websocket: WebSocket, room: str) -> bool:
        """Add a client to a room."""
        if websocket not in self.active_clients:
            logger.warning("Attempted to add disconnected client to room")
            return False
            
        # Create room if it doesn't exist
        if room not in self.rooms:
            self.rooms[room] = set()
            
        # Add client to room
        self.rooms[room].add(websocket)
        self.active_clients[websocket].rooms.add(room)
        
        logger.info(f"Client {self.active_clients[websocket].client_id} joined room: {room}")
        return True
    
    async def leave_room(self, websocket: WebSocket, room: str) -> bool:
        """Remove a client from a room."""
        if websocket not in self.active_clients:
            return False
            
        if room in self.rooms and websocket in self.rooms[room]:
            self.rooms[room].remove(websocket)
            self.active_clients[websocket].rooms.remove(room)
            
            # Clean up empty rooms
            if not self.rooms[room]:
                del self.rooms[room]
                
            logger.info(f"Client {self.active_clients[websocket].client_id} left room: {room}")
            return True
        return False
    
    def get_client_id(self, websocket: WebSocket) -> Optional[str]:
        """Get the client ID for a WebSocket."""
        if websocket in self.active_clients:
            return self.active_clients[websocket].client_id
        return None
    
    def get_user_id(self, websocket: WebSocket) -> Optional[str]:
        """Get the user ID for a WebSocket if authenticated."""
        if websocket in self.active_clients:
            return self.active_clients[websocket].user_id
        return None
    
    def is_authenticated(self, websocket: WebSocket) -> bool:
        """Check if a WebSocket client is authenticated."""
        if websocket in self.active_clients:
            return self.active_clients[websocket].user_id is not None
        return False
    
    def get_clients_in_room(self, room: str) -> List[WebSocketClient]:
        """Get all clients in a specific room."""
        if room not in self.rooms:
            return []
        
        return [
            self.active_clients[ws] for ws in self.rooms[room] 
            if ws in self.active_clients
        ]
    
    def register_message_handler(self, msg_type: str, handler: WebSocketHandler) -> None:
        """Register a handler function for a specific message type."""
        self.message_handlers[msg_type] = handler
        logger.info(f"Registered handler for message type: {msg_type}")
    
    async def require_authentication(self, websocket: WebSocket) -> bool:
        """
        Check if the WebSocket connection has valid authentication.
        For now, we'll check for a token in query parameters.
        In a real implementation, this would integrate with your auth system.
        """
        try:
            # Extract token from query parameters
            query_params = dict(websocket.query_params)
            token = query_params.get("token")
            
            if not token:
                await websocket.send_text("Authentication required: No token provided")
                await websocket.close(code=1008, reason="Authentication required")
                return False
                
            # Here you would validate the token against your auth system
            # For demonstration, we'll accept any non-empty token
            # In production, replace this with actual token validation
            if len(token) > 0:
                logger.info(f"Authentication successful for token: {token[:4]}...")
                return True
            else:
                await websocket.send_text("Authentication failed: Invalid token")
                await websocket.close(code=1008, reason="Invalid token")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            await websocket.close(code=1011, reason="Server error during authentication")
            return False
            
    async def send_personal_message(self, message: dict, websocket: WebSocket) -> bool:
        """Send a message to a specific client."""
        if websocket not in self.active_clients:
            logger.warning("Attempted to send message to disconnected client")
            return False
            
        try:
            await websocket.send_json(message)
            self.active_clients[websocket].update_activity()
            self.message_count += 1
            return True
        except Exception as e:
            logger.error(f"Error sending personal message: {str(e)}")
            return False
            
    async def send_error(self, websocket: WebSocket, error_message: str) -> bool:
        """Send an error message to a specific client."""
        error_payload = {
            "type": "error",
            "data": {
                "message": error_message
            }
        }
        return await self.send_personal_message(error_payload, websocket)
        
    async def handle_message(self, websocket: WebSocket, message: dict) -> bool:
        """Handle an incoming message based on its type."""
        if websocket not in self.active_clients:
            logger.warning("Received message from disconnected client")
            return False
            
        # Update client activity timestamp
        self.active_clients[websocket].update_activity()
            
        # Extract message type and data
        msg_type = message.get("type")
        data = message.get("data", {})
            
        if not msg_type:
            await self.send_error(websocket, "Message type is required")
            return False
            
        # Find handler for this message type
        handler = self.message_handlers.get(msg_type)
        if not handler:
            await self.send_error(websocket, f"No handler found for message type: {msg_type}")
            return False
            
        try:
            # Call the handler with websocket and data
            await handler(websocket, data)
            return True
        except Exception as e:
            logger.exception(f"Error in message handler for type {msg_type}: {str(e)}")
            await self.send_error(websocket, f"Error handling message: {str(e)}")
            return False
    
    async def authenticate_client(self, websocket: WebSocket, user_id: str) -> bool:
        """Set the user ID for a client, marking them as authenticated."""
        if websocket in self.active_clients:
            self.active_clients[websocket].user_id = user_id
            logger.info(f"Client {self.active_clients[websocket].client_id} authenticated as user {user_id}")
            return True
        return False
    
    def get_connection_stats(self) -> dict:
        """Get statistics about current WebSocket connections."""
        return {
            "active_connections": self.connection_count,
            "total_messages": self.message_count,
            "active_rooms": len(self.rooms),
            "room_connections": {room: len(clients) for room, clients in self.rooms.items()},
            "authenticated_clients": sum(1 for client in self.active_clients.values() if client.user_id is not None)
        }

# Create a global instance
manager = WebSocketManager()