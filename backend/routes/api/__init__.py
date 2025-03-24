"""API routes for ANITA backend."""
# Import all route modules here so they're available when importing the package

# Import all route modules
from . import auth_routes
from . import biometric_routes
from . import ble_routes
from . import cache_routes
from . import card_routes
from . import device_routes
from . import hardware_routes
from . import mifare_routes
from . import mqtt_routes
from . import nfc_routes
from . import rfid_routes  # Added
from . import security_routes  # Added
from . import smartcard_routes
from . import system_routes
from . import uwb_routes
from . import simulation_routes
from . import alerts_routes


# Export routers from each module
__all__ = [
    "auth_routes",
    "biometric_routes",
    "ble_routes",
    "cache_routes",
    "card_routes",
    "device_routes",
    "hardware_routes",
    "mifare_routes",
    "mqtt_routes",
    "nfc_routes",
    "rfid_routes",  # Added
    "security_routes",  # Added
    "smartcard_routes",
    "system_routes",
    "uwb_routes",
    "simulation_routes",
    "alerts_routes",

    ]
