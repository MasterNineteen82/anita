"""BLE notification management."""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable, Union
import time
import uuid
import json

class BleNotificationManager:
    """Manage BLE notifications, callbacks, and WebSocket distribution."""
    
    def __init__(self, logger=None):
        """Initialize the notification manager."""
        self.logger = logger or logging.getLogger(__name__)
        self._callbacks = {}  # char_uuid -> [callbacks]
        self._websocket_connections = set()  # Set of active WebSocket connections
        self._notification_history = {}  # char_uuid -> [last N notifications]
        self._max_history = 20  # Store up to this many notifications per characteristic
        self._active_notifications = set()  # Set of active notification UUIDs
    
    def add_callback(self, char_uuid: str, callback: Callable) -> str:
        """
        Register a callback for notifications from a characteristic.
        
        Args:
            char_uuid: UUID of the characteristic
            callback: Function to call with notification data
            
        Returns:
            Callback ID that can be used to remove the callback
        """
        char_uuid = char_uuid.lower()
        callback_id = str(uuid.uuid4())
        
        if char_uuid not in self._callbacks:
            self._callbacks[char_uuid] = {}
        
        self._callbacks[char_uuid][callback_id] = callback
        self.logger.debug(f"Added callback {callback_id} for {char_uuid}")
        
        return callback_id
    
    def remove_callback(self, char_uuid: str, callback_id: str) -> bool:
        """
        Remove a registered callback.
        
        Args:
            char_uuid: UUID of the characteristic
            callback_id: ID returned when adding the callback
            
        Returns:
            True if callback was removed
        """
        char_uuid = char_uuid.lower()
        
        if char_uuid not in self._callbacks:
            return False
        
        if callback_id not in self._callbacks[char_uuid]:
            return False
        
        del self._callbacks[char_uuid][callback_id]
        
        # Clean up empty dictionaries
        if not self._callbacks[char_uuid]:
            del self._callbacks[char_uuid]
        
        self.logger.debug(f"Removed callback {callback_id} for {char_uuid}")
        return True
    
    def register_websocket(self, websocket):
        """Register a WebSocket connection for receiving notifications."""
        self._websocket_connections.add(websocket)
        self.logger.debug(f"WebSocket registered, total: {len(self._websocket_connections)}")
    
    def unregister_websocket(self, websocket):
        """Unregister a WebSocket connection."""
        if websocket in self._websocket_connections:
            self._websocket_connections.remove(websocket)
            self.logger.debug(f"WebSocket unregistered, remaining: {len(self._websocket_connections)}")
    
    def process_notification(self, char_uuid: str, data: Union[bytes, bytearray]) -> None:
        """
        Process a received notification.
        
        Args:
            char_uuid: UUID of the characteristic
            data: Notification data
        """
        char_uuid = char_uuid.lower()
        self.logger.debug(f"Processing notification from {char_uuid}")
        
        # Convert data for easier handling
        if isinstance(data, (bytes, bytearray)):
            data_hex = data.hex()
            data_str = None
            try:
                # Try to decode as UTF-8
                data_str = data.decode('utf-8')
            except UnicodeDecodeError:
                pass
        else:
            data_hex = str(data)
            data_str = str(data)
        
        # Add to history
        if char_uuid not in self._notification_history:
            self._notification_history[char_uuid] = []
        
        self._notification_history[char_uuid].append({
            "timestamp": time.time(),
            "data_hex": data_hex,
            "data_str": data_str
        })
        
        # Trim history if needed
        if len(self._notification_history[char_uuid]) > self._max_history:
            self._notification_history[char_uuid] = self._notification_history[char_uuid][-self._max_history:]
        
        # Call callbacks
        if char_uuid in self._callbacks:
            for callback_id, callback in self._callbacks[char_uuid].items():
                try:
                    callback(char_uuid, data)
                except Exception as e:
                    self.logger.error(f"Error in notification callback {callback_id}: {e}")
        
        # Send to WebSocket clients
        if self._websocket_connections:
            asyncio.create_task(self._send_notification_to_websockets(char_uuid, data_hex, data_str))
    
    async def _send_notification_to_websockets(self, char_uuid: str, data_hex: str, data_str: Optional[str]) -> None:
        """
        Send a notification to all connected WebSockets.
        
        Args:
            char_uuid: UUID of the characteristic
            data_hex: Hexadecimal string representation of the data
            data_str: String representation of the data (if decodable as UTF-8)
        """
        if not self._websocket_connections:
            return
        
        # Create event message
        message = {
            "type": "notification",
            "characteristic": char_uuid,
            "data": data_hex,
            "timestamp": time.time()
        }
        
        if data_str:
            message["data_str"] = data_str
        
        message_json = json.dumps(message)
        
        # Set of connections to remove (if they fail)
        to_remove = set()
        
        # Send to all WebSockets
        for websocket in self._websocket_connections:
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                self.logger.error(f"Error sending notification to WebSocket: {e}")
                to_remove.add(websocket)
        
        # Remove failed connections
        for websocket in to_remove:
            self.unregister_websocket(websocket)
    
    def mark_notification_active(self, char_uuid: str) -> None:
        """Mark a characteristic as having active notifications."""
        self._active_notifications.add(char_uuid.lower())
    
    def mark_notification_inactive(self, char_uuid: str) -> None:
        """Mark a characteristic as not having active notifications."""
        char_uuid = char_uuid.lower()
        if char_uuid in self._active_notifications:
            self._active_notifications.remove(char_uuid)
    
    def get_active_notifications(self) -> List[str]:
        """Get a list of characteristics with active notifications."""
        return list(self._active_notifications)
    
    def is_notification_active(self, char_uuid: str) -> bool:
        """Check if notifications are active for a characteristic."""
        return char_uuid.lower() in self._active_notifications
    
    def get_notification_history(self, char_uuid: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get notification history.
        
        Args:
            char_uuid: Optional characteristic UUID to filter by
            
        Returns:
            Dictionary mapping characteristic UUIDs to notification histories
        """
        if char_uuid:
            char_uuid = char_uuid.lower()
            return {char_uuid: self._notification_history.get(char_uuid, [])}
        else:
            return self._notification_history
    
    def clear_notification_history(self, char_uuid: Optional[str] = None) -> None:
        """
        Clear notification history.
        
        Args:
            char_uuid: Optional characteristic UUID to clear, or all if None
        """
        if char_uuid:
            char_uuid = char_uuid.lower()
            if char_uuid in self._notification_history:
                del self._notification_history[char_uuid]
        else:
            self._notification_history = {}
    
    def clear_all(self) -> None:
        """Clear all callbacks, active notifications, and history."""
        self._callbacks = {}
        self._active_notifications = set()
        self._notification_history = {}
        self.logger.info("Cleared all notification data")