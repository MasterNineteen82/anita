"""BLE Core Module.

This module provides the core Bluetooth functionality used throughout the BLE package:
- Device discovery and connection management
- Service and characteristic operations
- Adapter management
- Notification handling

Core Architecture:
- BleService: High-level facade providing the main API for BLE operations
- BleDeviceManager: Handles device discovery and connection management
- BleAdapterManager: Manages Bluetooth adapters and hardware configuration
- BleServiceManager: Manages GATT services, characteristics, and descriptors
- BleNotificationManager: Handles notification subscriptions and delivery
"""

# Import the manager classes
from .adapter_manager import BleAdapterManager
from .device_manager import BleDeviceManager
from .service_manager import BleServiceManager
from .notification_manager import BleNotificationManager
from .ble_service import BleService

# Import additional utilities
from .scanner import BleScanner
from .constants import BLE_CONSTANTS

# Re-export for convenience
from .exceptions import (
    BleConnectionError,
    BleServiceError,
    BleAdapterError,
    BleNotSupportedError,
    BleOperationError
)

# Version information
__version__ = "1.3.0"

# Define public API
__all__ = [
    # Main service 
    "BleService",
    
    # Manager classes
    "BleDeviceManager",
    "BleAdapterManager", 
    "BleServiceManager",
    "BleNotificationManager",
    
    # Utilities
    "BleScanner",
    "BLE_CONSTANTS",
    
    # Exceptions
    "BleConnectionError",
    "BleServiceError", 
    "BleAdapterError",
    "BleNotSupportedError",
    "BleOperationError"
]

# Singleton instances (to be initialized on first use)
_ble_service = None

def get_ble_service() -> BleService:
    """Get the singleton BleService instance."""
    global _ble_service
    if _ble_service is None:
        _ble_service = BleService()
    return _ble_service