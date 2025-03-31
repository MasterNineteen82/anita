"""BLE event bus for communication between components."""

import asyncio
import logging
from typing import Dict, List, Any, Callable, Awaitable, Optional

logger = logging.getLogger(__name__)

class BleEventBus:
    """
    Event bus for BLE-related events.
    
    This class provides a simple event system for communication
    between different components of the BLE module.
    """
    
    def __init__(self):
        """Initialize the event bus."""
        self.handlers = {}
        self.ws_broadcast_fn = None
    
    def on(self, event_type: str, handler: Callable[..., Awaitable[None]]) -> None:
        """
        Register a handler for an event type.
        
        Args:
            event_type: Event type to listen for
            handler: Async function to handle the event
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        
        self.handlers[event_type].append(handler)
        logger.debug(f"Registered handler for event: {event_type}")
    
    def off(self, event_type: str, handler: Optional[Callable[..., Awaitable[None]]] = None) -> None:
        """
        Remove a handler for an event type.
        
        Args:
            event_type: Event type
            handler: Handler to remove (if None, removes all handlers for the event)
        """
        if handler is None:
            self.handlers[event_type] = []
            logger.debug(f"Removed all handlers for event: {event_type}")
        elif event_type in self.handlers:
            self.handlers[event_type] = [h for h in self.handlers[event_type] if h != handler]
            logger.debug(f"Removed specific handler for event: {event_type}")
    
    async def emit(self, event_type: str, data: Any = None) -> None:
        """
        Emit an event.
        
        Args:
            event_type: Event type to emit
            data: Event data
        """
        logger.debug(f"Emitting event: {event_type}")
        
        if event_type in self.handlers:
            tasks = []
            for handler in self.handlers[event_type]:
                try:
                    if data is not None:
                        task = asyncio.create_task(handler(data))
                    else:
                        task = asyncio.create_task(handler())
                    tasks.append(task)
                except Exception as e:
                    logger.error(f"Error creating task for event {event_type}: {e}")
            
            # Wait for all handlers to complete
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        
        # Also broadcast to WebSocket if registered
        if self.ws_broadcast_fn is not None:
            try:
                # Convert data to a format suitable for WebSocket transmission
                ws_data = data if isinstance(data, dict) else {"data": data}
                await self.ws_broadcast_fn(event_type, ws_data)
            except Exception as e:
                logger.error(f"Error broadcasting event to WebSocket: {e}")
    
    def register_ws_broadcast(self, broadcast_fn: Callable[[str, Dict[str, Any]], Awaitable[None]]) -> None:
        """
        Register a WebSocket broadcast function.
        
        Args:
            broadcast_fn: Function to broadcast messages to WebSocket clients
        """
        self.ws_broadcast_fn = broadcast_fn
        logger.debug("Registered WebSocket broadcast function")

# Singleton instance
ble_event_bus = BleEventBus()