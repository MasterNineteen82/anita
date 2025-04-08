"""BLE device discovery and connection management."""

import logging
import asyncio
import platform
import time
from typing import Dict, Any, List, Optional, Tuple, Set, Union, Callable
import uuid
from threading import Lock

import bleak
from bleak import BleakScanner, BleakClient, BleakError

from backend.modules.ble.utils.events import ble_event_bus
from backend.modules.ble.utils.ble_metrics import get_metrics_collector
from backend.modules.ble.utils.ble_persistence import get_persistence_service
from backend.modules.ble.utils.ble_recovery import get_error_recovery
from backend.modules.ble.models import (
    BLEDeviceInfo, ConnectionStatus, ConnectionParams,
    ScanParams, ConnectionResult
)
from .adapter_manager import get_adapter_manager
from .exceptions import BleConnectionError, BleOperationError, BleNotSupportedError

logger = logging.getLogger(__name__)

class BleDeviceManager:
    """
    Centralized manager for BLE device operations.
    """

    def __init__(self):
        self._cached_devices = []
        self._connected_devices = {}
        self.logger = logger

    def set_logger(self, logger_instance):
        """
        Set a custom logger instance.
        """
        self.logger = logger_instance

    async def scan_devices(
        self,
        scan_time: float = 5.0,
        active: bool = True,
        name_prefix: Optional[str] = None,
        services: Optional[List[str]] = None,
        allow_duplicates: bool = False,
    ) -> List[Dict]:
        """
        Scan for BLE devices.

        Args:
            scan_time: Duration to scan in seconds.
            active: Whether to perform active scanning.
            name_prefix: Filter devices by name prefix.
            services: List of service UUIDs to filter by.
            allow_duplicates: Whether to allow duplicate advertisements.

        Returns:
            List of discovered devices.
        """
        try:
            self.logger.info("Starting BLE scan...")
            devices = await BleakScanner.discover(
                timeout=scan_time,
                service_uuids=services,
                scanning_mode="active" if active else "passive",
            )
            self._cached_devices = [
                {
                    "name": device.name,
                    "address": device.address,
                    "rssi": device.rssi,
                }
                for device in devices
                if not name_prefix or (device.name and device.name.startswith(name_prefix))
            ]
            self.logger.info(f"Discovered {len(self._cached_devices)} devices.")
            return self._cached_devices
        except BleakError as e:
            self.logger.error(f"BLE scan failed: {e}")
            raise

    async def connect_device(self, address: str) -> bool:
        """
        Connect to a BLE device.

        Args:
            address: The address of the device to connect to.

        Returns:
            True if the connection was successful, False otherwise.
        """
        try:
            self.logger.info(f"Attempting to connect to device at {address}...")
            client = BleakClient(address)
            await client.connect()
            self._connected_devices[address] = client
            self.logger.info(f"Successfully connected to {address}.")
            return True
        except BleakError as e:
            self.logger.error(f"Failed to connect to {address}: {e}")
            return False

    async def disconnect_device(self, address: str) -> bool:
        """
        Disconnect from a BLE device.

        Args:
            address: The address of the device to disconnect from.

        Returns:
            True if the disconnection was successful, False otherwise.
        """
        try:
            self.logger.info(f"Attempting to disconnect from device at {address}...")
            client = self._connected_devices.get(address)
            if client:
                await client.disconnect()
                del self._connected_devices[address]
                self.logger.info(f"Successfully disconnected from {address}.")
                return True
            else:
                self.logger.warning(f"No active connection found for {address}.")
                return False
        except BleakError as e:
            self.logger.error(f"Failed to disconnect from {address}: {e}")
            return False

    def get_cached_devices(self) -> List[Dict]:
        """
        Return the list of cached devices from the last scan.

        Returns:
            List of cached devices.
        """
        return self._cached_devices

    def get_connected_devices(self) -> List[str]:
        """
        Return the list of currently connected device addresses.

        Returns:
            List of connected device addresses.
        """
        return list(self._connected_devices.keys())

# Singleton instance (to be initialized on first use)
from threading import Lock

_device_manager = None
_device_manager_lock = Lock()

def get_device_manager() -> BleDeviceManager:
    """Get the singleton device manager instance."""
    global _device_manager
    if (_device_manager is None):
        with _device_manager_lock:
            if _device_manager is None:  # Double-checked locking
                _device_manager = BleDeviceManager()
    return _device_manager