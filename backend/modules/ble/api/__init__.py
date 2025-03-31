"""BLE API Routes Package.

This package provides the API routes for Bluetooth Low Energy operations:

Main components:
- device_router: Device discovery, connection and data exchange
- adapter_router: Bluetooth adapter management 
- service_router: BLE service and characteristic operations
- notification_router: Subscribe to and receive BLE notifications
- health_router: System health, diagnostics and metrics

Usage:
    from backend.modules.ble.api import ble_router
    
    # In FastAPI app:
    app.include_router(ble_router)
"""

from fastapi import APIRouter
from .device_routes import device_router
from .adapter_routes import adapter_router
from .service_routes import service_router
from .notification_routes import notification_router
from .health_routes import health_router

# Import the WebSocket endpoint
from backend.modules.ble.comms import websocket_endpoint

# Create consolidated router
ble_router = APIRouter(prefix="/api/ble", tags=["Bluetooth"])

# Include all sub-routers
ble_router.include_router(device_router)
ble_router.include_router(adapter_router)
ble_router.include_router(service_router)
ble_router.include_router(notification_router)
ble_router.include_router(health_router)

# Add the WebSocket endpoint
ble_router.add_websocket_route("/ws", websocket_endpoint)

# Export the routers
__all__ = [
    "ble_router",
    "device_router",
    "adapter_router",
    "service_router",
    "notification_router",
    "health_router",
    "websocket_endpoint"
]

# Module version and metadata
__version__ = "1.0.0"
__author__ = "BLE Module Team"