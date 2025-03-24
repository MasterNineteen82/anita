from fastapi import FastAPI
import logging
from . import smartcard_ws

logger = logging.getLogger(__name__)

def setup_routes(app: FastAPI):
    """Set up all WebSocket routes."""
    try:
        # Import only smartcard_ws - remove any reference to device_ws
        from .smartcard_ws import register_websocket_routes
        
        # Register websocket routes
        register_websocket_routes(app)
        logger.info("WebSocket routes configured successfully")
    except Exception as e:
        logger.error(f"Failed to set up WebSocket routes: {e}")