# ble_manager.py
import asyncio
from bleak import BleakScanner, BleakClient
import logging
from typing import Callable, Optional, Dict

from typing import Optional, List, Dict, Any

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BleRepositoryInterface(ABC):
    """Interface for BLE device repositories."""
    
    @abstractmethod
    async def scan_devices(self, timeout: int = 10) -> List[Dict[str, Any]]:
        """Scan for available BLE devices."""
        pass
    
    @abstractmethod
    async def connect_device(self, device_id: str) -> bool:
        """Connect to a BLE device."""
        pass
    
    @abstractmethod
    async def disconnect_device(self, device_id: str) -> bool:
        """Disconnect from a BLE device."""
        pass

    @abstractmethod
    async def read_characteristic(self, device_id: str, char_uuid: str) -> Optional[bytes]:
        """Read a characteristic value from a specific device."""
        pass

    @abstractmethod
    async def write_characteristic(self, device_id: str, char_uuid: str, data: bytes) -> bool:
        """Write a value to a characteristic for a specific device."""
        pass

    @abstractmethod
    async def start_notify(self, device_id: str, char_uuid: str, callback: Callable[[str, bytes], None]) -> bool:
        """Start notifications for a characteristic on a specific device."""
        pass

    @abstractmethod
    async def stop_notify(self, device_id: str, char_uuid: str) -> bool:
        """Stop notifications for a characteristic on a specific device."""
        pass

    @abstractmethod
    async def get_services(self, device_id: str) -> List[Dict[str, Any]]:
        """Get available services for a connected device."""
        pass

    @abstractmethod
    async def get_characteristics(self, device_id: str, service_uuid: str) -> List[Dict[str, Any]]:
        """Get characteristics for a service on a specific device."""
        pass

class BleService:
    """Service for BLE operations using repository pattern."""
    
    def __init__(self, repository: BleRepositoryInterface, logger = None):
        """Initialize the BLE service with dependencies."""
        self.repository = repository
        self.logger = logger
    
    async def scan_devices(self, timeout: int = 10) -> List[Dict[str, Any]]:
        """Scan for available BLE devices."""
        if self.logger:
            self.logger.info(f"Scanning for BLE devices with timeout {timeout}s")
        
        return await self.repository.scan_devices(timeout)
    
    async def connect_device(self, device_id: str) -> bool:
        """Connect to a specific BLE device."""
        if self.logger:
            self.logger.info(f"Connecting to BLE device: {device_id}")
        
        return await self.repository.connect_device(device_id)
    
    async def disconnect_device(self, device_id: str) -> bool:
        """Disconnect from a BLE device."""
        if self.logger:
            self.logger.info(f"Disconnecting from BLE device: {device_id}")
        
        return await self.repository.disconnect_device(device_id)
    
    async def read_characteristic(self, device_id: str, char_uuid: str) -> Optional[bytes]:
        """Read a characteristic value."""
        if self.logger:
            self.logger.info(f"Reading characteristic: {char_uuid} from device: {device_id}")
        
        return await self.repository.read_characteristic(device_id, char_uuid)
    
    async def write_characteristic(self, device_id: str, char_uuid: str, data: bytes) -> bool:
        """Write a value to a characteristic."""
        if self.logger:
            self.logger.info(f"Writing to characteristic: {char_uuid} on device: {device_id}")
        
        return await self.repository.write_characteristic(device_id, char_uuid, data)

    async def start_notify(self, device_id: str, char_uuid: str, callback: Callable[[str, bytes], None]) -> bool:
        """Start notifications for a characteristic."""
        if self.logger:
            self.logger.info(f"Starting notifications for characteristic: {char_uuid} on device: {device_id}")
        
        return await self.repository.start_notify(device_id, char_uuid, callback)
    
    async def stop_notify(self, device_id: str, char_uuid: str) -> bool:
        """Stop notifications for a characteristic."""
        if self.logger:
            self.logger.info(f"Stopping notifications for characteristic: {char_uuid} on device: {device_id}")
        
        return await self.repository.stop_notify(device_id, char_uuid)

    async def get_services(self, device_id: str) -> List[Dict[str, Any]]:
        """Get available services for connected device."""
        if self.logger:
            self.logger.info(f"Getting available services for device: {device_id}")
        
        return await self.repository.get_services(device_id)

    async def get_characteristics(self, device_id: str, service_uuid: str) -> List[Dict[str, Any]]:
        """Get characteristics for a service."""
        if self.logger:
            self.logger.info(f"Getting characteristics for service: {service_uuid} on device: {device_id}")
        
        return await self.repository.get_characteristics(device_id, service_uuid)

