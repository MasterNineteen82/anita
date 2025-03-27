"""API routes for ANITA backend."""
# Import all route modules here so they're available when importing the package

# Import all route modules
from . import alerts_routes
from . import auth_routes
from . import biometric_routes
from . import cache_routes
from . import card_routes
from . import device_routes
from . import hardware_routes
from . import mifare_routes
from . import monitoring_router
from . import mqtt_routes
from . import nfc_routes
from . import rfid_routes
from . import security_routes
from . import smartcard_routes
from . import smartcard
from . import system_routes
from . import uwb_routes
from . import simulation_routes




# Export routers from each module
__all__ = [
    "alerts_routes",
    "auth_routes",
    "biometric_routes",
    "cache_routes",
    "card_routes",
    "device_routes",
    "hardware_routes",
    "mifare_routes",
    "monitoring_router",
    "mqtt_routes",
    "nfc_routes",
    "rfid_routes",  # Added
    "security_routes",  # Added
    "smartcard_routes",
    "smartcard",
    "system_routes",
    "simulation_routes"
    "uwb_routes",
    "simulation_routes",


    ]