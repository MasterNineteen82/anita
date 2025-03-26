import asyncio
import logging
import platform
import sys
from typing import List, Dict, Optional, Callable, Any, Set
from bleak import BleakScanner, BleakClient, BleakError
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
import struct

class BLEManager:
    """
    Cross-platform BLE communication manager using Bleak library.
    Provides unified interface for BLE operations across Windows, macOS, and Linux.
    """
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.client: Optional[BleakClient] = None
        self.device: Optional[BLEDevice] = None
        self.device_address: Optional[str] = None
        self.services_cache: Dict[str, Dict] = {}
        self.characteristics_cache: Dict[str, Dict] = {}
        self.notification_callbacks: Dict[str, Callable] = {}
        self.connected = False
        self.mtu = 23  # Default BLE MTU size
        
        # Track bonded devices
        self.bonded_devices: Set[str] = set()
        self._load_bonded_devices()
        
        self.logger.info(f"BLE Manager initialized using Bleak {platform.system()}")

    def _load_bonded_devices(self):
        """Load previously bonded devices from storage."""
        try:
            # Simple implementation using a file
            # In production, use a more robust storage solution
            import os
            if os.path.exists("bonded_devices.txt"):
                with open("bonded_devices.txt", "r") as f:
                    self.bonded_devices = set(line.strip() for line in f if line.strip())
                self.logger.info(f"Loaded {len(self.bonded_devices)} bonded devices")
        except Exception as e:
            self.logger.error(f"Failed to load bonded devices: {e}")

    def _save_bonded_devices(self):
        """Save bonded devices to storage."""
        try:
            with open("bonded_devices.txt", "w") as f:
                for device in self.bonded_devices:
                    f.write(f"{device}\n")
            self.logger.info(f"Saved {len(self.bonded_devices)} bonded devices")
        except Exception as e:
            self.logger.error(f"Failed to save bonded devices: {e}")

    async def scan_devices(self, scan_time: int = 5, active: bool = False) -> List[Dict]:
        """
        Scan for BLE devices using Bleak.
        
        Args:
            scan_time: Duration of scan in seconds
            active: Whether to use active scanning
            
        Returns:
            List of discovered devices with name, address, and RSSI
        """
        self.logger.info(f"Scanning for BLE devices (time: {scan_time}s, active: {active})")
        
        try:
            # Use Bleak's scanner with the specified parameters
            devices = await BleakScanner.discover(
                timeout=scan_time,
                return_adv=active,  # Return advertisement data if active
            )
            
            # Format the results for the API
            result = []
            for device in devices:
                device_info = {
                    "name": device.name if hasattr(device, "name") else "Unknown Device",
                    "address": device.address,
                    "rssi": device.rssi,
                    "bonded": device.address in self.bonded_devices
                }
                
                # Add additional data if active scanning was used
                if active and hasattr(device, 'advertisement_data') and device.advertisement_data:
                    if device.advertisement_data.manufacturer_data:
                        device_info["manufacturer_data"] = {
                            str(k): list(v) for k, v in device.advertisement_data.manufacturer_data.items()
                        }
                    if device.advertisement_data.service_data:
                        device_info["service_data"] = {
                            str(k): list(v) for k, v in device.advertisement_data.service_data.items()
                        }
                    if device.advertisement_data.service_uuids:
                        device_info["service_uuids"] = device.advertisement_data.service_uuids
                
                result.append(device_info)
            
            self.logger.info(f"Found {len(result)} devices")
            return result
        except BleakError as e:
            self.logger.error(f"Bleak scanning error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error scanning for devices: {e}", exc_info=True)
            raise BleakError(f"Scan error: {e}")

    async def connect_device(self, address: str, auto_reconnect: bool = True) -> bool:
        """
        Connect to a BLE device using its address.

        Args:
            address: Device MAC address or identifier
            auto_reconnect: Whether to automatically reconnect on disconnect

        Returns:
            True if connection successful, False otherwise
        """
        self.logger.info(f"Connecting to device: {address}")

        if self.client and self.client.is_connected:
            self.logger.warning(f"Already connected to {self.device_address}, disconnecting first")
            await self.disconnect_device()

        try:
            # Create a new BleakClient instance
            self.device_address = address

            # Set up disconnect callback for auto-reconnect
            disconnected_event = asyncio.Event()

            def disconnection_handler(client):
                self.logger.info(f"Device {address} disconnected")
                self.connected = False
                disconnected_event.set()

                # Auto-reconnect logic
                if auto_reconnect and not client.is_disconnecting:
                    self.logger.info("Scheduling auto-reconnect...")
                    asyncio.create_task(self._attempt_reconnect(address))

            # Create and connect the client
            self.client = BleakClient(address, disconnected_callback=disconnection_handler)
            await self.client.connect()
            self.connected = True

            # After successful connection, negotiate MTU
            await self._negotiate_mtu()

            # Get services and cache them
            await self._cache_services()

            # If we successfully connected, add to bonded devices
            self.bonded_devices.add(address)
            self._save_bonded_devices()

            self.logger.info(f"Successfully connected to {address}")
            return True

        except BleakError as e:
            self.logger.error(f"Bleak connection error: {e}")
            self.connected = False
            self.client = None
            raise  # Re-raise the BleakError
        except Exception as e:
            self.logger.error(f"Error connecting to device: {e}", exc_info=True)
            self.connected = False
            self.client = None
            raise BleakError(f"Connection error: {e}")  # Wrap and raise as BleakError

    async def _attempt_reconnect(self, address: str, max_attempts: int = 5):
        """Attempt to reconnect to a device with exponential backoff."""
        for attempt in range(1, max_attempts + 1):
            self.logger.info(f"Reconnection attempt {attempt}/{max_attempts} to {address}")
            
            # Exponential backoff
            await asyncio.sleep(min(30, 2 ** attempt))
            
            try:
                success = await self.connect_device(address)
                if success:
                    self.logger.info(f"Reconnection successful on attempt {attempt}")
                    return True
            except Exception as e:
                self.logger.error(f"Reconnection attempt {attempt} failed: {e}")
                
        self.logger.warning(f"Failed to reconnect after {max_attempts} attempts")
        return False

    async def _negotiate_mtu(self):
        """Negotiate the Maximum Transmission Unit (MTU) size."""
        if not self.client or not self.client.is_connected:
            return
            
        try:
            # MTU negotiation is platform-specific
            if platform.system() == "Linux":
                # Linux supports MTU negotiation directly
                self.mtu = await self.client.exchange_mtu(512)
                self.logger.info(f"MTU negotiated on Linux: {self.mtu}")
            elif platform.system() == "Windows":
                # Windows has a different method
                if hasattr(self.client._backend, "request_mtu"):
                    self.mtu = await self.client._backend.request_mtu(512)
                    self.logger.info(f"MTU negotiated on Windows: {self.mtu}")
                else:
                    self.logger.warning("MTU negotiation not supported on this Windows configuration")
            elif platform.system() == "Darwin":
                # macOS doesn't support explicit MTU negotiation
                self.logger.info("MTU negotiation not explicitly supported on macOS")
                self.mtu = 185  # Default for macOS
                
            # Get the negotiated MTU if available
            if hasattr(self.client, 'mtu_size'):
                self.mtu = self.client.mtu_size
                self.logger.info(f"Retrieved negotiated MTU: {self.mtu}")
            
        except Exception as e:
            self.logger.warning(f"MTU negotiation failed: {e}")

    async def _cache_services(self):
        """Discover and cache services and characteristics."""
        if not self.client or not self.client.is_connected:
            return
            
        try:
            # Clear existing cache
            self.services_cache = {}
            self.characteristics_cache = {}
            
            # Discover services
            services = {}
            for service in self.client.services:
                service_uuid = str(service.uuid).lower()
                services[service_uuid] = {
                    "description": self._get_service_description(service_uuid),
                    "characteristics": []
                }
                
                # Process characteristics for this service
                for char in service.characteristics:
                    char_uuid = str(char.uuid).lower()
                    char_info = {
                        "uuid": char_uuid,
                        "description": self._get_characteristic_description(char_uuid),
                        "properties": [p.name for p in char.properties],
                        "service_uuid": service_uuid
                    }
                    services[service_uuid]["characteristics"].append(char_info)
                    
                    # Also add to flat characteristics cache for quick lookups
                    self.characteristics_cache[char_uuid] = char_info
            
            self.services_cache = services
            self.logger.info(f"Cached {len(services)} services and {len(self.characteristics_cache)} characteristics")
            
        except Exception as e:
            self.logger.error(f"Service discovery failed: {e}")

    async def disconnect_device(self) -> bool:
        """
        Disconnect from the connected BLE device.
        
        Returns:
            True if disconnected successfully, False otherwise
        """
        if not self.client:
            self.logger.warning("No device connected")
            return False
            
        try:
            # Stop all active notifications
            for char_uuid in list(self.notification_callbacks.keys()):
                await self.stop_notify(char_uuid)
                
            # Disconnect the client
            await self.client.disconnect()
            self.client = None
            self.device_address = None
            self.connected = False
            
            self.logger.info("Disconnected successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error disconnecting: {e}", exc_info=True)
            return False

    async def get_services(self) -> List[Dict]:
        """
        Get services from the connected device.
        
        Returns:
            List of services with their UUIDs and descriptions
        """
        if not self.client or not self.client.is_connected:
            self.logger.warning("No device connected")
            return []
            
        try:
            # If we have cached services, return those
            if self.services_cache:
                return [
                    {"uuid": uuid, "description": info["description"]}
                    for uuid, info in self.services_cache.items()
                ]
                
            # Otherwise, discover services
            await self._cache_services()
            return [
                {"uuid": uuid, "description": info["description"]}
                for uuid, info in self.services_cache.items()
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting services: {e}", exc_info=True)
            return []

    async def get_characteristics(self, service_uuid: str) -> List[Dict]:
        """
        Get characteristics for a specific service.
        
        Args:
            service_uuid: The UUID of the service
            
        Returns:
            List of characteristics with their UUIDs, properties, and descriptions
        """
        if not self.client or not self.client.is_connected:
            self.logger.warning("No device connected")
            return []
            
        try:
            # If we have cached services, return those
            if service_uuid in self.services_cache:
                return self.services_cache[service_uuid]["characteristics"]
                
            # Otherwise, discover services
            await self._cache_services()
            if service_uuid in self.services_cache:
                return self.services_cache[service_uuid]["characteristics"]
            else:
                self.logger.warning(f"Service {service_uuid} not found")
                return []
                
        except Exception as e:
            self.logger.error(f"Error getting characteristics: {e}", exc_info=True)
            return []

    async def read_characteristic(self, characteristic_uuid: str, service_uuid: Optional[str] = None) -> Dict:
        """
        Read value from a characteristic.
        
        Args:
            characteristic_uuid: The UUID of the characteristic
            service_uuid: Optional service UUID to verify the characteristic
            
        Returns:
            Dictionary with the value and its hex representation
        """
        if not self.client or not self.client.is_connected:
            self.logger.warning("No device connected")
            raise ValueError("No device connected")
            
        try:
            # Verify service if provided
            if service_uuid and self.services_cache:
                if service_uuid not in self.services_cache:
                    raise ValueError(f"Service {service_uuid} not found")
                    
                found = False
                for char in self.services_cache[service_uuid]["characteristics"]:
                    if char["uuid"] == characteristic_uuid:
                        found = True
                        break
                        
                if not found:
                    raise ValueError(f"Characteristic {characteristic_uuid} not found in service {service_uuid}")
            
            # Read the characteristic
            value = await self.client.read_gatt_char(characteristic_uuid)
            
            # Try to decode the value based on common formats
            decoded_value = self._decode_characteristic_value(characteristic_uuid, value)
            
            return {
                "uuid": characteristic_uuid,
                "value": value.hex(),
                "decoded": decoded_value
            }
            
        except BleakError as e:
            self.logger.error(f"Bleak read error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error reading characteristic: {e}", exc_info=True)
            raise

    async def write_characteristic(self, characteristic_uuid: str, value: bytes,
                                   service_uuid: Optional[str] = None, with_response: bool = True) -> bool:
        """
        Write value to a characteristic.
        
        Args:
            characteristic_uuid: The UUID of the characteristic
            value: The bytes to write
            service_uuid: Optional service UUID to verify the characteristic
            with_response: Whether to require a response
            
        Returns:
            True if write successful, False otherwise
        """
        if not self.client or not self.client.is_connected:
            self.logger.warning("No device connected")
            raise ValueError("No device connected")
            
        try:
            # Verify service if provided
            if service_uuid and self.services_cache:
                if service_uuid not in self.services_cache:
                    raise ValueError(f"Service {service_uuid} not found")
                    
                found = False
                for char in self.services_cache[service_uuid]["characteristics"]:
                    if char["uuid"] == characteristic_uuid:
                        found = True
                        break
                        
                if not found:
                    raise ValueError(f"Characteristic {characteristic_uuid} not found in service {service_uuid}")
            
            # Write the characteristic
            await self.client.write_gatt_char(characteristic_uuid, value, response=with_response)
            return True
            
        except BleakError as e:
            self.logger.error(f"Bleak write error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error writing characteristic: {e}", exc_info=True)
            raise

    async def start_notify(self, characteristic_uuid: str, callback: Callable) -> bool:
        """
        Subscribe to notifications for a characteristic.
        
        Args:
            characteristic_uuid: The UUID of the characteristic
            callback: Callback function to handle notifications
            
        Returns:
            True if subscription successful, False otherwise
        """
        if not self.client or not self.client.is_connected:
            self.logger.warning("No device connected")
            return False
            
        try:
            # Define the notification callback
            def notification_handler(sender: BleakGATTCharacteristic, data: bytearray):
                # Call the user's callback
                callback(characteristic_uuid, data)
            
            # Start notifications
            await self.client.start_notify(characteristic_uuid, notification_handler)
            
            # Store the callback for reconnection
            self.notification_callbacks[characteristic_uuid] = callback
            
            self.logger.info(f"Started notifications for {characteristic_uuid}")
            return True
            
        except BleakError as e:
            self.logger.error(f"Bleak notification error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error starting notifications: {e}", exc_info=True)
            return False

    async def stop_notify(self, characteristic_uuid: str) -> bool:
        """
        Unsubscribe from notifications for a characteristic.
        
        Args:
            characteristic_uuid: The UUID of the characteristic
            
        Returns:
            True if unsubscription successful, False otherwise
        """
        if not self.client or not self.client.is_connected:
            self.logger.warning("No device connected")
            return False
            
        try:
            # Stop notifications
            await self.client.stop_notify(characteristic_uuid)
            
            # Remove the callback
            if characteristic_uuid in self.notification_callbacks:
                del self.notification_callbacks[characteristic_uuid]
            
            self.logger.info(f"Stopped notifications for {characteristic_uuid}")
            return True
            
        except BleakError as e:
            self.logger.error(f"Bleak notification error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error stopping notifications: {e}", exc_info=True)
            return False

    def get_service_for_characteristic(self, characteristic_uuid: str) -> Optional[str]:
        """Get the service UUID for a characteristic."""
        if characteristic_uuid in self.characteristics_cache:
            return self.characteristics_cache[characteristic_uuid]["service_uuid"]
        return None

    def _decode_characteristic_value(self, uuid: str, value: bytes) -> Any:
        """Decode characteristic value based on UUID."""
        # Standard characteristic UUIDs
        if uuid.lower() == "00002a19-0000-1000-8000-00805f9b34fb":  # Battery Level
            return f"{value[0]}%" if value else "Unknown"
            
        elif uuid.lower() == "00002a29-0000-1000-8000-00805f9b34fb":  # Manufacturer Name
            return value.decode('utf-8').strip('\x00') if value else "Unknown"
            
        elif uuid.lower() == "00002a24-0000-1000-8000-00805f9b34fb":  # Model Number
            return value.decode('utf-8').strip('\x00') if value else "Unknown"
            
        elif uuid.lower() == "00002a25-0000-1000-8000-00805f9b34fb":  # Serial Number
            return value.decode('utf-8').strip('\x00') if value else "Unknown"
            
        elif uuid.lower() == "00002a27-0000-1000-8000-00805f9b34fb":  # Hardware Revision
            return value.decode('utf-8').strip('\x00') if value else "Unknown"
            
        elif uuid.lower() == "00002a26-0000-1000-8000-00805f9b34fb":  # Firmware Revision
            return value.decode('utf-8').strip('\x00') if value else "Unknown"
            
        elif uuid.lower() == "00002a28-0000-1000-8000-00805f9b34fb":  # Software Revision
            return value.decode('utf-8').strip('\x00') if value else "Unknown"
        
        # For other characteristics, try common formats
        try:
            # Try UTF-8 string
            text = value.decode('utf-8').strip('\x00')
            if text and text.isprintable():
                return text
        except UnicodeDecodeError:
            pass
            
        try:
            # Try as 16-bit integer
            if len(value) == 2:
                return struct.unpack("<h", value)[0]
        except struct.error:
            pass
            
        try:
            # Try as 32-bit integer
            if len(value) == 4:
                return struct.unpack("<i", value)[0]
        except struct.error:
            pass
            
        # Default to hex string
        return value.hex()

    def _get_service_description(self, uuid: str) -> str:
        """Get human-readable description for a service UUID."""
        uuid = uuid.lower()
        
        services = {
            "00001800-0000-1000-8000-00805f9b34fb": "Generic Access",
            "00001801-0000-1000-8000-00805f9b34fb": "Generic Attribute",
            "0000180a-0000-1000-8000-00805f9b34fb": "Device Information",
            "0000180f-0000-1000-8000-00805f9b34fb": "Battery Service",
            "00001812-0000-1000-8000-00805f9b34fb": "HID Service",
            "00001813-0000-1000-8000-00805f9b34fb": "Scan Parameters",
            "00001819-0000-1000-8000-00805f9b34fb": "Location and Navigation",
        }
        
        # Try direct match
        if uuid in services:
            return services[uuid]
            
        # Try extracting the 16-bit UUID
        if "-" in uuid:
            short_uuid = uuid.split("-")[0].lstrip("0")
            for full_uuid, description in services.items():
                if full_uuid.startswith(short_uuid):
                    return description
        
        return "Unknown Service"

    def _get_characteristic_description(self, uuid: str) -> str:
        """Get human-readable description for a characteristic UUID."""
        uuid = uuid.lower()
        
        characteristics = {
            "00002a00-0000-1000-8000-00805f9b34fb": "Device Name",
            "00002a01-0000-1000-8000-00805f9b34fb": "Appearance",
            "00002a19-0000-1000-8000-00805f9b34fb": "Battery Level",
            "00002a29-0000-1000-8000-00805f9b34fb": "Manufacturer Name",
            "00002a24-0000-1000-8000-00805f9b34fb": "Model Number",
            "00002a25-0000-1000-8000-00805f9b34fb": "Serial Number",
            "00002a27-0000-1000-8000-00805f9b34fb": "Hardware Revision",
            "00002a26-0000-1000-8000-00805f9b34fb": "Firmware Revision",
            "00002a28-0000-1000-8000-00805f9b34fb": "Software Revision",
        }
        
        # Try direct match
        if uuid in characteristics:
            return characteristics[uuid]
            
        # Try extracting the 16-bit UUID
        if "-" in uuid:
            short_uuid = uuid.split("-")[0].lstrip("0")
            for full_uuid, description in characteristics.items():
                if full_uuid.startswith(short_uuid):
                    return description
        
        return "Unknown Characteristic"

    async def negotiate_mtu(self, mtu_size: int = 517) -> int:
        """
        Negotiate MTU size with connected device.
        
        Args:
            mtu_size: Desired MTU size (max 517 for most devices)
            
        Returns:
            int: Negotiated MTU size
        """
        if not self.client or not self.client.is_connected:
            self.logger.warning("No device connected, cannot negotiate MTU")
            raise BleakError("Not connected to device")
        
        try:
            # Bleak handles MTU negotiation differently based on platform
            if self.platform_type == "windows":
                # Windows uses requestMtu method
                negotiated_mtu = await self.client._backend.request_mtu(mtu_size)
            elif self.platform_type == "macos":
                # macOS doesn't support MTU negotiation explicitly
                negotiated_mtu = 185  # Default for macOS
                self.logger.info("MTU negotiation not supported on macOS, using default value")
            else:  # Linux/Android
                negotiated_mtu = await self.client.exchange_mtu(mtu_size)
                
            self.logger.info(f"MTU negotiated: {negotiated_mtu}")
            return negotiated_mtu
        except Exception as e:
            self.logger.error(f"Error negotiating MTU: {e}", exc_info=True)
            raise BleakError(f"MTU negotiation failed: {str(e)}")

    async def set_connection_parameters(
        self, 
        min_interval: float = 7.5,  # ms
        max_interval: float = 30.0,  # ms
        latency: int = 0,
        timeout: int = 500  # ms
    ) -> bool:
        """
        Set connection parameters for an active connection.
        
        Args:
            min_interval: Minimum connection interval in milliseconds (min: 7.5ms)
            max_interval: Maximum connection interval in milliseconds
            latency: Slave latency (number of connection events)
            timeout: Supervision timeout in milliseconds
            
        Returns:
            bool: Whether parameters were set successfully
        """
        if not self.client or not self.client.is_connected:
            self.logger.warning("No device connected, cannot set connection parameters")
            raise BleakError("Not connected to device")
        
        try:
            # Convert ms to BLE intervals (1.25ms units)
            min_interval_units = max(6, int(min_interval / 1.25))  # Minimum is 6 (7.5ms)
            max_interval_units = max(min_interval_units, int(max_interval / 1.25))
            
            # Implementation depends on platform
            if self.platform_type == "windows":
                # Windows BluetoothLE API supports connection parameters
                success = await self.client._backend.set_connection_parameters(
                    min_interval_units, max_interval_units, latency, timeout
                )
            elif self.platform_type in ["linux", "android"]:
                # Linux/Android implementation
                success = await self.client.set_connection_parameters(
                    min_interval_units, max_interval_units, latency, timeout
                )
            else:
                # macOS doesn't support this directly
                self.logger.warning(f"Connection parameter setting not supported on {self.platform_type}")
                return False
                
            self.logger.info(f"Connection parameters set: min={min_interval}ms, max={max_interval}ms, latency={latency}, timeout={timeout}ms")
            return success
        except Exception as e:
            self.logger.error(f"Error setting connection parameters: {e}", exc_info=True)
            raise BleakError(f"Connection parameter setting failed: {str(e)}")

    async def get_connection_parameters(self) -> Dict[str, Any]:
        """
        Get current connection parameters.
        
        Returns:
            Dict: Connection parameters
        """
        if not self.client or not self.client.is_connected:
            self.logger.warning("No device connected, cannot get connection parameters")
            raise BleakError("Not connected to device")
        
        try:
            # Implementation depends on platform
            if self.platform_type == "windows":
                # Windows BluetoothLE API
                params = await self.client._backend.get_connection_parameters()
            elif self.platform_type in ["linux", "android"]:
                # Linux/Android implementation
                params = await self.client.get_connection_parameters()
            else:
                # macOS doesn't support this
                self.logger.warning(f"Getting connection parameters not supported on {self.platform_type}")
                return {
                    "min_interval": None,
                    "max_interval": None,
                    "latency": None,
                    "timeout": None
                }
            
            # Convert BLE intervals (1.25ms units) to milliseconds
            return {
                "min_interval": params.get("min_interval", 0) * 1.25,
                "max_interval": params.get("max_interval", 0) * 1.25,
                "latency": params.get("latency", 0),
                "timeout": params.get("timeout", 0)
            }
        except Exception as e:
            self.logger.error(f"Error getting connection parameters: {e}", exc_info=True)
            raise BleakError(f"Getting connection parameters failed: {str(e)}")

    async def scan_with_filters(
        self, 
        service_uuids: List[str] = None,
        name_filter: str = None,
        address_filter: str = None,
        scan_time: int = 5,
        active: bool = False
    ) -> List[Dict]:
        """
        Scan for BLE devices with filters.
        
        Args:
            service_uuids: List of service UUIDs to filter devices by
            name_filter: Name substring to filter devices by
            address_filter: MAC address or part of it to filter by
            scan_time: Duration in seconds to scan
            active: Whether to use active scanning
            
        Returns:
            List[Dict]: List of discovered devices matching the filters
        """
        try:
            # Create scanner with service UUID filter if provided
            kwargs = {}
            if service_uuids:
                kwargs["service_uuids"] = service_uuids
            
            # Use Bleak's scanner
            devices = await BleakScanner.discover(timeout=scan_time, return_adv=active, **kwargs)
            
            # Apply additional client-side filters
            filtered_devices = []
            for device in devices:
                # Apply name filter if provided
                if name_filter and (not device.name or name_filter.lower() not in device.name.lower()):
                    continue
                    
                # Apply address filter if provided
                if address_filter and address_filter.lower() not in device.address.lower():
                    continue
                    
                # Device passed all filters, convert to standard format
                device_info = {
                    "name": device.name or "Unknown Device",
                    "address": device.address,
                    "rssi": device.rssi
                }
                
                # Add additional data if available
                if active and device.advertisement_data:
                    if device.advertisement_data.manufacturer_data:
                        device_info["manufacturer_data"] = {
                            str(k): list(v) for k, v in device.advertisement_data.manufacturer_data.items()
                        }
                    if device.advertisement_data.service_data:
                        device_info["service_data"] = {
                            str(k): list(v) for k, v in device.advertisement_data.service_data.items()
                        }
                    if device.advertisement_data.service_uuids:
                        device_info["service_uuids"] = device.advertisement_data.service_uuids
                
                filtered_devices.append(device_info)
            
            return filtered_devices
        except Exception as e:
            self.logger.error(f"Error scanning with filters: {e}", exc_info=True)
            raise BleakError(f"Filtered scan failed: {str(e)}")