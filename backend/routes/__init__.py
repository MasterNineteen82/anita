"""
Routes package initialization.
Exposes all API routes for the application.
"""

# Import all route modules except monitoring_router
from .api.auth_routes import router as auth_router
from .api.biometric_routes import router as biometric_router
from .api.ble_routes import router as ble_router
from .api.cache_routes import router as cache_router
from .api.card_routes import router as card_router
from .api.device_routes import router as device_router
from .api.hardware_routes import router as hardware_router
from .api.mifare_routes import router as mifare_router
from .api.mqtt_routes import router as mqtt_router
from .api.nfc_routes import router as nfc_router
from .api.rfid_routes import router as rfid_router
from .api.security_routes import router as security_router
from .api.smartcard_routes import router as smartcard_router
from .api.system_routes import router as system_router
from .api.uwb_routes import router as uwb_router

# Define a getter for monitoring_router
def get_monitoring_router():
    from . import monitoring_router
    return monitoring_router

# Export all routers
__all__ = [
    "auth_router",
    "biometric_router",
    "ble_router",
    "cache_router",
    "card_router",
    "device_router",
    "hardware_router",
    "mifare_router",
    "mqtt_router",
    "nfc_router",
    "rfid_router",
    "security_router",
    "smartcard_router",
    "system_router",
    "uwb_router",
    "get_monitoring_router",  # Export the function instead of the module directly
]