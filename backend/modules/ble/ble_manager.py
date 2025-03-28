import asyncio
import logging
import os
import platform
import struct
import sys # noqa: F401
import time
from typing import Any, Callable, Dict, List, Optional, Set
import logging

from bleak import BleakClient, BleakError, BleakScanner
# Get version safely using metadata or package info

from importlib.metadata import version
try:
    __version__ = version("bleak")
except ImportError:
    __version__ = "Unknown"
    
import bleak
from bleak.backends.characteristic import BleakGATTCharacteristic # noqa: F401
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData # noqa: F401
from fastapi import HTTPException # noqa: F401

logger = logging.getLogger(__name__)
class BLEManager:
    def __init__(self, logger=None, bonded_devices_file="bonded_devices.txt"):
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
        self.bonded_devices_file = bonded_devices_file  # Store the file path
        self._load_bonded_devices()
        
        self.logger.info(f"BLE Manager initialized using Bleak {platform.system()}")

    def _load_bonded_devices(self):
        """Load previously bonded devices from storage."""
        try:
            # Simple implementation using a file
            # In production, use a more robust storage solution
            if os.path.exists(self.bonded_devices_file):
                with open(self.bonded_devices_file, "r") as f:
                    self.bonded_devices = set(line.strip() for line in f if line.strip())
                self.logger.info(f"Loaded {len(self.bonded_devices)} bonded devices")
        except Exception as e:
            self.logger.error(f"Failed to load bonded devices: {e}")

    def _save_bonded_devices(self):
        """Save bonded devices to storage."""
        try:
            with open(self.bonded_devices_file, "w") as f:
                for device in self.bonded_devices:
                    f.write(f"{device}\n")
            self.logger.info(f"Saved {len(self.bonded_devices)} bonded devices")
        except Exception as e:
            self.logger.error(f"Failed to save bonded devices: {e}")

    def get_cached_devices(self):
        """
        Return currently cached devices from the last scan
        """
        if hasattr(self, '_cached_devices'):
            return self._cached_devices
        return []

    async def scan_devices(self, scan_time=5.0, active=True, name_prefix=None, services=None, allow_duplicates=False):
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
            devices = await BleakScanner.discover(timeout=scan_time)

            # Log all discovered devices before filtering
            try:
                # Existing scan code
                logger.info(f"Raw scan results: {[device.address for device in devices]}")
            except Exception as e:
                logger.error(f"Scan failed: {str(e)}", exc_info=True)

            results = []
            seen_addresses = set()
            for device in devices:
                if not allow_duplicates and device.address in seen_addresses:
                    continue

                if name_prefix and (not device.name or not device.name.startswith(name_prefix)):
                    continue

                seen_addresses.add(device.address)
                results.append({
                    "address": device.address.lower(),  # Convert to lowercase
                    "name": device.name or "Unknown Device",
                    "rssi": device.rssi
                })

            # Store the scan results
            self._cached_devices = devices

            return results
        except Exception as e:
            # Log the error
            logger.error(f"Scan failed: {str(e)}", exc_info=True)
            return []
        
        
    def _normalize_ble_address(self, address: str) -> str:
        """Normalize a BLE address to ensure correct format."""
        if not address:
            return address
            
        # Remove any non-alphanumeric chars except ':'
        address = ''.join(c for c in address if c.isalnum() or c == ':')
        
        # Split by ':' and ensure each segment is correct length
        parts = address.split(':')
        if len(parts) == 6:
            # Make sure each part is exactly 2 chars
            parts = [part[-2:].zfill(2) for part in parts]
            return ':'.join(parts)
        
        return address
        
    def _process_device_list(self, devices_list) -> List[Dict]:
        """Process a list of BLEDevice objects."""
        result = []
        if not isinstance(devices_list, list):
            self.logger.warning(f"Expected list but got {type(devices_list)}")
            return result
            
        for device in devices_list:
            if not isinstance(device, BLEDevice):
                self.logger.warning(f"Skipping non-BLEDevice object: {device}")
                continue
                
            # Normalize address
            address = self._normalize_ble_address(device.address)

            device_info = {
                "name": device.name if hasattr(device, "name") and device.name else "Unknown Device",
                "address": address,
                # Using RSSI safely with fallback
                "rssi": getattr(device, "rssi", -100),
                "bonded": address in self.bonded_devices
            }
            result.append(device_info)
            
        return result

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

    async def get_services(self):
        if not self.client or not self.client.is_connected:
            raise BleakError("Not connected to a device")
        return self.client.services

    async def get_characteristics(self, service_uuid):
        service = self.client.services.get_service(service_uuid)
        return service.characteristics if service else []

    async def read_characteristic(self, char_uuid):
        if not self.client or not self.client.is_connected:
            raise BleakError("Not connected to a device")
        value = await self.client.read_gatt_char(char_uuid)
        return {
            "value": value.hex(),
            "text": value.decode("utf-8", errors="ignore")
        }

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

    async def start_notify(self, char_uuid, callback):
        if not self.client or not self.client.is_connected:
            raise BleakError("Not connected to a device")
        await self.client.start_notify(char_uuid, callback)

    async def stop_notify(self, char_uuid):
        if not self.client or not self.client.is_connected:
            raise BleakError("Not connected to a device")
        await self.client.stop_notify(char_uuid)

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
        
        # Add these methods to the BLEManager class

    async def is_adapter_available(self) -> bool:
        """
        Check if Bluetooth adapter is available and powered on.
        
        Returns:
            bool: True if adapter is available, False otherwise
        """
        try:
            # Use BleakScanner to perform a quick check if the adapter is working
            await BleakScanner.discover(timeout=0.5)
            self.logger.info("Bluetooth adapter is available")
            return True
        except BleakError as e:
            self.logger.warning(f"Bluetooth adapter check failed: {e}")
            if "No Bluetooth adapters found" in str(e):
                return False
            # Other errors might mean the adapter exists but is in a problem state
            return False
        except Exception as e:
            self.logger.error(f"Error checking adapter availability: {e}")
            return False

    async def get_adapter_info(self) -> dict:
        """
        Get detailed information about the Bluetooth adapter.
        
        Returns:
            dict: Comprehensive information about the adapter
        """
        adapter_available = await self.is_adapter_available()
        
        # Get platform-specific adapter info
        system_platform = platform.system()
        adapter_address = "Unknown"
        adapter_name = "Unknown"
        adapter_vendor = "Unknown"
        adapter_model = "Unknown"
        adapter_firmware = "Unknown"
        hci_version = "Unknown"
        
        # Get Bleak version safely - this fixes the "__version__" attribute error
        bleak_version = "Unknown"
        try:
            # Try multiple ways to get the version
            if hasattr(bleak, '__version__'):
                bleak_version = bleak.__version__
            else:
                try:
                    # Try to get version from package metadata
                    from importlib.metadata import version
                    bleak_version = version("bleak")
                except (ImportError, Exception):
                    # Fallback using the version we defined at the top
                    if '__version__' in globals():
                        bleak_version = __version__
        except Exception as e:
            self.logger.debug(f"Error determining Bleak version: {e}")
        
        try:
            if system_platform == "Windows":
                # WINDOWS-SPECIFIC DETECTION - OPTIMIZED APPROACH
                self.logger.info("Collecting Windows Bluetooth adapter information...")
                
                # Method 1: Use Get-NetAdapter cmdlet focused on Bluetooth interfaces
                try:
                    import subprocess
                    ps_cmd = """
                    Get-NetAdapter | Where-Object {
                        $_.InterfaceDescription -like '*bluetooth*' -or 
                        $_.Name -like '*bluetooth*'
                    } | Select-Object Name, InterfaceDescription, MacAddress, Status | ConvertTo-Json
                    """
                    
                    try:
                        self.logger.debug("Executing PowerShell command for adapter info")
                        result = subprocess.check_output(["powershell", "-Command", ps_cmd], 
                                                        stderr=subprocess.STDOUT, 
                                                        timeout=3)  # Add timeout for better performance
                        result_str = result.decode('utf-8', errors='ignore')
                        
                        import json
                        try:
                            adapters = json.loads(result_str)
                            if adapters is None:  # Handle empty response
                                self.logger.debug("No Bluetooth adapters found from Get-NetAdapter")
                            elif not isinstance(adapters, list):
                                adapters = [adapters]
                            
                            for adapter in adapters:
                                if adapter and adapter.get('Status') and 'Up' in adapter.get('Status'):
                                    # Found an active Bluetooth adapter
                                    if adapter.get('MacAddress'):
                                        adapter_address = adapter.get('MacAddress')
                                    if adapter.get('Name'):
                                        adapter_name = adapter.get('Name')
                                    if adapter.get('InterfaceDescription'):
                                        description = adapter.get('InterfaceDescription')
                                        if "(" in description:
                                            adapter_vendor = description.split("(")[0].strip()
                                            if ")" in description:
                                                model_part = description.split("(")[1].split(")")[0].strip()
                                                if "Hard Drive" not in model_part:
                                                    adapter_model = model_part
                                        else:
                                            adapter_model = description
                                    break
                        
                        except json.JSONDecodeError as e:
                            self.logger.warning(f"Failed to parse Get-NetAdapter JSON output: {e}")
                    
                    except subprocess.TimeoutExpired:
                        self.logger.warning("PowerShell command timed out, proceeding with other methods")
                    except subprocess.CalledProcessError as e:
                        self.logger.warning(f"Method 1 (Get-NetAdapter) failed with exit code {e.returncode}")
                
                except Exception as e:
                    self.logger.warning(f"Method 1 (Get-NetAdapter) failed: {e}")
                
                # Method 2: Directly query BT radio from Device Manager
                if adapter_name == "Unknown" or adapter_address == "Unknown":
                    try:
                        ps_cmd = """
                        Get-PnpDevice -Class Bluetooth -FriendlyName '*radio*' | 
                        Select-Object FriendlyName, InstanceId, Manufacturer, Status | ConvertTo-Json -Depth 2
                        """
                        
                        result = subprocess.check_output(["powershell", "-Command", ps_cmd], 
                                                        stderr=subprocess.STDOUT,
                                                        timeout=3)
                        result_str = result.decode('utf-8', errors='ignore')
                        
                        try:
                            devices = json.loads(result_str)
                            if devices is None:  # Handle empty response
                                self.logger.debug("No Bluetooth devices found from Get-PnpDevice")
                            elif not isinstance(devices, list):
                                devices = [devices]
                            
                            for device in devices:
                                if device and device.get('Status') == 'OK':
                                    if device.get('FriendlyName'):
                                        adapter_name = device.get('FriendlyName')
                                    
                                    if device.get('Manufacturer'):
                                        adapter_vendor = device.get('Manufacturer')
                                    
                                    if device.get('InstanceId'):
                                        # Try to extract MAC from Instance ID
                                        instance_id = device.get('InstanceId')
                                        # Look for common patterns in Windows InstanceIDs
                                        id_parts = instance_id.split('\\')
                                        for part in id_parts:
                                            if len(part) == 12 and all(c in '0123456789ABCDEF' for c in part.upper()):
                                                # Likely a MAC address in hex format
                                                formatted_mac = ':'.join(part[i:i+2].upper() for i in range(0, len(part), 2))
                                                adapter_address = formatted_mac
                                                break
                        except json.JSONDecodeError:
                            self.logger.warning("Failed to parse Get-PnpDevice JSON output")
                    except subprocess.TimeoutExpired:
                        self.logger.warning("PowerShell command timed out, proceeding with other methods")
                    except Exception as e:
                        self.logger.warning(f"Method 2 (Get-PnpDevice) failed: {e}")
                
                # Method 3: Use WinRT API only if previous methods failed (slower but more reliable)
                if (adapter_name == "Unknown" or adapter_address == "Unknown") and platform.version().split('.')[0] >= '10':
                    try:
                        # This approach works on Windows 10 or later with appropriate dependencies
                        ps_cmd = """
                        Add-Type -AssemblyName System.Runtime.WindowsRuntime
                        $asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
                        Function Await($WinRtTask, $ResultType) {
                            $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
                            $netTask = $asTask.Invoke($null, @($WinRtTask))
                            $netTask.Wait(-1) | Out-Null
                            $netTask.Result
                        }
                        
                        try {
                            [Windows.Devices.Bluetooth.BluetoothAdapter,Windows.Devices.Bluetooth,ContentType=WindowsRuntime] | Out-Null
                            $adapter = [Windows.Devices.Bluetooth.BluetoothAdapter]::GetDefaultAsync()
                            $adapter = Await $adapter ([Windows.Devices.Bluetooth.BluetoothAdapter])
                            
                            $deviceInfo = [PSCustomObject]@{
                                Name = $adapter.Name
                                BluetoothAddress = $adapter.BluetoothAddress.ToString("X")
                                IsClassicSupported = $adapter.IsClassicSupported
                                IsLowEnergySupported = $adapter.IsLowEnergySupported
                            }
                            
                            ConvertTo-Json -InputObject $deviceInfo
                        } catch {
                            # Return empty JSON if error occurs
                            "{}"
                        }
                        """
                        
                        result = subprocess.check_output(["powershell", "-Command", ps_cmd], 
                                                    stderr=subprocess.STDOUT,
                                                    timeout=5)  # Give this more time as it's more complex
                        result_str = result.decode('utf-8', errors='ignore')
                        
                        try:
                            device_info = json.loads(result_str)
                            
                            if device_info and device_info.get('Name'):
                                adapter_name = device_info.get('Name')
                            
                            if device_info and device_info.get('BluetoothAddress'):
                                # Format the address with colons
                                addr = device_info.get('BluetoothAddress')
                                if len(addr) == 12:  # Expecting a 12-char hex string
                                    adapter_address = ':'.join(addr[i:i+2].upper() for i in range(0, len(addr), 2))
                        except json.JSONDecodeError:
                            self.logger.warning("Failed to parse WinRT API JSON output")
                    except subprocess.TimeoutExpired:
                        self.logger.warning("WinRT PowerShell command timed out")
                    except Exception as e:
                        self.logger.debug(f"Method 3 (WinRT API) failed: {e}")
                
                # Method 4: Use registry as fallback (only if other methods failed)
                if adapter_name == "Unknown" or adapter_address == "Unknown":
                    try:
                        import winreg
                        
                        # Look in several possible registry locations
                        registry_paths = [
                            r"SYSTEM\CurrentControlSet\Services\BTHPORT\Parameters\Devices",
                            r"SYSTEM\CurrentControlSet\Services\BTH\Parameters\Devices",
                            r"SYSTEM\CurrentControlSet\services\BTHUSB\Parameters",
                            r"SYSTEM\CurrentControlSet\Enum\BTH"
                        ]
                        
                        for path in registry_paths:
                            try:
                                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
                                    # Try to enumerate subkeys (which might be device MAC addresses)
                                    try:
                                        i = 0
                                        while True:
                                            subkey_name = winreg.EnumKey(key, i)
                                            # Check if this looks like a MAC address (12 hex chars)
                                            if len(subkey_name) == 12 and all(c in '0123456789abcdefABCDEF' for c in subkey_name):
                                                adapter_address = ':'.join(subkey_name[i:i+2].upper() for i in range(0, len(subkey_name), 2))
                                                break
                                            i += 1
                                    except EnvironmentError:
                                        # No more subkeys
                                        pass
                            except Exception:
                                continue
                    
                    except Exception as e:
                        self.logger.warning(f"Method 4 (Registry) failed: {e}")

            elif system_platform == "Linux":
                # Linux-specific adapter info with improved detection methods
                import subprocess
                try:
                    # Basic adapter info using hciconfig
                    try:
                        result = subprocess.check_output(["hciconfig"], stderr=subprocess.STDOUT, timeout=2).decode('utf-8', errors='ignore')
                        for line in result.splitlines():
                            if "Address:" in line:
                                adapter_address = line.split("Address:")[1].strip()
                            if "Name:" in line:
                                adapter_name = line.split("'")[1].strip() if "'" in line else "Bluetooth Adapter"
                            if "HCI Version:" in line:
                                hci_version = line.split("HCI Version:")[1].split("Revision:")[0].strip()
                    except subprocess.TimeoutExpired:
                        self.logger.warning("hciconfig command timed out")
                    
                    # Get more detailed information using bluetoothctl
                    try:
                        ctrl_result = subprocess.check_output(["bluetoothctl", "show"], stderr=subprocess.STDOUT, timeout=2).decode('utf-8', errors='ignore')
                        for line in ctrl_result.splitlines():
                            line = line.strip()
                            if "Controller" in line and "Name:" not in line:
                                parts = line.split()
                                if len(parts) >= 2:
                                    adapter_address = parts[1].strip()
                            if "Name:" in line and ":" in line:
                                adapter_name = line.split(":", 1)[1].strip()
                            if "Firmware:" in line and ":" in line:
                                adapter_firmware = line.split(":", 1)[1].strip()
                    except subprocess.TimeoutExpired:
                        self.logger.warning("bluetoothctl command timed out")
                    except Exception as e:
                        self.logger.debug(f"Error getting bluetoothctl info: {e}")
                    
                    # Try to get vendor/model info from lsusb
                    try:
                        lsusb_result = subprocess.check_output(["lsusb"], stderr=subprocess.STDOUT, timeout=2).decode('utf-8', errors='ignore')
                        for line in lsusb_result.splitlines():
                            if "Bluetooth" in line:
                                parts = line.split()
                                if len(parts) >= 6:
                                    adapter_vendor = parts[5].replace("Technology", "").replace("Inc.", "").strip()
                                    adapter_model = ' '.join(parts[6:]).replace("Bluetooth", "").strip()
                    except subprocess.TimeoutExpired:
                        self.logger.warning("lsusb command timed out")
                    except Exception as e:
                        self.logger.debug(f"Error getting lsusb info: {e}")
                except Exception as e:
                    self.logger.warning(f"Error getting Linux adapter info: {e}")
                
            elif system_platform == "Darwin":  # macOS
                # macOS-specific adapter info detection
                import subprocess
                try:
                    # Use system_profiler to get Bluetooth information
                    try:
                        result = subprocess.check_output(["system_profiler", "SPBluetoothDataType"], 
                                                    stderr=subprocess.STDOUT, 
                                                    timeout=3).decode('utf-8', errors='ignore')
                        
                        bt_controller_section = False
                        for line in result.splitlines():
                            line = line.strip()
                            if "Bluetooth Controller" in line:
                                bt_controller_section = True
                            elif bt_controller_section:
                                if not line or ":" not in line:
                                    # End of controller section
                                    bt_controller_section = False
                                elif "Address:" in line or "Bluetooth Address:" in line:
                                    adapter_address = line.split(":", 1)[1].strip()
                                elif "Manufacturer:" in line:
                                    adapter_vendor = line.split(":", 1)[1].strip()
                                elif "Transport:" in line:
                                    adapter_model = line.split(":", 1)[1].strip()
                                elif "Firmware Version:" in line:
                                    adapter_firmware = line.split(":", 1)[1].strip()
                                elif "Name:" in line:
                                    adapter_name = line.split(":", 1)[1].strip()
                    except subprocess.TimeoutExpired:
                        self.logger.warning("system_profiler command timed out")
                    
                    # Try ioreg as an alternative if system_profiler didn't work
                    if adapter_address == "Unknown":
                        try:
                            ioreg_result = subprocess.check_output(["ioreg", "-l", "-p", "IODeviceTree", "-r", "-n", "bluetooth"], 
                                                                stderr=subprocess.STDOUT, 
                                                                timeout=3).decode('utf-8', errors='ignore')
                            for line in ioreg_result.splitlines():
                                if "bluetooth-address" in line:
                                    parts = line.split('=')
                                    if len(parts) >= 2:
                                        # Extract the hex value and format it
                                        hex_val = parts[1].strip().strip('"<>').replace(' ', '')
                                        if len(hex_val) >= 12:
                                            adapter_address = ':'.join(hex_val[i:i+2].upper() for i in range(0, 12, 2))
                                            break
                        except subprocess.TimeoutExpired:
                            self.logger.warning("ioreg command timed out")
                        except Exception as e:
                            self.logger.debug(f"Error getting ioreg info: {e}")
                except Exception as e:
                    self.logger.warning(f"Error getting macOS adapter info: {e}")
        
        except Exception as e:
            self.logger.warning(f"Error getting adapter info: {e}")
            
        # ENHANCED FALLBACK MECHANISM
        # If still no name but we have an address, create a name from that
        if adapter_name == "Unknown" and adapter_address != "Unknown":
            short_addr = adapter_address.replace(':', '')[-4:]
            adapter_name = f"Bluetooth Adapter ({short_addr})"
            
        # If we still don't have a model but have a vendor, create a generic model
        if adapter_model == "Unknown" and adapter_vendor != "Unknown":
            adapter_model = f"{adapter_vendor} Bluetooth"
        
        # If we have partial MAC address information, try to clean it up
        if adapter_address != "Unknown" and ":" not in adapter_address and len(adapter_address) >= 12:
            # Try to format it as a proper MAC
            clean_addr = ''.join(c for c in adapter_address if c in '0123456789abcdefABCDEF')
            if len(clean_addr) >= 12:
                adapter_address = ':'.join(clean_addr[:12][i:i+2].upper() for i in range(0, len(clean_addr), 2))
        
        # Create comprehensive device info
        features = {
            "BLE": True,
            "BR/EDR": system_platform != "iOS",
            "Scanning": True,
            "Bonding": system_platform in ["Windows", "Linux", "Darwin"],
            "GATT": True,
            "Notifications": True,
            "Extended Advertising": system_platform in ["Linux", "Darwin", "Windows"],
            "LE Secure Connections": True
        }
            
        hardware_info = {
            "vendor": adapter_vendor,
            "model": adapter_model,
            "firmware": adapter_firmware,
            "hci_version": hci_version
        }
        
        # Create the final adapter info with proper error handling for Bleak version
        adapter_info = {
            "available": adapter_available,
            "name": adapter_name,
            "address": adapter_address,
            "platform": system_platform,
            "api_version": f"Bleak {bleak_version}",  # Use our safely retrieved version
            "features": features,
            "hardware": hardware_info,
            "timestamp": time.time()
        }
        
        self.logger.info(f"Adapter info retrieved: {adapter_name} ({adapter_address})")
        return adapter_info

    def is_disconnecting(self) -> bool:
        """Flag to indicate if the device is in the process of disconnecting."""
        return getattr(self, "_disconnecting", False)

    def set_disconnecting(self, value: bool) -> None:
        """Set the disconnecting flag."""
        self._disconnecting = value

    async def disconnection_handler(self, client=None):
        """
        Handle disconnection events.
        
        This is called when the BLE client disconnects, either intentionally or due to
        connection loss.
        """
        auto_reconnect = getattr(self, "auto_reconnect", False)
        
        if self.client:
            self.logger.info(f"Device {self.device_address} disconnected")
            is_disconnecting = getattr(self, "is_disconnecting", False)
            
            # Check if we should attempt to reconnect
            if auto_reconnect and not is_disconnecting:
                self.logger.info(f"Attempting to reconnect to {self.device_address}")
                
                # Add a small delay before reconnecting
                await asyncio.sleep(1)
                
                try:
                    # Clear the client reference to force a new connection
                    self.client = None
                    
                    # Attempt to reconnect
                    await self.connect_to_device(
                        device_address=self.device_address,
                        timeout=10,
                        auto_reconnect=True
                    )
                    
                    self.logger.info(f"Successfully reconnected to {self.device_address}")
                except Exception as e:
                    self.logger.error(f"Failed to reconnect to {self.device_address}: {e}")
            else:
                self.logger.info(f"Not attempting reconnection (auto_reconnect={auto_reconnect}, is_disconnecting={is_disconnecting})")
        
        # Emit disconnection event
        if self.device_address:
            # Notify subscribers
            await self.notify_subscribers("disconnect", {"address": self.device_address})

    async def discover_services(self) -> Dict[str, Any]:
        """
        Discover services for the connected device.
        
        Returns:
            Dict[str, Any]: Dictionary of discovered services
        """
        if not self.client or not self.client.is_connected:
            raise BleakError("Not connected to a device")
        
        self.services_cache = {}
        
        try:
            # Get services
            services = {}
            
            for service in self.client.services:
                if not hasattr(service, 'uuid'):
                    self.logger.warning(f"Service has no UUID attribute: {service}")
                    continue
                    
                if isinstance(service, str):
                    self.logger.warning(f"Service is a string, not a proper service object: {service}")
                    continue
                    
                uuid = str(service.uuid)
                description = self._get_service_description(uuid)
                
                characteristics = []
                for char in service.characteristics:
                    if not hasattr(char, 'uuid'):
                        self.logger.warning(f"Characteristic has no UUID attribute: {char}")
                        continue
                        
                    char_uuid = str(char.uuid)
                    char_desc = self._get_characteristic_description(char_uuid)
                    properties = []
                    
                    if hasattr(char, 'properties'):
                        props = char.properties
                        # Convert numeric properties to string list
                        if isinstance(props, int):
                            if props & 0x01:
                                properties.append("broadcast")
                            if props & 0x02:
                                properties.append("read")
                            if props & 0x04:
                                properties.append("write_without_response")
                            if props & 0x08:
                                properties.append("write")
                            if props & 0x10:
                                properties.append("notify")
                            if props & 0x20:
                                properties.append("indicate")
                            if props & 0x40:
                                properties.append("authenticated_signed_writes")
                            if props & 0x80:
                                properties.append("extended_properties")
                        elif isinstance(props, list):
                            properties = props
                    
                    char_info = {
                        "uuid": char_uuid,
                        "description": char_desc,
                        "properties": properties
                    }
                    characteristics.append(char_info)
                
                service_info = {
                    "uuid": uuid,
                    "description": description,
                    "characteristics": characteristics
                }
                services[uuid] = service_info
            
            self.services_cache = services
            return services
        
        except Exception as e:
            self.logger.error(f"Service discovery failed: {e}")
            raise BleakError(f"Service discovery failed: {e}")

async def get_adapter_info(self) -> dict:
    """Get information about the Bluetooth adapter."""
    try:
        return await self.manager.get_adapter_info()
    except Exception as e:
        self.logger.error(f"Error getting adapter info: {e}")
        raise