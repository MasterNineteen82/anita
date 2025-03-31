"""BLE notification management and subscription handling."""

import logging
import asyncio
import time
from typing import Dict, Any, List, Optional, Callable, Union
from collections import deque

from backend.modules.ble.models import (
    NotificationEvent, NotificationHistory, CharacteristicValue,
    NotificationMessage, MessageType
)
from backend.modules.ble.utils.events import ble_event_bus
from backend.modules.ble.comms import websocket_manager, broadcast_message
from .exceptions import BleConnectionError, BleServiceError

class BleNotificationManager:
    """
    Manages BLE characteristic notifications.
    
    Provides functionality for:
    - Subscribing/unsubscribing to characteristic notifications
    - Tracking notification history
    - Delivering notifications to WebSocket clients
    - Notification callbacks and handlers
    """
    
    def __init__(self, service_manager=None, max_history: int = 1000, logger=None):
        """
        Initialize the notification manager.
        
        Args:
            service_manager: Optional service manager to use for operations
            max_history: Maximum number of notifications to keep in history
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.service_manager = service_manager
        self.max_history = max_history
        
        # Notification history (deque for efficient size limiting)
        self._notification_history: Dict[str, deque] = {}
        
        # Active subscriptions
        self._active_subscriptions: Dict[str, Dict[str, Any]] = {}
        
        # Register for events
        ble_event_bus.on("device_disconnected", self._handle_device_disconnected)
    
    def set_service_manager(self, service_manager):
        """Set the service manager to use for operations."""
        self.service_manager = service_manager
    
    async def subscribe_to_characteristic(
        self, characteristic_uuid: str, enable: bool = True
    ) -> bool:
        """
        Subscribe to notifications for a characteristic.
        
        Args:
            characteristic_uuid: UUID of the characteristic
            enable: Whether to enable (True) or disable (False) notifications
            
        Returns:
            True if successful
        """
        if not self.service_manager:
            raise BleServiceError("No service manager available")
        
        try:
            if enable:
                # Subscribe to the characteristic
                success = await self.service_manager.start_notify(
                    characteristic_uuid, self._notification_callback
                )
                
                if success:
                    # Track the subscription
                    self._active_subscriptions[characteristic_uuid] = {
                        "timestamp": time.time(),
                        "enabled": True
                    }
                    
                    # Emit event
                    ble_event_bus.emit("notification_subscribed", {
                        "uuid": characteristic_uuid
                    })
                
                return success
            else:
                # Unsubscribe from the characteristic
                success = await self.service_manager.stop_notify(characteristic_uuid)
                
                if success and characteristic_uuid in self._active_subscriptions:
                    # Update subscription status
                    self._active_subscriptions[characteristic_uuid]["enabled"] = False
                    
                    # Emit event
                    ble_event_bus.emit("notification_unsubscribed", {
                        "uuid": characteristic_uuid
                    })
                
                return success
        except Exception as e:
            self.logger.error(f"Error subscribing to characteristic: {e}", exc_info=True)
            raise BleServiceError(f"Error subscribing to characteristic: {e}")
    
    def get_active_subscriptions(self) -> List[str]:
        """
        Get a list of characteristic UUIDs with active subscriptions.
        
        Returns:
            List of characteristic UUIDs
        """
        return [
            uuid for uuid, data in self._active_subscriptions.items()
            if data.get("enabled", False)
        ]
    
    def get_notification_history(
        self, characteristic_uuid: Optional[str] = None, limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get the notification history for a characteristic.
        
        Args:
            characteristic_uuid: Optional UUID to filter by
            limit: Maximum number of events to return
            
        Returns:
            Dictionary with notification events
        """
        if characteristic_uuid:
            # Get history for a specific characteristic
            events = list(self._notification_history.get(characteristic_uuid, []))[-limit:]
            return {
                "events": events,
                "count": len(events),
                "characteristic_uuid": characteristic_uuid
            }
        else:
            # Get combined history across all characteristics
            all_events = []
            for uuid, events in self._notification_history.items():
                all_events.extend([
                    {**event, "characteristic_uuid": uuid}
                    for event in events
                ])
            
            # Sort by timestamp (most recent first)
            all_events.sort(key=lambda e: e.get("timestamp", 0), reverse=True)
            all_events = all_events[:limit]
            
            return {
                "events": all_events,
                "count": len(all_events)
            }
    
    def clear_notification_history(self, characteristic_uuid: Optional[str] = None) -> None:
        """
        Clear notification history.
        
        Args:
            characteristic_uuid: Optional UUID to clear history for
        """
        if characteristic_uuid:
            # Clear history for a specific characteristic
            if characteristic_uuid in self._notification_history:
                self._notification_history[characteristic_uuid] = deque(maxlen=self.max_history)
        else:
            # Clear all history
            self._notification_history = {}
    
    async def clear_all_subscriptions(self) -> bool:
        """
        Clear all subscriptions.
        
        Returns:
            True if successful
        """
        if not self.service_manager:
            # If there's no service manager, just clear the tracking
            self._active_subscriptions = {}
            return True
        
        try:
            # Get a copy of the keys
            uuids = list(self._active_subscriptions.keys())
            
            # Unsubscribe from each characteristic
            for uuid in uuids:
                if self._active_subscriptions[uuid].get("enabled", False):
                    try:
                        await self.service_manager.stop_notify(uuid)
                    except Exception as e:
                        self.logger.warning(f"Error unsubscribing from {uuid}: {e}")
            
            # Clear the tracking dict
            self._active_subscriptions = {}
            
            return True
        except Exception as e:
            self.logger.error(f"Error clearing subscriptions: {e}", exc_info=True)
            return False
    
    # Notification callback from device
    async def _notification_callback(
        self, characteristic_uuid: str, data: Union[bytes, bytearray]
    ) -> None:
        """
        Handle a notification from a characteristic.
        
        This method is called when a notification is received from a device.
        It stores the notification in history and broadcasts it to WebSocket clients.
        
        Args:
            characteristic_uuid: UUID of the characteristic
            data: Notification data
        """
        try:
            # Create a notification event
            timestamp = time.time()
            
            # Convert data to various formats for flexibility
            char_value = CharacteristicValue(
                hex=data.hex() if data else "",
                text=self._try_decode_bytes(data),
                bytes=[b for b in data] if data else [],
                int=self._try_convert_to_int(data)
            )
            
            # Create event object
            event = {
                "timestamp": timestamp,
                "value": char_value.dict()
            }
            
            # Store in history
            if characteristic_uuid not in self._notification_history:
                self._notification_history[characteristic_uuid] = deque(maxlen=self.max_history)
            
            self._notification_history[characteristic_uuid].append(event)
            
            # Broadcast to WebSocket clients
            notification_message = {
                "type": MessageType.NOTIFICATION,
                "characteristic": characteristic_uuid,
                "value": char_value.dict(),
                "timestamp": timestamp
            }
            
            # Use the broadcast function from comms package
            await broadcast_message(MessageType.NOTIFICATION, {
                "characteristic": characteristic_uuid,
                "value": char_value.dict(),
                "timestamp": timestamp
            })
            
            # Emit event
            ble_event_bus.emit("notification_received", {
                "uuid": characteristic_uuid,
                "value": char_value.dict(),
                "timestamp": timestamp
            })
        except Exception as e:
            self.logger.error(f"Error handling notification: {e}", exc_info=True)
    
    # Event handlers
    async def _handle_device_disconnected(self, event_data: Dict[str, Any]) -> None:
        """
        Handle device disconnection.
        
        Clears active subscriptions when a device disconnects.
        
        Args:
            event_data: Event data
        """
        # Just clear subscription tracking - the service manager will
        # take care of stopping notifications on the device side
        self._active_subscriptions = {}
    
    # Helper methods
    def _try_decode_bytes(self, value: bytes) -> str:
        """Try to decode bytes to UTF-8 string."""
        if not value:
            return ""
        try:
            return value.decode('utf-8')
        except UnicodeDecodeError:
            return "(binary data)"

    def _try_convert_to_int(self, value: bytes) -> Optional[int]:
        """Try to convert bytes to integer value."""
        if not value or len(value) not in [1, 2, 4, 8]:
            return None
            
        try:
            return int.from_bytes(value, byteorder='little', signed=False)
        except Exception:
            return None