class BLEManager(BleRepositoryInterface):
    def __init__(self, logger=None):
        self.client = None
        self.device = None
        self.logger = logger or logging.getLogger(__name__)
        self.notification_callbacks = {}
        self.services_cache = {}
        self.connected_devices: Dict[str, BleakClient] = {}  # Store connected devices

    async def scan_devices(self, scan_time=5):
        self.logger.info(f"Scanning for devices for {scan_time} seconds...")
        devices = await BleakScanner.discover(timeout=scan_time)
        device_list = []
        for i, device in enumerate(devices):
            # Use advertisement_data.rssi instead of device.rssi (deprecated)
            rssi = device.advertisement_data.rssi if hasattr(device, 'advertisement_data') else "Unknown"
            self.logger.info(f"{i}: {device.name or 'Unknown'} [{device.address}] RSSI: {rssi}")
            device_list.append({
                "name": device.name,
                "address": device.address,
                "rssi": rssi
            })
        return device_list

    async def connect_device(self, address):
        self.logger.info(f"Connecting to device {address}...")
        try:
            client = BleakClient(address)
            await client.connect()
            self.logger.info(f"Connected to {address}")
            self.connected_devices[address] = client  # Store the client
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to {address}: {e}")
            return False

    async def disconnect_device(self, address):
        if address in self.connected_devices:
            client = self.connected_devices[address]
            if client and client.is_connected:
                # Stop all notifications before disconnecting
                for char_uuid in list(self.notification_callbacks.keys()):
                    await self.stop_notify(address, char_uuid)
                await client.disconnect()
                self.logger.info(f"Disconnected from {address}")
                del self.connected_devices[address]
                # Remove notification callbacks associated with this device
                self.notification_callbacks = {
                    k: v for k, v in self.notification_callbacks.items() if not k.startswith(address)
                }
                return True
            else:
                self.logger.warning(f"Device {address} is not connected.")
                return False
        else:
            self.logger.warning(f"Device {address} not found in connected devices.")
            return False

    async def read_characteristic(self, device_id, char_uuid):
        if device_id not in self.connected_devices:
            self.logger.warning(f"Device {device_id} not connected.")
            return None
        client = self.connected_devices[device_id]
        try:
            value = await client.read_gatt_char(char_uuid)
            self.logger.info(f"Read value from {char_uuid} on {device_id}: {value}")
            return value
        except Exception as e:
            self.logger.error(f"Failed to read characteristic {char_uuid} on {device_id}: {e}")
            return None

    async def write_characteristic(self, device_id, char_uuid, data):
        if device_id not in self.connected_devices:
            self.logger.warning(f"Device {device_id} not connected.")
            return False
        client = self.connected_devices[device_id]
        try:
            await client.write_gatt_char(char_uuid, data)
            self.logger.info(f"Wrote value to {char_uuid} on {device_id}: {data}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to write characteristic {char_uuid} on {device_id}: {e}")
            return False

    async def get_services(self, device_id):
        if device_id not in self.connected_devices:
            self.logger.warning(f"Device {device_id} not connected.")
            return []
        client = self.connected_devices[device_id]
        try:
            services = []
            for service in client.services:
                services.append({
                    "uuid": service.uuid,
                    "description": self._get_service_description(service.uuid)
                })
            return services
        except Exception as e:
            self.logger.error(f"Failed to get services for {device_id}: {e}")
            return []

    async def get_characteristics(self, device_id, service_uuid):
        if device_id not in self.connected_devices:
            self.logger.warning(f"Device {device_id} not connected.")
            return []
        client = self.connected_devices[device_id]
        try:
            characteristics_list = []
            service = client.services.get_service(service_uuid)
            if service:
                for char in service.characteristics:
                    props = []
                    if "read" in char.properties:
                        props.append("read")
                    if "write" in char.properties:
                        props.append("write")
                    if "notify" in char.properties:
                        props.append("notify")
                    characteristics_list.append({
                        "uuid": char.uuid,
                        "properties": props,
                        "service_uuid": service_uuid,
                        "description": self._get_characteristic_description(char.uuid)
                    })
            return characteristics_list
        except Exception as e:
            self.logger.error(f"Failed to get characteristics for service {service_uuid} on {device_id}: {e}")
            return []

    async def start_notify(self, device_id: str, char_uuid: str, callback: Callable[[str, bytes], None]) -> bool:
        """Start notifications for a characteristic."""
        if device_id not in self.connected_devices:
            self.logger.warning(f"Device {device_id} not connected.")
            return False

        client = self.connected_devices[device_id]
        if not client or not client.is_connected:
            self.logger.warning("Not connected to any device.")
            return False
            
        try:
            async def callback_wrapper(sender, data):
                await callback(char_uuid, data)
                
            await client.start_notify(char_uuid, callback_wrapper)
            # Store the callback with a key that includes the device ID
            self.notification_callbacks[f"{device_id}:{char_uuid}"] = callback_wrapper
            self.logger.info(f"Started notifications for {char_uuid} on {device_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start notifications for {char_uuid} on {device_id}: {e}")
            return False
            
    async def stop_notify(self, device_id: str, char_uuid: str) -> bool:
        """Stop notifications for a characteristic."""
        # Use the device ID to find the correct client
        if device_id not in self.connected_devices:
            self.logger.warning(f"Device {device_id} not connected.")
            return False

        client = self.connected_devices[device_id]
        if not client or not client.is_connected:
            self.logger.warning("Not connected to any device.")
            return False
            
        try:
            await client.stop_notify(char_uuid)
            # Remove the callback using the device-specific key
            callback_key = f"{device_id}:{char_uuid}"
            if callback_key in self.notification_callbacks:
                del self.notification_callbacks[callback_key]
            self.logger.info(f"Stopped notifications for {char_uuid} on {device_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to stop notifications for {char_uuid} on {device_id}: {e}")
            return False

    def _get_service_description(self, uuid):
        services = {
            "0000180a-0000-1000-8000-00805f9b34fb": "Device Information",
            "0000180f-0000-1000-8000-00805f9b34fb": "Battery Service",
            "0000180d-0000-1000-8000-00805f9b34fb": "Heart Rate Service",
        }
        return services.get(uuid.lower(), "Unknown Service")

    def _get_characteristic_description(self, uuid):
        characteristics = {
            "00002a19-0000-1000-8000-00805f9b34fb": "Battery Level",
            "00002a29-0000-1000-8000-00805f9b34fb": "Manufacturer Name",
            "00002a37-0000-1000-8000-00805f9b34fb": "Heart Rate Measurement",
        }
        return characteristics.get(uuid.lower(), "Unknown Characteristic")