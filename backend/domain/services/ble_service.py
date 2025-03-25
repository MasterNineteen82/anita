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

class BleService:
    """Service for BLE operations using repository pattern."""
    
    def __init__(self, repository: Optional[BleRepositoryInterface] = None, logger = None):
        """Initialize the BLE service with dependencies."""
        self.repository = repository
        self.logger = logger
    
    async def scan_devices(self, timeout: int = 10) -> List[Dict[str, Any]]:
        """Scan for available BLE devices."""
        if self.logger:
            self.logger.info(f"Scanning for BLE devices with timeout {timeout}s")
        
        # Use repository if available
        if self.repository:
            return await self.repository.scan_devices(timeout)
        
        # Fallback to original implementation
        return []
    
    async def connect_device(self, device_id: str) -> bool:
        """Connect to a specific BLE device."""
        if self.logger:
            self.logger.info(f"Connecting to BLE device: {device_id}")
        
        if self.repository:
            return await self.repository.connect_device(device_id)
        
        return False
    
    async def disconnect_device(self, device_id: str) -> bool:
        """Disconnect from a BLE device."""
        if self.logger:
            self.logger.info(f"Disconnecting from BLE device: {device_id}")
        
        if self.repository:
            return await self.repository.disconnect_device(device_id)
        
        return False
    
    async def read_characteristic(self, char_uuid: str) -> Optional[bytes]:
        """Read a characteristic value."""
        if self.logger:
            self.logger.info(f"Reading characteristic: {char_uuid}")
        
        # TODO: Implement when repository adds this method
        return None
    
    async def write_characteristic(self, char_uuid: str, data: bytes) -> bool:
        """Write a value to a characteristic."""
        if self.logger:
            self.logger.info(f"Writing to characteristic: {char_uuid}")
        
        # TODO: Implement when repository adds this method
        return False

    async def start_notify(self, char_uuid: str, callback) -> bool:
        """Start notifications for a characteristic."""
        if self.logger:
            self.logger.info(f"Starting notifications for characteristic: {char_uuid}")
        
        # TODO: Implement with repository when available
        return False
    
    async def stop_notify(self, char_uuid: str) -> bool:
        """Stop notifications for a characteristic."""
        if self.logger:
            self.logger.info(f"Stopping notifications for characteristic: {char_uuid}")
        
        # TODO: Implement with repository when available
        return False

    async def get_services(self) -> List[Dict[str, Any]]:
        """Get available services for connected device."""
        if self.logger:
            self.logger.info("Getting available services")
        
        # TODO: Implement with repository when available
        return []

    async def get_characteristics(self, service_uuid: str) -> List[Dict[str, Any]]:
        """Get characteristics for a service."""
        if self.logger:
            self.logger.info(f"Getting characteristics for service: {service_uuid}")
        
        # TODO: Implement with repository when available
        return []

class BLEManager:
    async def __init__(self, logger=None):
        self.client = None
        self.device = None
        self.logger = logger or logging.getLogger(__name__)
        self.notification_callbacks = {}
        self.services_cache = {}
        
    async def scan_devices(self, scan_time=5):
        self.logger.info(f"Scanning for devices for {scan_time} seconds...")
        devices = await BleakScanner.discover(timeout=scan_time)
        for i, device in enumerate(devices):
            # Use advertisement_data.rssi instead of device.rssi (deprecated)
            rssi = device.advertisement_data.rssi if hasattr(device, 'advertisement_data') else "Unknown"
            self.logger.info(f"{i}: {device.name or 'Unknown'} [{device.address}] RSSI: {rssi}")
        return devices

    async def connect_device(self, address):
        self.logger.info(f"Connecting to device {address}...")
        self.client = BleakClient(address)
        try:
            await self.client.connect()
            self.logger.info(f"Connected to {address}")
            self.device = address
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to {address}: {e}")
            self.client = None
            return False

    async def disconnect_device(self):
        if self.client and self.client.is_connected:
            # Stop all notifications before disconnecting
            for char_uuid in list(self.notification_callbacks.keys()):
                await self.stop_notify(char_uuid)
            await self.client.disconnect()
            self.logger.info(f"Disconnected from {self.device}")
            self.client = None
            self.device = None
            self.notification_callbacks.clear()
            return True
        return False

    async def read_characteristic(self, char_uuid):
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

    async def write_characteristic(self, char_uuid, data):
        if not self.client or not self.client.is_connected:
            self.logger.warning("Not connected to any device.")
            return False
        try:
            await self.client.write_gatt_char(char_uuid, data)
            self.logger.info(f"Wrote value to {char_uuid}: {data}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to write characteristic {char_uuid}: {e}")
            return False

    async def get_services(self):
        if not self.client or not self.client.is_connected:
            self.logger.warning("Not connected to any device.")
            return []
        try:
            services = []
            for service in self.client.services:
                services.append({
                    "uuid": service.uuid,
                    "description": self._get_service_description(service.uuid)
                })
            return services
        except Exception as e:
            self.logger.error(f"Failed to get services: {e}")
            raise Exception(f"Service discovery failed: {str(e)}")

    async def get_characteristics(self, service_uuid):
        if not self.client or not self.client.is_connected:
            self.logger.warning("Not connected to any device.")
            return []
        try:
            for service in self.client.services:
                if service.uuid == service_uuid:
                    characteristics = []
                    for char in service.characteristics:
                        props = []
                        if "read" in char.properties:
                            props.append("read")
                        if "write" in char.properties:
                            props.append("write")
                        if "notify" in char.properties:
                            props.append("notify")
                        characteristics.append({
                            "uuid": char.uuid,
                            "properties": props,
                            "service_uuid": service_uuid,
                            "description": self._get_characteristic_description(char.uuid)
                        })
                    return characteristics
            return []
        except Exception as e:
            self.logger.error(f"Failed to get characteristics: {e}")
            raise Exception(f"Characteristic discovery failed: {str(e)}")

    async def start_notify(self, char_uuid: str, callback: Callable[[str, bytes], None]) -> bool:
        """Start notifications for a characteristic."""
        if not self.client or not self.client.is_connected:
            self.logger.warning("Not connected to any device.")
            return False
            
        try:
            async def callback_wrapper(sender, data):
                asyncio.create_task(callback(char_uuid, data))
                
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

    async def _get_service_description(self, uuid):
        services = {
            "0000180a-0000-1000-8000-00805f9b34fb": "Device Information",
            "0000180f-0000-1000-8000-00805f9b34fb": "Battery Service",
            "0000180d-0000-1000-8000-00805f9b34fb": "Heart Rate Service",
        }
        return services.get(uuid.lower(), "Unknown Service")

    async def _get_characteristic_description(self, uuid):
        characteristics = {
            "00002a19-0000-1000-8000-00805f9b34fb": "Battery Level",
            "00002a29-0000-1000-8000-00805f9b34fb": "Manufacturer Name",
            "00002a37-0000-1000-8000-00805f9b34fb": "Heart Rate Measurement",
        }
        return characteristics.get(uuid.lower(), "Unknown Characteristic")