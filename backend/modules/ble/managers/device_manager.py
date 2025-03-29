"""BLE Device management functionality."""

import asyncio
import time
from typing import Dict, Any, List, Optional, Tuple, Callable
import logging
from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError
import platform

class BleDeviceManager:
    """Manages BLE device operations including scanning, connecting and data exchange."""
    
    def __init__(self, metrics_collector=None, logger=None):
        """Initialize the device manager."""
        self.logger = logger or logging.getLogger(__name__)
        self.metrics_collector = metrics_collector
        self.client = None
        self.device_address = None
        self.is_scanning = False
        self.scan_lock = asyncio.Lock()
        self.system_platform = platform.system()
        self._active_notifications = {}
        
    # [All the existing methods up to stop_notify are fine]
    
    async def stop_notify(self, char_uuid: str) -> bool:
        """
        Stop notifications for a characteristic.
        
        Args:
            char_uuid: UUID of the characteristic
            
        Returns:
            bool: True if notifications stopped successfully
        """
        if not self.client or not self.client.is_connected:
            raise BleakError("Not connected to device")
        
        try:
            self.logger.info(f"Stopping notifications for characteristic: {char_uuid}")
            
            # Stop notifications
            await self.client.stop_notify(char_uuid)
            
            # Remove the callback
            if char_uuid in self._active_notifications:
                del self._active_notifications[char_uuid]
            
            self.logger.info(f"Successfully stopped notifications for: {char_uuid}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping notifications: {e}")
            raise BleakError(f"Error stopping notifications: {e}")
    
    async def get_device_info(self) -> Dict[str, Any]:
        """
        Get information about the connected device.
        
        Returns:
            Dict with device information
        """
        if not self.client or not self.client.is_connected:
            raise BleakError("Not connected to device")
        
        try:
            self.logger.info("Getting device information")
            
            # Basic device info
            device_info = {
                "address": self.device_address,
                "connected": self.client.is_connected,
                "mtu": getattr(self.client, "mtu_size", None),
                "services_resolved": self.client.services is not None,
                "platform": self.system_platform
            }
            
            # Get service count if available
            if self.client.services:
                device_info["service_count"] = len(self.client.services)
                
                # Try to identify device type based on services
                device_info["device_type"] = self._identify_device_type(self.client.services)
            
            return device_info
            
        except Exception as e:
            self.logger.error(f"Error getting device info: {e}")
            raise BleakError(f"Error getting device info: {e}")
    
    def _identify_device_type(self, services) -> str:
        """
        Try to identify the device type based on its services.
        
        Args:
            services: Service list from the BleakClient
            
        Returns:
            String describing the device type or "Unknown"
        """
        # Common service UUIDs and their associated device types
        device_profiles = {
            "1800": "Generic Access",
            "1801": "Generic Attribute",
            "180D": "Heart Rate",
            "180F": "Battery Service",
            "1812": "HID",
            "1813": "Scan Parameters",
            "1818": "Cycling Power",
            "1819": "Cycling Speed and Cadence",
            "181C": "User Data",
            "181D": "Weight Scale",
            "181E": "Bond Management",
            "181F": "Continuous Glucose Monitoring",
            "FFF0": "Nordic UART Service",
            "180A": "Device Information"
        }
        
        # Check for common device types
        service_uuids = [service.uuid for service in services]
        
        # Check for health devices
        if any(uuid.startswith("180D") for uuid in service_uuids):
            return "Health (Heart Rate)"
        elif any(uuid.startswith("1809") for uuid in service_uuids):
            return "Health (Temperature)"
        elif any(uuid.startswith("1812") for uuid in service_uuids):
            return "HID (Input Device)"
        elif any(uuid.startswith("FFF0") for uuid in service_uuids):
            return "Nordic UART Device"
        elif any(uuid.startswith("1800") for uuid in service_uuids) and len(service_uuids) <= 3:
            return "Basic BLE Peripheral"
        
        # Default case
        return "Unknown"
    
    async def pair_device(self) -> bool:
        """
        Attempt to pair with the connected device.
        Note: Pairing support depends on the platform and Bleak version.
        
        Returns:
            bool: True if pairing successful or already paired
        """
        if not self.client or not self.client.is_connected:
            raise BleakError("Not connected to device")
        
        try:
            self.logger.info(f"Attempting to pair with device: {self.device_address}")
            
            # Check if the client has a pair method (depends on Bleak version)
            if hasattr(self.client, "pair"):
                result = await self.client.pair()
                self.logger.info(f"Pairing result: {result}")
                return result
            else:
                # For versions without explicit pairing
                self.logger.info("Pairing not supported in this Bleak version")
                return False
                
        except Exception as e:
            self.logger.error(f"Error pairing device: {e}")
            raise BleakError(f"Error pairing: {e}")
    
    async def is_device_available(self, address: str) -> bool:
        """
        Check if a device is available without connecting to it.
        
        Args:
            address: Device address to check
            
        Returns:
            bool: True if the device is available
        """
        try:
            self.logger.debug(f"Checking if device {address} is available")
            
            # Quick scan to see if the device is advertising
            scanner = BleakScanner()
            await scanner.start()
            
            # Wait briefly for results
            await asyncio.sleep(2.0)
            
            # Get discovered devices
            devices = await scanner.get_discovered_devices()
            
            # Stop scanner
            await scanner.stop()
            
            # Check if the device is in the discovered devices
            for device in devices:
                if hasattr(device, 'address') and device.address.lower() == address.lower():
                    self.logger.debug(f"Device {address} is available")
                    return True
            
            self.logger.debug(f"Device {address} not found")
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking device availability: {e}")
            return False
    
    async def get_descriptor_value(self, descriptor_handle: int) -> Dict[str, Any]:
        """
        Read a descriptor value.
        
        Args:
            descriptor_handle: The handle of the descriptor
            
        Returns:
            Dict with the descriptor value
        """
        if not self.client or not self.client.is_connected:
            raise BleakError("Not connected to device")
        
        try:
            self.logger.info(f"Reading descriptor: {descriptor_handle}")
            
            # Read the descriptor
            value = await self.client.read_gatt_descriptor(descriptor_handle)
            
            # Format the value
            hex_value = value.hex()
            text_value = value.decode('utf-8', errors='replace') if value else ""
            
            self.logger.info(f"Read descriptor value: {hex_value}")
            return {
                "value": hex_value,
                "text": text_value,
                "bytes": list(value)
            }
            
        except Exception as e:
            self.logger.error(f"Error reading descriptor: {e}")
            raise BleakError(f"Error reading descriptor: {e}")

    async def scan_devices(self, scan_time=5.0, active=True, service_uuids=None):
        """Scan for BLE devices.
        
        Args:
            scan_time: Duration to scan for in seconds
            active: Whether to use active scanning
            service_uuids: Optional list of service UUIDs to filter by
            
        Returns:
            List of discovered devices
        """
        self.logger.info(f"Scanning for devices (scan_time={scan_time}, active={active})")
        
        # Record scan start in metrics if available
        scan_id = None
        if hasattr(self.metrics_collector, "record_scan_start"):
            scan_id = self.metrics_collector.record_scan_start()
        
        try:
            # Implement your device scanning logic
            # This is just a mock implementation - replace with your actual code
            import random
            import time
            
            # Simulate scanning delay
            await asyncio.sleep(min(scan_time, 2.0))
            
            # Generate mock devices
            devices = []
            for i in range(random.randint(3, 8)):
                # Create a mock MAC address
                mac = ":".join([f"{random.randint(0, 255):02X}" for _ in range(6)])
                
                device = {
                    "address": mac,
                    "name": f"Mock Device {i+1}",
                    "rssi": random.randint(-90, -40)
                }
                devices.append(device)
            
            # Record scan completion in metrics if available
            if scan_id and hasattr(self.metrics_collector, "record_scan_complete"):
                self.metrics_collector.record_scan_complete(
                    scan_id, success=True, device_count=len(devices)
                )
            
            return devices
        except Exception as e:
            self.logger.error(f"Error scanning for devices: {e}", exc_info=True)
            
            # Record scan failure in metrics if available
            if scan_id and hasattr(self.metrics_collector, "record_scan_complete"):
                self.metrics_collector.record_scan_complete(
                    scan_id, success=False, error=str(e)
                )
                
            raise