"""
Re-export of the BLE Service from core module.
This file ensures backward compatibility with existing import patterns.
"""

# Re-export BleService and get_ble_service from core implementation
from backend.modules.ble.core.ble_service import BleService, get_ble_service

# Ensure these are included in __all__ for proper importing
__all__ = ['BleService', 'get_ble_service']