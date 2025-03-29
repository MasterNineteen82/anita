"""BLE routes package."""

from fastapi import APIRouter
from .device_routes import device_router
from .adapter_routes import adapter_router
from .service_routes import service_router
from .notification_routes import notification_router
from .health_routes import health_router

# Create consolidated router
ble_router = APIRouter(prefix="/api/ble", tags=["Bluetooth"])

# Include all sub-routers
ble_router.include_router(device_router)
ble_router.include_router(adapter_router)
ble_router.include_router(service_router)
ble_router.include_router(notification_router)
ble_router.include_router(health_router)

# Export the routers
__all__ = [
    "ble_router",
    "device_router",
    "adapter_router",
    "service_router",
    "notification_router",
    "health_router",
]