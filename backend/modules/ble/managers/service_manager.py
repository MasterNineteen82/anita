"""Bluetooth service and characteristic management."""

import logging
from typing import Dict, Any, List, Optional, Tuple, Union, Callable
import uuid

from bleak.backends.service import BleakGATTService, BleakGATTCharacteristic
from bleak.backends.descriptor import BleakGATTDescriptor
from bleak import BleakClient, BleakError

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
    
    async def get_services(self) -> List[Dict[str, Any]]:
        """
        Get all services from the connected device.
        
        Returns:
            List of service dictionaries
        """
        if not self.client:
            raise BleakError("No BLE client available")
        
        if not self.client.is_connected:
            raise BleakError("Device is not connected")
        
        try:
            # Get services
            services = []
            
            # Cache service UUIDs for faster lookups
            if not self._service_uuids:
                for service in self.client.services:
                    self._service_uuids[str(service.uuid).lower()] = service
                    self._gatt_services[str(service.uuid).lower()] = service
            
            # Format each service
            for uuid_str, service in self._gatt_services.items():
                service_info = {
                    "uuid": str(service.uuid).lower(),
                    "description": self._get_service_description(str(service.uuid)),
                    "handle": service.handle,
                    "characteristics": len(service.characteristics)
                }
                services.append(service_info)
            
            return sorted(services, key=lambda s: s["handle"])
        except Exception as e:
            self.logger.error(f"Error getting services: {e}")
            raise BleakError(f"Error getting services: {e}")
    
    async def get_service_info(self, service_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific service.
        
        Args:
            service_uuid: UUID of the service
            
        Returns:
            Service info dictionary or None if not found
        """
        if not self.client:
            raise BleakError("No BLE client available")
        
        if not self.client.is_connected:
            raise BleakError("Device is not connected")
        
        try:
            # Normalize UUID
            service_uuid = service_uuid.lower()
            
            # Get service
            service = self._get_service(service_uuid)
            
            if not service:
                return None
            
            # Format service info
            char_count = len(service.characteristics)
            characteristics = []
            
            for char in service.characteristics:
                char_info = {
                    "uuid": str(char.uuid).lower(),
                    "handle": char.handle,
                    "description": self._get_characteristic_description(str(char.uuid)),
                    "properties": [prop.name for prop in char.properties]
                }
                characteristics.append(char_info)
            
            return {
                "uuid": service_uuid,
                "handle": service.handle,
                "description": self._get_service_description(service_uuid),
                "characteristics": characteristics,
                "characteristic_count": char_count
            }
        except Exception as e:
            self.logger.error(f"Error getting service info: {e}")
            raise BleakError(f"Error getting service info: {e}")
    
    async def get_characteristics(self, service_uuid: str) -> List[Dict[str, Any]]:
        """
        Get all characteristics for a specific service.
        
        Args:
            service_uuid: UUID of the service
            
        Returns:
            List of characteristic dictionaries
        """
        if not self.client:
            raise BleakError("No BLE client available")
        
        if not self.client.is_connected:
            raise BleakError("Device is not connected")
        
        try:
            # Normalize UUID
            service_uuid = service_uuid.lower()
            
            # Get service
            service = self._get_service(service_uuid)
            
            if not service:
                raise BleakError(f"Service {service_uuid} not found")
            
            # Format characteristics
            characteristics = []
            
            for char in service.characteristics:
                properties = [prop.name for prop in char.properties]
                
                char_info = {
                    "uuid": str(char.uuid).lower(),
                    "handle": char.handle,
                    "description": self._get_characteristic_description(str(char.uuid)),
                    "properties": properties,
                    "readable": "read" in [p.lower() for p in properties],
                    "writable": any(p.lower() in ["write", "write-without-response"] for p in properties),
                    "notifiable": "notify" in [p.lower() for p in properties],
                    "indicatable": "indicate" in [p.lower() for p in properties]
                }
                characteristics.append(char_info)
            
            return sorted(characteristics, key=lambda c: c["handle"])
        except Exception as e:
            self.logger.error(f"Error getting characteristics: {e}")
            raise BleakError(f"Error getting characteristics: {e}")
    
    async def get_characteristic_info(self, service_uuid: str, char_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific characteristic.
        
        Args:
            service_uuid: UUID of the service
            char_uuid: UUID of the characteristic
            
        Returns:
            Characteristic info dictionary or None if not found
        """
        if not self.client:
            raise BleakError("No BLE client available")
        
        if not self.client.is_connected:
            raise BleakError("Device is not connected")
        
        try:
            # Normalize UUIDs
            service_uuid = service_uuid.lower()
            char_uuid = char_uuid.lower()
            
            # Get characteristic
            char = self._get_characteristic(service_uuid, char_uuid)
            
            if not char:
                return None
            
            # Get descriptors
            descriptors = []
            for desc in char.descriptors:
                descriptors.append({
                    "uuid": str(desc.uuid).lower(),
                    "handle": desc.handle
                })
            
            # Properties
            properties = [prop.name for prop in char.properties]
            
            # Format characteristic info
            return {
                "uuid": char_uuid,
                "handle": char.handle,
                "service_uuid": service_uuid,
                "description": self._get_characteristic_description(char_uuid),
                "properties": properties,
                "readable": "read" in [p.lower() for p in properties],
                "writable": any(p.lower() in ["write", "write-without-response"] for p in properties),
                "notifiable": "notify" in [p.lower() for p in properties],
                "indicatable": "indicate" in [p.lower() for p in properties],
                "descriptors": descriptors,
                "descriptor_count": len(descriptors)
            }
        except Exception as e:
            self.logger.error(f"Error getting characteristic info: {e}")
            raise BleakError(f"Error getting characteristic info: {e}")
    
    async def get_descriptors(self, service_uuid: str, char_uuid: str) -> List[Dict[str, Any]]:
        """
        Get all descriptors for a specific characteristic.
        
        Args:
            service_uuid: UUID of the service
            char_uuid: UUID of the characteristic
            
        Returns:
            List of descriptor dictionaries
        """
        if not self.client:
            raise BleakError("No BLE client available")
        
        if not self.client.is_connected:
            raise BleakError("Device is not connected")
        
        try:
            # Normalize UUIDs
            service_uuid = service_uuid.lower()
            char_uuid = char_uuid.lower()
            
            # Get characteristic
            char = self._get_characteristic(service_uuid, char_uuid)
            
            if not char:
                raise BleakError(f"Characteristic {char_uuid} not found in service {service_uuid}")
            
            # Format descriptors
            descriptors = []
            
            for desc in char.descriptors:
                desc_info = {
                    "uuid": str(desc.uuid).lower(),
                    "handle": desc.handle,
                    "description": self._get_descriptor_description(str(desc.uuid))
                }
                descriptors.append(desc_info)
            
            return sorted(descriptors, key=lambda d: d["handle"])
        except Exception as e:
            self.logger.error(f"Error getting descriptors: {e}")
            raise BleakError(f"Error getting descriptors: {e}")
    
    async def read_characteristic(self, char_uuid: str) -> Union[bytes, bytearray]:
        """
        Read a value from a characteristic.
        
        Args:
            char_uuid: UUID of the characteristic
            
        Returns:
            Bytes containing the characteristic value
        """
        if not self.client:
            raise BleakError("No BLE client available")
        
        if not self.client.is_connected:
            raise BleakError("Device is not connected")
        
        try:
            # Normalize UUID
            char_uuid = char_uuid.lower()
            
            # Read the value
            self.logger.info(f"Reading characteristic: {char_uuid}")
            value = await self.client.read_gatt_char(char_uuid)
            
            self.logger.debug(f"Read value: {value.hex() if isinstance(value, (bytes, bytearray)) else value}")
            return value
        except Exception as e:
            self.logger.error(f"Error reading characteristic: {e}")
            raise BleakError(f"Error reading characteristic: {e}")
    
    async def write_characteristic(self, char_uuid: str, data: Union[bytes, bytearray, str], with_response: bool = True) -> bool:
        """
        Write a value to a characteristic.
        
        Args:
            char_uuid: UUID of the characteristic
            data: Data to write (bytes or string)
            with_response: Whether to wait for a response
            
        Returns:
            True if successful
        """
        if not self.client:
            raise BleakError("No BLE client available")
        
        if not self.client.is_connected:
            raise BleakError("Device is not connected")
        
        try:
            # Normalize UUID
            char_uuid = char_uuid.lower()
            
            # Convert data to bytes if it's a string
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            # Write the value
            self.logger.info(f"Writing to characteristic: {char_uuid}, with response: {with_response}")
            self.logger.debug(f"Data: {data.hex() if isinstance(data, (bytes, bytearray)) else data}")
            
            await self.client.write_gatt_char(char_uuid, data, with_response)
            
            self.logger.info(f"Successfully wrote to characteristic: {char_uuid}")
            return True
        except Exception as e:
            self.logger.error(f"Error writing to characteristic: {e}")
            raise BleakError(f"Error writing to characteristic: {e}")
    
    async def start_notify(self, char_uuid: str, callback: Callable = None) -> bool:
        """
        Start notifications for a characteristic.
        
        Args:
            char_uuid: UUID of the characteristic
            callback: Function to call when notifications are received (sender, data)
            
        Returns:
            True if successful
        """
        if not self.client:
            raise BleakError("No BLE client available")
        
        if not self.client.is_connected:
            raise BleakError("Device is not connected")
        
        try:
            # Normalize UUID
            char_uuid = char_uuid.lower()
            
            # Check if already subscribed
            if char_uuid in self._active_notifications:
                self.logger.info(f"Already subscribed to {char_uuid}, updating callback")
                
                # If we have a new callback, update without re-subscribing
                if callback:
                    old_callback = self._active_notifications[char_uuid]
                    self._active_notifications[char_uuid] = callback
                    
                    # We're done if we're just updating the callback
                    return True
            
            # Start notifications
            self.logger.info(f"Starting notifications for characteristic: {char_uuid}")
            
            def notification_wrapper(sender: int, data: bytearray):
                """Wrapper to log notifications and call the user callback."""
                self.logger.debug(
                    f"Notification from {char_uuid}: {data.hex() if data else 'None'}"
                )
                
                # Call the user's callback if provided
                if callback:
                    callback(char_uuid, data)
            
            # Store the callback for future reference
            self._active_notifications[char_uuid] = callback
            
            # Start notifications with our wrapper
            await self.client.start_notify(char_uuid, notification_wrapper)
            
            self.logger.info(f"Successfully started notifications for: {char_uuid}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting notifications: {e}")
            raise BleakError(f"Error starting notifications: {e}")
    
    async def stop_notify(self, char_uuid: str) -> bool:
        """
        Stop notifications for a characteristic.
        
        Args:
            char_uuid: UUID of the characteristic
            
        Returns:
            True if successful
        """
        if not self.client:
            raise BleakError("No BLE client available")
        
        if not self.client.is_connected:
            raise BleakError("Device is not connected")
        
        try:
            # Normalize UUID
            char_uuid = char_uuid.lower()
            
            # Check if notifications were even started
            if char_uuid not in self._active_notifications:
                self.logger.warning(f"Not subscribed to notifications for {char_uuid}")
                return True  # Return success since we're not subscribed anyway
            
            self.logger.info(f"Stopping notifications for characteristic: {char_uuid}")
            
            # Stop notifications
            await self.client.stop_notify(char_uuid)
            
            # Remove the callback
            del self._active_notifications[char_uuid]
            
            self.logger.info(f"Successfully stopped notifications for: {char_uuid}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping notifications: {e}")
            raise BleakError(f"Error stopping notifications: {e}")
    
    def get_active_notifications(self) -> List[str]:
        """
        Get a list of characteristics with active notifications.
        
        Returns:
            List of characteristic UUIDs with active notifications
        """
        return list(self._active_notifications.keys())
    
    def has_active_notifications(self, char_uuid: str) -> bool:
        """
        Check if a characteristic has active notifications.
        
        Args:
            char_uuid: UUID of the characteristic
            
        Returns:
            True if notifications are active
        """
        return char_uuid.lower() in self._active_notifications
    
    def clear_notifications(self):
        """Clear all active notifications (without unsubscribing)."""
        self._active_notifications = {}
    
    def _get_service(self, service_uuid: str) -> Optional[BleakGATTService]:
        """
        Get a service by UUID.
        
        Args:
            service_uuid: UUID of the service
            
        Returns:
            Service object or None if not found
        """
        if not self.client or not self.client.services:
            return None
        
        # Try exact match first
        service_uuid = service_uuid.lower()
        
        # Check if service is already cached
        if service_uuid in self._gatt_services:
            return self._gatt_services[service_uuid]
        
        # Not in cache, search all services
        for service in self.client.services:
            if str(service.uuid).lower() == service_uuid:
                # Cache for future lookups
                self._gatt_services[service_uuid] = service
                return service
        
        return None
    
    def _get_characteristic(self, service_uuid: str, char_uuid: str) -> Optional[BleakGATTCharacteristic]:
        """
        Get a characteristic by UUID within a service.
        
        Args:
            service_uuid: UUID of the service
            char_uuid: UUID of the characteristic
            
        Returns:
            Characteristic object or None if not found
        """
        service = self._get_service(service_uuid)
        
        if not service:
            return None
        
        char_uuid = char_uuid.lower()
        
        for char in service.characteristics:
            if str(char.uuid).lower() == char_uuid:
                return char
        
        return None
    
    def _get_descriptor(self, service_uuid: str, char_uuid: str, desc_uuid: str) -> Optional[BleakGATTDescriptor]:
        """
        Get a descriptor by UUID within a characteristic.
        
        Args:
            service_uuid: UUID of the service
            char_uuid: UUID of the characteristic
            desc_uuid: UUID of the descriptor
            
        Returns:
            Descriptor object or None if not found
        """
        char = self._get_characteristic(service_uuid, char_uuid)
        
        if not char:
            return None
        
        desc_uuid = desc_uuid.lower()
        
        for desc in char.descriptors:
            if str(desc.uuid).lower() == desc_uuid:
                return desc
        
        return None
    
    def _get_service_description(self, service_uuid: str) -> str:
        """Get a human-readable description for a service UUID."""
        # Strip any prefix like '0000XXXX-0000-1000-8000-00805f9b34fb'
        short_uuid = self._get_short_uuid(service_uuid)
        
        # Look up in dictionary
        return self._service_descriptions.get(short_uuid.lower(), "Unknown Service")
    
    def _get_characteristic_description(self, char_uuid: str) -> str:
        """Get a human-readable description for a characteristic UUID."""
        # Strip any prefix
        short_uuid = self._get_short_uuid(char_uuid)
        
        # Look up in dictionary
        return self._char_descriptions.get(short_uuid.lower(), "Unknown Characteristic")
    
    def _get_descriptor_description(self, desc_uuid: str) -> str:
        """Get a human-readable description for a descriptor UUID."""
        # Common descriptors
        descriptors = {
            "2902": "Client Characteristic Configuration",
            "2901": "Characteristic User Description",
            "2903": "Server Characteristic Configuration",
            "2904": "Characteristic Presentation Format",
            "2905": "Characteristic Aggregate Format",
            "2906": "Valid Range",
            "2907": "External Report Reference",
            "2908": "Report Reference"
        }
        
        # Strip any prefix
        short_uuid = self._get_short_uuid(desc_uuid)
        
        # Look up in dictionary
        return descriptors.get(short_uuid.lower(), "Unknown Descriptor")
    
    def _get_short_uuid(self, uuid_str: str) -> str:
        """Extract the short form of a UUID if it's in the standard Bluetooth format."""
        uuid_str = uuid_str.lower()
        
        # Handle 16-bit UUID
        if len(uuid_str) <= 8:
            return uuid_str
        
        # Try to extract from standard format: 0000XXXX-0000-1000-8000-00805f9b34fb
        if "-" in uuid_str:
            parts = uuid_str.split("-")
            if len(parts) == 5 and parts[2] == "1000" and parts[3] == "8000" and parts[4] == "00805f9b34fb":
                return parts[0][4:8]
        
        # Return as-is if not standard format
        return uuid_str
    
    def _load_service_descriptions(self) -> Dict[str, str]:
        """Load standard Bluetooth service descriptions."""
        return {
            "1800": "Generic Access",
            "1801": "Generic Attribute",
            "1802": "Immediate Alert",
            "1803": "Link Loss",
            "1804": "Tx Power",
            "1805": "Current Time",
            "1806": "Reference Time Update",
            "1807": "Next DST Change",
            "1808": "Glucose",
            "1809": "Health Thermometer",
            "180a": "Device Information",
            "180d": "Heart Rate",
            "180e": "Phone Alert Status",
            "180f": "Battery",
            "1810": "Blood Pressure",
            "1811": "Alert Notification",
            "1812": "Human Interface Device",
            "1813": "Scan Parameters",
            "1814": "Running Speed and Cadence",
            "1815": "Automation IO",
            "1816": "Cycling Speed and Cadence",
            "1818": "Cycling Power",
            "1819": "Location and Navigation",
            "181a": "Environmental Sensing",
            "181b": "Body Composition",
            "181c": "User Data",
            "181d": "Weight Scale",
            "181e": "Bond Management",
            "181f": "Continuous Glucose Monitoring",
            "1820": "Internet Protocol Support",
            "1821": "Indoor Positioning",
            "1822": "Pulse Oximeter",
            "1823": "HTTP Proxy",
            "1824": "Transport Discovery",
            "1825": "Object Transfer",
            "1826": "Fitness Machine",
            "1827": "Mesh Provisioning",
            "1828": "Mesh Proxy",
            "1829": "Reconnection Configuration",
            "183a": "Insulin Delivery",
            "183b": "Binary Sensor",
            "183c": "Emergency Configuration",
            # Add more as needed
        }
    
    def _load_characteristic_descriptions(self) -> Dict[str, str]:
        """Load standard Bluetooth characteristic descriptions."""
        return {
            "2a00": "Device Name",
            "2a01": "Appearance",
            "2a02": "Peripheral Privacy Flag",
            "2a03": "Reconnection Address",
            "2a04": "Peripheral Preferred Connection Parameters",
            "2a05": "Service Changed",
            "2a06": "Alert Level",
            "2a07": "Tx Power Level",
            "2a08": "Date Time",
            "2a09": "Day of Week",
            "2a0a": "Day Date Time",
            "2a0b": "Exact Time 100",
            "2a0c": "Exact Time 256",
            "2a0d": "DST Offset",
            "2a0e": "Time Zone",
            "2a0f": "Local Time Information",
            "2a10": "Secondary Time Zone",
            "2a11": "Time with DST",
            "2a12": "Time Accuracy",
            "2a13": "Time Source",
            "2a14": "Reference Time Information",
            "2a15": "Time Update Control Point",
            "2a16": "Time Update State",
            "2a17": "Glucose Measurement",
            "2a18": "Battery Level",
            "2a19": "Battery Power State",
            "2a1c": "Temperature Measurement",
            "2a1d": "Temperature Type",
            "2a1e": "Intermediate Temperature",
            "2a1f": "Measurement Interval",
            "2a20": "Boot Keyboard Input Report",
            "2a21": "System ID",
            "2a22": "Model Number String",
            "2a23": "Serial Number String",
            "2a24": "Firmware Revision String",
            "2a25": "Hardware Revision String",
            "2a26": "Software Revision String",
            "2a27": "Manufacturer Name String",
            "2a28": "IEEE 11073-20601 Regulatory Cert. Data List",
            "2a29": "PnP ID",
            "2a2a": "Peripheral Preferred Connection Parameters",
            "2a2b": "Current Time",
            "2a2c": "Magnetic Declination",
            "2a31": "Scan Refresh",
            "2a32": "Boot Keyboard Output Report",
            "2a33": "Boot Mouse Input Report",
            "2a34": "Glucose Measurement Context",
            "2a35": "Blood Pressure Measurement",
            "2a36": "Intermediate Cuff Pressure",
            "2a37": "Heart Rate Measurement",
            "2a38": "Body Sensor Location",
            "2a39": "Heart Rate Control Point",
            "2a3f": "Alert Status",
            "2a40": "Ringer Control Point",
            "2a41": "Ringer Setting",
            "2a42": "Alert Category ID Bit Mask",
            "2a43": "Alert Category ID",
            "2a44": "Alert Notification Control Point",
            "2a45": "Unread Alert Status",
            "2a46": "New Alert",
            "2a47": "Supported New Alert Category",
            "2a48": "Supported Unread Alert Category",
            "2a49": "Blood Pressure Feature",
            "2a4a": "HID Information",
            "2a4b": "Report Map",
            "2a4c": "HID Control Point",
            "2a4d": "Report",
            "2a4e": "Protocol Mode",
            "2a4f": "Scan Interval Window",
            "2a50": "PnP ID",
            "2a51": "Glucose Feature",
            "2a52": "Record Access Control Point",
            "2a53": "RSC Measurement",
            "2a54": "RSC Feature",
            "2a55": "SC Control Point",
            "2a56": "Digital Input",
            "2a57": "Digital Output",
            "2a58": "Analog Input",
            "2a59": "Analog Output",
            "2a5a": "Aggregate Input",
            "2a5b": "CSC Measurement",
            "2a5c": "CSC Feature",
            "2a5d": "Sensor Location",
            # Add more as needed
        }