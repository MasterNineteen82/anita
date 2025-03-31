"""Bluetooth API routes.

This module serves as the main entry point for BLE API routes.
"""

import logging
from fastapi import APIRouter

# Create router
router = APIRouter()

# Import sub-routers
from backend.modules.ble.api import (
    device_router, 
    adapter_router, 
    service_router, 
    notification_router,
    health_router
)

# Import WebSocket functionality
from backend.modules.ble.comms.websocket import websocket_endpoint

# Include all routes from sub-routers
router.include_router(device_router)
router.include_router(adapter_router)
router.include_router(service_router)
router.include_router(notification_router)
router.include_router(health_router)

# Add WebSocket endpoint
router.add_websocket_route("/ws/ble", websocket_endpoint)

# Get logger
logger = logging.getLogger(__name__)

# Export the router
__all__ = ['router']