"""Main BLE router that aggregates all sub-routers."""

from fastapi import APIRouter
import logging

from backend.modules import ble

# Import all sub-routers
from .adapter_routes import adapter_router
from .device_routes import device_router
from .service_routes import service_router
from .health_routes import health_router
from .notification_routes import notification_router


# Create main router
router = APIRouter(prefix="/ble", tags=["BLE"])

# Include all sub-routers
router.include_router(adapter_router)
router.include_router(device_router)
router.include_router(service_router)
router.include_router(health_router)
router.include_router(notification_router)


__all__ = ["router"]