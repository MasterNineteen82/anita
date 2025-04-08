"""
BLE Manager bridge module.

This module provides backward compatibility with older code that depends on
the BLEManager class. It re-exports the new BleDeviceManager implementation
with a compatible interface.
"""

import warnings
import logging
from typing import Optional, Any
from .core.device_manager import BleDeviceManager, get_device_manager

logger = logging.getLogger(__name__)

class BLEManager:
    """
    Legacy BLE Manager class.

    This class forwards all operations to the new BleDeviceManager implementation.
    It exists solely for backward compatibility.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the BLE Manager.

        Args:
            logger: Optional logger instance
        """
        warnings.warn(
            "BLEManager is deprecated. Use BleDeviceManager instead.",
            DeprecationWarning, stacklevel=2
        )
        self._device_manager = get_device_manager()
        self.logger = logger or logging.getLogger(__name__)

        # If the device manager supports setting a logger, do so
        if hasattr(self._device_manager, 'set_logger'):
            self._device_manager.set_logger(self.logger)

    def __getattr__(self, name: str) -> Any:
        """Forward attribute access to the device manager."""
        return getattr(self._device_manager, name)


# Singleton instance for backward compatibility
_ble_manager = None

def get_ble_manager(logger: Optional[logging.Logger] = None) -> BLEManager:
    """
    Get the singleton BLE manager instance.

    Args:
        logger: Optional logger instance

    Returns:
        BLEManager instance
    """
    global _ble_manager
    if _ble_manager is None:
        _ble_manager = BLEManager(logger=logger)
    return _ble_manager