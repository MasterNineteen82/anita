from fastapi import FastAPI
import logging

logger = logging.getLogger(__name__)

def setup_routes(app: FastAPI):
    """Set up all WebSocket routes."""
    try:
        # Import the registration function rather than the module
        from .smartcard_ws import register_websocket_routes
        
        # Register the routes
        register_websocket_routes(app)
        logger.info("WebSocket routes configured successfully")
    except Exception as e:
        logger.error(f"Failed to set up WebSocket routes: {e}")