"""Bluetooth service and characteristic management."""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Union, Callable
import uuid

from bleak.backends.service import BleakGATTService, BleakGATTCharacteristic
from bleak.backends.descriptor import BleakGATTDescriptor
from bleak import BleakClient, BleakError

from backend.modules.ble.models import (
    BleService, BleCharacteristic, BleDescriptor,
    CharacteristicValue, ServicesResult
)
from backend.modules.ble.utils.events import ble_event_bus
from .exceptions import BleServiceError, BleConnectionError

class BleServiceManager:
    """Manages BLE services, characteristics and descriptors."""
    
    def __init__(self, client=None, logger=None):
        """Initialize the service manager."""
        self.logger = logger or logging.getLogger(__name__)
        self.client = client
        self._gatt_services = {}
        self._service_uuids = {}
        self._char_descriptions = self._load_characteristic_descriptions()
        self._service_descriptions = self._load_service_descriptions()
        self._active_notifications = {}
    
    def set_client(self, client):
        """Set the BLE client to use for service operations."""
        self.client = client
        self._gatt_services = {}  # Reset cached services
    
    async def get_services(self, max_retries: int = 3, retry_delay: float = 1.0) -> List[Dict[str, Any]]:
        """
        Get all services from the connected device.
        
        Args:
            max_retries: Maximum number of retries for getting services.
            retry_delay: Delay between retries in seconds.
        
        Returns:
            List of service dictionaries
        """
        if not self.client:
            raise BleConnectionError("No BLE client available")
        
        if not self.client.is_connected:
            raise BleConnectionError("Device is not connected")
        
        attempt = 0
        last_error = None
        
        while attempt < max_retries:
            try:
                self.logger.info(f"Attempting to get services (attempt {attempt + 1}/{max_retries})...")
                # Get services
                services = []
                
                # Cache service UUIDs for faster lookups
                if not self._service_uuids:
                    for service in self.client.services:
                        short_uuid = self._get_short_uuid(service.uuid)
                        self._service_uuids[short_uuid] = service.uuid
                        self._service_uuids[service.uuid] = service.uuid
                        
                for service in self.client.services:
                    # Get service description
                    description = self._get_service_description(service.uuid)
                    
                    # Create service dictionary
                    service_dict = {
                        "uuid": service.uuid,
                        "description": description,
                        "characteristics": [],
                        "handle": getattr(service, "handle", None)
                    }
                    
                    # Add to results
                    services.append(service_dict)
                    
                    # Cache the service
                    self._gatt_services[service.uuid] = service
                    
                # Create pydantic model result
                result = ServicesResult(
                    services=services,
                    count=len(services)
                )
                
                self.logger.info(f"Successfully retrieved {len(services)} services")
                return services
            except BleConnectionError:
                raise
            except Exception as e:
                attempt += 1
                last_error = str(e)
                self.logger.warning(f"Attempt {attempt} failed to get services: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                continue
        
        self.logger.error(f"Failed to get services after {max_retries} attempts: {last_error}", exc_info=True)
        raise BleServiceError(f"Failed to get services after {max_retries} attempts: {last_error}")

    async def get_characteristics(self, service_uuid: str, max_retries: int = 3, retry_delay: float = 1.0) -> List[Dict[str, Any]]:
        """
        Get all characteristics for a service.
        
        Args:
            service_uuid: UUID of the service
            max_retries: Maximum number of retries for getting characteristics.
            retry_delay: Delay between retries in seconds.
        
        Returns:
            List of characteristic dictionaries
        """
        if not self.client:
            raise BleConnectionError("No BLE client available")
        
        if not self.client.is_connected:
            raise BleConnectionError("Device is not connected")
        
        # Resolve short UUID if provided
        service_uuid = self._service_uuids.get(service_uuid, service_uuid)
        
        attempt = 0
        last_error = None
        
        while attempt < max_retries:
            try:
                self.logger.info(f"Attempting to get characteristics for service {service_uuid} (attempt {attempt + 1}/{max_retries})...")
                # Get the service
                if service_uuid not in self._gatt_services:
                    # Try to find the service in client.services if not cached
                    found = False
                    for svc in self.client.services:
                        if svc.uuid == service_uuid:
                            self._gatt_services[service_uuid] = svc
                            found = True
                            break
                    if not found:
                        raise BleServiceError(f"Service {service_uuid} not found")
                
                service = self._gatt_services[service_uuid]
                
                # Get characteristics
                characteristics = []
                for char in service.characteristics:
                    # Get characteristic description
                    description = self._get_characteristic_description(char.uuid)
                    
                    # Get properties
                    properties = []
                    if char.properties:
                        properties = char.properties
                    
                    # Create characteristic dictionary
                    char_dict = {
                        "uuid": char.uuid,
                        "description": description,
                        "properties": properties,
                        "handle": getattr(char, "handle", None),
                        "descriptors": []
                    }
                    
                    # Add descriptors if available
                    if hasattr(char, "descriptors") and char.descriptors:
                        for desc in char.descriptors:
                            desc_dict = {
                                "uuid": desc.uuid,
                                "handle": getattr(desc, "handle", None)
                            }
                            char_dict["descriptors"].append(desc_dict)
                    
                    # Add to results
                    characteristics.append(char_dict)
                    
                self.logger.info(f"Successfully retrieved {len(characteristics)} characteristics for service {service_uuid}")
                return characteristics
            except BleConnectionError:
                raise
            except Exception as e:
                attempt += 1
                last_error = str(e)
                self.logger.warning(f"Attempt {attempt} failed to get characteristics for service {service_uuid}: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                continue
        
        self.logger.error(f"Failed to get characteristics for service {service_uuid} after {max_retries} attempts: {last_error}", exc_info=True)
        raise BleServiceError(f"Error getting characteristics: {last_error}")

    async def read_characteristic(self, characteristic_uuid: str) -> CharacteristicValue:
        """
        Read the value of a characteristic.
        
        Args:
            characteristic_uuid: UUID of the characteristic
            
        Returns:
            CharacteristicValue object with various representations
        """
        if not self.client:
            raise BleConnectionError("No BLE client available")
        
        if not self.client.is_connected:
            raise BleConnectionError("Device is not connected")
        
        try:
            # Read the characteristic
            start_time = asyncio.get_event_loop().time()
            value = await self.client.read_gatt_char(characteristic_uuid)
            end_time = asyncio.get_event_loop().time()
            
            # Emit metric event
            ble_event_bus.emit("operation_completed", {
                "operation": "read",
                "uuid": characteristic_uuid,
                "duration": end_time - start_time,
                "success": True
            })
            
            # Create value object
            char_value = CharacteristicValue(
                hex=value.hex() if value else "",
                text=self._try_decode_bytes(value),
                bytes=[b for b in value] if value else [],
                int=self._try_convert_to_int(value)
            )
            
            return char_value
        except BleConnectionError:
            raise
        except Exception as e:
            self.logger.error(f"Error reading characteristic: {e}", exc_info=True)
            # Emit failed metric
            ble_event_bus.emit("operation_completed", {
                "operation": "read",
                "uuid": characteristic_uuid,
                "success": False,
                "error": str(e)
            })
            raise BleServiceError(f"Error reading characteristic: {e}")

    async def write_characteristic(
        self, characteristic_uuid: str, value: Union[bytes, bytearray, str, int],
        value_type: str = "hex", byte_length: int = 4,
        response: bool = True
    ) -> bool:
        """
        Write a value to a characteristic.
        
        Args:
            characteristic_uuid: UUID of the characteristic
            value: Value to write
            value_type: Type of value (hex, text, bytes, int)
            byte_length: Length in bytes for integer values
            response: Whether to wait for response
            
        Returns:
            True if successful
        """
        if not self.client:
            raise BleConnectionError("No BLE client available")
        
        if not self.client.is_connected:
            raise BleConnectionError("Device is not connected")
        
        try:
            # Convert value to bytes
            bytes_value = self._convert_value_to_bytes(value, value_type, byte_length)
            
            if bytes_value is None:
                raise BleServiceError(f"Invalid value or value type: {value_type}")
            
            # Write the value
            start_time = asyncio.get_event_loop().time()
            await self.client.write_gatt_char(
                characteristic_uuid, bytes_value, response=response
            )
            end_time = asyncio.get_event_loop().time()
            
            # Emit metric event
            ble_event_bus.emit("operation_completed", {
                "operation": "write",
                "uuid": characteristic_uuid,
                "duration": end_time - start_time,
                "success": True
            })
            
            return True
        except BleConnectionError:
            raise
        except Exception as e:
            self.logger.error(f"Error writing characteristic: {e}", exc_info=True)
            # Emit failed metric
            ble_event_bus.emit("operation_completed", {
                "operation": "write",
                "uuid": characteristic_uuid,
                "success": False,
                "error": str(e)
            })
            raise BleServiceError(f"Error writing characteristic: {e}")

    async def start_notify(self, characteristic_uuid: str, callback: Callable) -> bool:
        """
        Start notifications for a characteristic.
        
        Args:
            characteristic_uuid: UUID of the characteristic
            callback: Callback function for notifications
            
        Returns:
            True if successful
        """
        if not self.client:
            raise BleConnectionError("No BLE client available")
        
        if not self.client.is_connected:
            raise BleConnectionError("Device is not connected")
        
        try:
            # Check if already notifying
            if characteristic_uuid in self._active_notifications:
                self.logger.debug(f"Already notifying on {characteristic_uuid}")
                return True
            
            # Start notifications
            await self.client.start_notify(characteristic_uuid, callback)
            
            # Track the active notification
            self._active_notifications[characteristic_uuid] = callback
            
            # Emit event
            ble_event_bus.emit("notification_started", {
                "uuid": characteristic_uuid
            })
            
            return True
        except BleConnectionError:
            raise
        except Exception as e:
            self.logger.error(f"Error starting notifications: {e}", exc_info=True)
            raise BleServiceError(f"Error starting notifications: {e}")

    async def stop_notify(self, characteristic_uuid: str) -> bool:
        """
        Stop notifications for a characteristic.
        
        Args:
            characteristic_uuid: UUID of the characteristic
            
        Returns:
            True if successful
        """
        if not self.client:
            raise BleConnectionError("No BLE client available")
        
        if not self.client.is_connected:
            raise BleConnectionError("Device is not connected")
        
        try:
            # Check if notifying
            if characteristic_uuid not in self._active_notifications:
                self.logger.debug(f"Not notifying on {characteristic_uuid}")
                return True
            
            # Stop notifications
            await self.client.stop_notify(characteristic_uuid)
            
            # Remove from active notifications
            del self._active_notifications[characteristic_uuid]
            
            # Emit event
            ble_event_bus.emit("notification_stopped", {
                "uuid": characteristic_uuid
            })
            
            return True
        except BleConnectionError:
            raise
        except Exception as e:
            self.logger.error(f"Error stopping notifications: {e}", exc_info=True)
            raise BleServiceError(f"Error stopping notifications: {e}")

    def get_active_notifications(self) -> List[str]:
        """
        Get a list of characteristic UUIDs with active notifications.
        
        Returns:
            List of characteristic UUIDs
        """
        return list(self._active_notifications.keys())

    async def clear_all_notifications(self) -> bool:
        """
        Stop all active notifications.
        
        Returns:
            True if successful
        """
        if not self.client or not self.client.is_connected:
            # If not connected, just clear the tracking dict
            self._active_notifications = {}
            return True
        
        try:
            # Get a copy of the keys since we'll be modifying the dict
            uuids = list(self._active_notifications.keys())
            
            # Stop each notification
            for uuid in uuids:
                try:
                    await self.client.stop_notify(uuid)
                except Exception as e:
                    self.logger.warning(f"Error stopping notification for {uuid}: {e}")
            
            # Clear the tracking dict
            self._active_notifications = {}
            
            return True
        except Exception as e:
            self.logger.error(f"Error clearing notifications: {e}", exc_info=True)
            return False

    # Helper methods
    async def _get_service(self, service_uuid: str) -> Optional[BleakGATTService]:
        """Get a service by UUID."""
        # Check cache first
        if service_uuid in self._gatt_services:
            return self._gatt_services[service_uuid]
        
        # Try to find the service
        for service in self.client.services:
            if service.uuid.lower() == service_uuid.lower():
                self._gatt_services[service_uuid] = service
                return service
                
            # Check if we need to convert from short UUID
            short_uuid = self._get_short_uuid(service.uuid)
            if short_uuid.lower() == service_uuid.lower():
                self._gatt_services[service_uuid] = service
                return service
        
        return None

    def _get_short_uuid(self, uuid_str: str) -> str:
        """Get the short version of a UUID (last 4 characters)."""
        if len(uuid_str) <= 4:
            return uuid_str
            
        return uuid_str.split('-')[-1][:4]

    def _get_service_description(self, uuid_str: str) -> str:
        """Get a human-readable description for a service UUID."""
        short_uuid = self._get_short_uuid(uuid_str)
        
        # Try the full UUID first
        if uuid_str in self._service_descriptions:
            return self._service_descriptions[uuid_str]
            
        # Try the short UUID
        if short_uuid in self._service_descriptions:
            return self._service_descriptions[short_uuid]
            
        return "Unknown Service"

    def _get_characteristic_description(self, uuid_str: str) -> str:
        """Get a human-readable description for a characteristic UUID."""
        short_uuid = self._get_short_uuid(uuid_str)
        
        # Try the full UUID first
        if uuid_str in self._char_descriptions:
            return self._char_descriptions[uuid_str]
            
        # Try the short UUID
        if short_uuid in self._char_descriptions:
            return self._char_descriptions[short_uuid]
            
        return "Unknown Characteristic"

    def _try_decode_bytes(self, value: bytes) -> str:
        """Try to decode bytes to UTF-8 string."""
        if not value:
            return ""
        try:
            return value.decode('utf-8')
        except UnicodeDecodeError:
            return "(binary data)"

    def _try_convert_to_int(self, value: bytes) -> Optional[int]:
        """Try to convert bytes to integer value."""
        if not value or len(value) not in [1, 2, 4, 8]:
            return None
            
        try:
            return int.from_bytes(value, byteorder='little', signed=False)
        except Exception:
            return None

    def _convert_value_to_bytes(
        self, value: Any, value_type: str, byte_length: int = 4
    ) -> Optional[bytes]:
        """Convert a value to bytes based on the specified type."""
        try:
            if value_type == "hex":
                # Convert hex string to bytes
                if isinstance(value, str):
                    if value.startswith("0x"):
                        value = value[2:]
                    return bytes.fromhex(value)
                return bytes(value)
            elif value_type == "text":
                # Convert text to bytes
                if isinstance(value, str):
                    return value.encode('utf-8')
                return bytes(value)
            elif value_type == "bytes":
                # Convert byte array to bytes
                return bytes(value)
            elif value_type == "int":
                # Convert integer to bytes
                return int(value).to_bytes(byte_length, byteorder='little')
            else:
                self.logger.warning(f"Unknown value type: {value_type}")
                return None
        except Exception as e:
            self.logger.error(f"Error converting value: {e}", exc_info=True)
            return None

    def _load_characteristic_descriptions(self) -> Dict[str, str]:
        """Load the characteristic descriptions."""
        # Standard Bluetooth characteristic UUIDs
        descriptions = {
            # Core characteristics
            "2A00": "Device Name",
            "2A01": "Appearance",
            "2A02": "Peripheral Privacy Flag",
            "2A03": "Reconnection Address",
            "2A04": "Peripheral Preferred Connection Parameters",
            "2A05": "Service Changed",
            
            # Common health characteristics
            "2A06": "Alert Level",
            "2A07": "Tx Power Level",
            "2A08": "Date Time",
            "2A09": "Day of Week",
            "2A0A": "Day Date Time",
            "2A0B": "Exact Time 256",
            
            # Battery characteristics
            "2A19": "Battery Level",
            
            # Health characteristics
            "2A1C": "Temperature Measurement",
            "2A1D": "Temperature Type",
            "2A1E": "Intermediate Temperature",
            
            # Heart rate characteristics
            "2A37": "Heart Rate Measurement",
            "2A38": "Body Sensor Location",
            "2A39": "Heart Rate Control Point",
            
            # More can be added as needed...
        }
        
        return descriptions

    def _load_service_descriptions(self) -> Dict[str, str]:
        """Load the service descriptions."""
        # Standard Bluetooth service UUIDs
        descriptions = {
            # Core services
            "1800": "Generic Access",
            "1801": "Generic Attribute",
            
            # Common health services
            "1802": "Immediate Alert",
            "1803": "Link Loss",
            "1804": "Tx Power",
            "1805": "Current Time",
            "1806": "Reference Time Update",
            "1807": "Next DST Change",
            "1808": "Glucose",
            "1809": "Health Thermometer",
            "180A": "Device Information",
            "180D": "Heart Rate",
            "180E": "Phone Alert Status",
            "180F": "Battery",
            
            # More can be added as needed...
        }
        
        return descriptions