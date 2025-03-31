"""BLE event system to avoid circular imports."""

import logging
from typing import Dict, List, Any, Callable

logger = logging.getLogger(__name__)

class BleEventBus:
    """Simple event bus for BLE events."""
    
    def __init__(self):
        self.handlers: Dict[str, List[Callable]] = {}
        
    def on(self, event_name: str, handler: Callable) -> None:
        """
        Register a handler for an event.
        
        Args:
            event_name: The name of the event
            handler: The handler function
        """
        if event_name not in self.handlers:
            self.handlers[event_name] = []
            
        self.handlers[event_name].append(handler)
        
    def off(self, event_name: str, handler: Callable) -> None:
        """
        Unregister a handler for an event.
        
        Args:
            event_name: The name of the event
            handler: The handler function
        """
        if event_name in self.handlers:
            try:
                self.handlers[event_name].remove(handler)
            except ValueError:
                pass
                
    def emit(self, event_name: str, data: Any = None) -> None:
        """
        Emit an event.
        
        Args:
            event_name: The name of the event
            data: The event data
        """
        if event_name not in self.handlers:
            return
            
        for handler in self.handlers[event_name]:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Error in event handler for {event_name}: {e}", exc_info=True)

# Create a singleton instance
ble_event_bus = BleEventBus()