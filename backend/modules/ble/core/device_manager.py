"""BLE device discovery and connection management."""

import logging
import asyncio
import platform
import time
from typing import Dict, Any, List, Optional, Tuple, Set, Union, Callable
import uuid
from threading import Lock
import binascii

import bleak
from bleak import BleakClient, BleakError

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
from backend.modules.ble.utils.ble_scanner_wrapper import get_ble_scanner
from backend.modules.ble.utils.ble_device_info import enhance_device_info

logger = logging.getLogger(__name__)

class BleDeviceManager:
    """
    Centralized manager for BLE device operations.
    """

    def __init__(self):
        self._cached_devices = []
        self._connected_devices = {}
        self.logger = logger
        self._scanner = get_ble_scanner()
        self._mock_mode = False
        self._mock_devices = self._get_mock_devices()

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
            self.logger.info("Starting BLE scan using thread-safe scanner...")
            
            if self._mock_mode:
                self.logger.info("Using mock devices for scan")
                devices = self._mock_devices
            else:
                devices = await self._scanner.discover_devices(
                    timeout=scan_time,
                    service_uuids=services,
                    active=active
                )
            
            processed_devices = []
            for device in devices:
                if name_prefix and not (device.get("name") and device.get("name").startswith(name_prefix)):
                    continue

                # Process metadata to ensure serializability
                serializable_metadata = {}
                if device.get("metadata"):
                    for key, value in device.get("metadata").items():
                        if isinstance(value, dict):
                            # Handle nested dicts like manufacturer_data
                            serializable_metadata[key] = {
                                m_key: binascii.hexlify(m_value).decode('ascii') 
                                       if isinstance(m_value, bytes) else m_value
                                for m_key, m_value in value.items()
                            }
                        elif isinstance(value, bytes):
                            serializable_metadata[key] = binascii.hexlify(value).decode('ascii')
                        else:
                            serializable_metadata[key] = value
                        
                device_info = {
                    "address": device.get("address"),
                    "name": device.get("name") or "Unknown",
                    # "details": device.get("details"),  # Removed: Causes serialization errors
                    "rssi": device.get("rssi"),
                    "metadata": serializable_metadata
                }
                processed_devices.append(device_info)
        
            self._cached_devices = processed_devices
            self.logger.info(f"Discovered {len(processed_devices)} BLE devices")
            return processed_devices
        except Exception as e:
            self.logger.error(f"Error during BLE scan: {e}", exc_info=True)
            if self._mock_mode:
                self.logger.info("Returning mock devices due to scan error")
                return self._mock_devices
            raise BleOperationError(f"Failed to scan for devices: {str(e)}")
            
    def _get_test_devices(self):
        """Generate realistic test devices when real scanning fails due to Windows issues."""
        self.logger.info("Generating test devices for Windows platform")
        test_devices = [
            {
                "address": "11:22:33:44:55:66",
                "name": "Fitness Tracker Pro",
                "rssi": -65,
                "is_real": False,
                "metadata": {
                    "manufacturer_data": {"76": "1403010b13187164"},
                    "service_uuids": ["180d", "180f"]  # Heart rate and battery services
                },
                "source": "test_windows"
            },
            {
                "address": "22:33:44:55:66:77",
                "name": "Smart Watch XR40",
                "rssi": -58,
                "is_real": False,
                "metadata": {
                    "manufacturer_data": {"89": "0300"},
                    "service_uuids": ["1800", "1801", "180a"]  # Generic services
                },
                "source": "test_windows"
            },
            {
                "address": "33:44:55:66:77:88",
                "name": "BLE Temperature Sensor",
                "rssi": -72,
                "is_real": False,
                "metadata": {
                    "manufacturer_data": {"106": "07569abcd"},
                    "service_uuids": ["181a"]  # Environmental sensing service
                },
                "source": "test_windows"
            }
        ]
        self._cached_devices = test_devices
        return test_devices

    async def connect_device(
        self,
        address: str,
        connection_params: Optional[ConnectionParams] = None,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ) -> ConnectionResult:
        """
        Connect to a BLE device with retry logic.

        Args:
            address: Device address.
            connection_params: Connection parameters.
            max_retries: Maximum number of connection retries.
            retry_delay: Delay between retries in seconds.

        Returns:
            ConnectionResult object.
        """
        if address in self._connected_devices:
            self.logger.info(f"Device {address} already connected")
            client = self._connected_devices[address]["client"]
            connected_at = self._connected_devices[address]["connected_at"]
            return ConnectionResult(
                success=True,
                address=address,
                connection_time=int(time.time() - connected_at),
                client=client
            )

        if self._mock_mode:
            self.logger.info(f"Mock connection to device {address}")
            mock_device = next((d for d in self._mock_devices if d["address"] == address), None)
            if mock_device:
                self._connected_devices[address] = {
                    "client": None,
                    "connected_at": time.time(),
                    "connection_params": connection_params
                }
                return ConnectionResult(success=True, address=address, connection_time=0)
            else:
                return ConnectionResult(success=False, address=address, error="Mock device not found")

        attempt = 0
        last_error = None

        while attempt < max_retries:
            try:
                self.logger.info(f"Connecting to device {address} (attempt {attempt + 1}/{max_retries})...")
                client = BleakClient(address)
                await client.connect()

                self.logger.info(f"Successfully connected to device {address}")
                self._connected_devices[address] = {
                    "client": client,
                    "connected_at": time.time(),
                    "connection_params": connection_params
                }

                return ConnectionResult(
                    success=True,
                    address=address,
                    connection_time=int(time.time() - self._connected_devices[address]["connected_at"]),
                    client=client
                )
            except BleakError as e:
                attempt += 1
                last_error = str(e)
                self.logger.warning(f"Connection attempt {attempt} failed for {address}: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                continue

        self.logger.error(f"Failed to connect to device {address} after {max_retries} attempts: {last_error}")
        raise BleConnectionError(f"Failed to connect after {max_retries} attempts: {last_error}")

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

    async def get_saved_devices(self) -> List[Dict]:
        """
        Return the list of bonded/saved devices (Not Implemented).
        
        Placeholder implementation. Requires platform-specific logic or persistence.

        Returns:
            An empty list (currently).
        """
        self.logger.warning("get_saved_devices is not yet implemented.")
        # TODO: Implement logic to retrieve bonded/paired devices from OS or persistence
        raise NotImplementedError("Bonded device retrieval is not implemented.")

    def _get_mock_devices(self) -> List[Dict]:
        """
        Return a list of mock devices for testing purposes.

        Returns:
            List of mock device dictionaries.
        """
        return [
            {
                "address": "00:11:22:33:44:55",
                "name": "Mock Device 1",
                "rssi": -75,
                "metadata": {}
            },
            {
                "address": "AA:BB:CC:DD:EE:FF",
                "name": "Mock Device 2",
                "rssi": -65,
                "metadata": {}
            }
        ]

    def set_mock_mode(self, enable: bool):
        """
        Enable or disable mock mode for testing.

        Args:
            enable: Boolean to enable or disable mock mode.
        """
        self._mock_mode = enable
        self.logger.info(f"Mock mode {'enabled' if enable else 'disabled'}")

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