# ble_manager.py
import asyncio
from bleak import BleakScanner, BleakClient
import logging
from typing import Callable, Optional, Dict, List
import platform
import sys

class BLEManager:
    def __init__(self, logger=None, platform_override=None):
        self.client = None
        self.device = None
        self.logger = logger or logging.getLogger(__name__)
        self.notification_callbacks = {}
        self.services_cache = {}
        self.platform = platform_override if platform_override else sys.platform

    async def scan_devices(self, scan_time=5) -> List:
        """Scans for Bluetooth devices and returns a list of discovered devices."""
        self.logger.info(f"Scanning for devices for {scan_time} seconds...")
        try:
            devices = await BleakScanner.discover(timeout=scan_time)
            for i, device in enumerate(devices):
                rssi = device.advertisement_data.rssi if hasattr(device, 'advertisement_data') else "Unknown"
                self.logger.info(f"{i}: {device.name or 'Unknown'} [{device.address}] RSSI: {rssi}")
            return devices
        except Exception as e:
            self.logger.error(f"Error during scanning: {e}")
            return []

    async def connect_device(self, address: str) -> bool:
        """Connects to a Bluetooth device with the given address."""
        self.logger.info(f"Connecting to device {address}...")
        try:
            self.client = BleakClient(address)
            await self.client.connect()
            self.logger.info(f"Connected to {address}")
            self.device = address
            self.services_cache = {}  # Clear service cache on new connection
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to {address}: {e}")
            self.client = None
            return False

    async def disconnect_device(self) -> bool:
        """Disconnects from the currently connected device."""
        if self.client and self.client.is_connected:
            try:
                # Stop all notifications before disconnecting
                for char_uuid in list(self.notification_callbacks.keys()):
                    await self.stop_notify(char_uuid)
                await self.client.disconnect()
                self.logger.info(f"Disconnected from {self.device}")
                self.client = None
                self.device = None
                self.notification_callbacks.clear()
                self.services_cache.clear()
                return True
            except Exception as e:
                self.logger.error(f"Error during disconnection: {e}")
                return False
        return False

    async def read_characteristic(self, char_uuid: str) -> Optional[bytes]:
        """Reads a characteristic from the connected device."""
        if not self.client or not self.client.is_connected:
            self.logger.warning("Not connected to any device.")
            return None
        try:
            value = await self.client.read_gatt_char(char_uuid)
            self.logger.info(f"Read value from {char_uuid}: {value}")
            return value
        except Exception as e:
            self.logger.error(f"Failed to read characteristic {char_uuid}: {e}")
            return None

    async def write_characteristic(self, char_uuid: str, data: bytes, response: bool = False) -> bool:
        """Writes a characteristic to the connected device."""
        if not self.client or not self.client.is_connected:
            self.logger.warning("Not connected to any device.")
            return False
        try:
            await self.client.write_gatt_char(char_uuid, data, response=response)
            self.logger.info(f"Wrote value to {char_uuid}: {data}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to write characteristic {char_uuid}: {e}")
            return False

    async def get_services(self) -> List[Dict]:
        """Retrieves services of the connected device from cache or device."""
        if not self.client or not self.client.is_connected:
            self.logger.warning("Not connected to any device.")
            return []

        if self.services_cache:
            return list(self.services_cache.values())

        try:
            services = []
            for service in self.client.services:
                service_data = {
                    "uuid": service.uuid,
                    "description": self._get_service_description(service.uuid)
                }
                services.append(service_data)
                self.services_cache[service.uuid] = service_data  # Cache service
            return services
        except Exception as e:
            self.logger.error(f"Failed to get services: {e}")
            raise Exception(f"Service discovery failed: {str(e)}")

    async def get_characteristics(self, service_uuid: str) -> List[Dict]:
        """Retrieves characteristics for a service from the connected device."""
        if not self.client or not self.client.is_connected:
            self.logger.warning("Not connected to any device.")
            return []

        try:
            service = self.client.services.get(service_uuid)
            if not service:
                self.logger.warning(f"Service with UUID {service_uuid} not found.")
                return []

            characteristics = []
            for char in service.characteristics:
                props = []
                if "read" in char.properties:
                    props.append("read")
                if "write" in char.properties:
                    props.append("write")
                if "notify" in char.properties:
                    props.append("notify")
                char_data = {
                    "uuid": char.uuid,
                    "properties": props,
                    "service_uuid": service_uuid,
                    "description": self._get_characteristic_description(char.uuid)
                }
                characteristics.append(char_data)
            return characteristics
        except Exception as e:
            self.logger.error(f"Failed to get characteristics: {e}")
            raise Exception(f"Characteristic discovery failed: {str(e)}")

    async def start_notify(self, char_uuid: str, callback: Callable[[str, bytes], None]) -> bool:
        """Start notifications for a characteristic."""
        if not self.client or not self.client.is_connected:
            self.logger.warning("Not connected to any device.")
            return False

        try:
            def callback_wrapper(sender, data):
                try:
                    asyncio.create_task(callback(char_uuid, data))
                except Exception as e:
                    self.logger.error(f"Error in notification callback: {e}")

            await self.client.start_notify(char_uuid, callback_wrapper)
            self.notification_callbacks[char_uuid] = callback_wrapper
            self.logger.info(f"Started notifications for {char_uuid}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start notifications for {char_uuid}: {e}")
            return False

    async def stop_notify(self, char_uuid: str) -> bool:
        """Stop notifications for a characteristic."""
        if not self.client or not self.client.is_connected:
            self.logger.warning("Not connected to any device.")
            return False

        try:
            await self.client.stop_notify(char_uuid)
            if char_uuid in self.notification_callbacks:
                del self.notification_callbacks[char_uuid]
            self.logger.info(f"Stopped notifications for {char_uuid}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to stop notifications for {char_uuid}: {e}")
            return False

    def _get_service_description(self, uuid: str) -> str:
        """Provides a description for known service UUIDs."""
        services = {
            "0000180a-0000-1000-8000-00805f9b34fb": "Device Information",
            "0000180f-0000-1000-8000-00805f9b34fb": "Battery Service",
            "0000180d-0000-1000-8000-00805f9b34fb": "Heart Rate Service",
        }
        return services.get(uuid.lower(), "Unknown Service")

    def _get_characteristic_description(self, uuid: str) -> str:
        """Provides a description for known characteristic UUIDs."""
        characteristics = {
            "00002a19-0000-1000-8000-00805f9b34fb": "Battery Level",
            "00002a29-0000-1000-8000-00805f9b34fb": "Manufacturer Name",
            "00002a37-0000-1000-8000-00805f9b34fb": "Heart Rate Measurement",
        }
        return characteristics.get(uuid.lower(), "Unknown Characteristic")