"""API routes package."""

from fastapi import APIRouter
# Import all route modules to make them available
from . import (
    device_routes, smartcard_routes, nfc_routes, mifare_routes, biometric_routes,
    card_routes, system_routes, uwb_routes, auth_routes, cache_routes,
    hardware_routes, mqtt_routes, rfid_routes, security_routes
)

# Create the main API router that will include all sub-routers
router = APIRouter()

# Include all route modules' routers
router.include_router(mqtt_routes.router)  # Add this line to use mqtt_routes
# Add similar lines for other route modules if they're not already included elsewhere

# Export the router
__all__ = ["router", "mqtt_routes"]  # Add mqtt_routes to __all__