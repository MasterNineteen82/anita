import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

# Setup proper logging
logger = logging.getLogger(__name__)

@dataclass
class BLEDeviceInfo:
    """Class to store BLE device information"""
    address: str
    name: Optional[str] = None
    rssi: Optional[int] = None
    manufacturer_data: Optional[Dict[int, bytes]] = None
    service_data: Optional[Dict[str, bytes]] = None
    service_uuids: List[str] = field(default_factory=list)
    last_seen: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert device info to dictionary"""
        return {
            "address": self.address,
            "name": self.name or "Unknown Device",
            "rssi": self.rssi,
            "service_uuids": self.service_uuids,
            "last_seen": self.last_seen,
            "manufacturer_data": {k: v.hex() for k, v in self.manufacturer_data.items()} if self.manufacturer_data else {},
            "service_data": {k: v.hex() for k, v in self.service_data.items()} if self.service_data else {}
        }

class DeviceCache:
    """Class to cache BLE devices"""
    def __init__(self, max_age: int = 300):
        self.devices: Dict[str, BLEDeviceInfo] = {}
        self.max_age = max_age  # Maximum age in seconds
        
    def add_device(self, device: BLEDeviceInfo) -> None:
        """Add or update a device in the cache"""
        self.devices[device.address] = device
        
    def get_device(self, address: str) -> Optional[BLEDeviceInfo]:
        """Get a device from the cache by address"""
        return self.devices.get(address)
        
    def clean_old_devices(self) -> None:
        """Remove devices that haven't been seen recently"""
        current_time = time.time()
        self.devices = {
            addr: device for addr, device in self.devices.items()
            if current_time - device.last_seen <= self.max_age
        }
        
    def clear(self) -> None:
        """Clear all devices from the cache"""
        self.devices = {}
        
    def get_all_devices(self) -> List[BLEDeviceInfo]:
        """Get all devices in the cache"""
        return list(self.devices.values())

class BleService:
    def __init__(self, ble_manager):
        self.ble_manager = ble_manager  # Initialize ble_manager
        self.connected_device = None
        self.device_data = {}
        self.listeners = defaultdict(list)
        self.adapter_status = "unknown"
        self.adapter_info = None
        self.adapter_type = None
        self.device_name = None
        self.device_address = None
        self.device_rssi = None
        self.device_services = None
        self.device_characteristics = None
        self.device_descriptors = None
        self.device_mtu = None
        self.device_connection_parameters = None
        self.device_manufacturer_data = None
        self.device_service_data = None
        self.device_tx_power = None
        self.device_appearance = None
        self.device_local_name = None
        self.device_address_type = None
        self.device_uuids = None
        self.device_is_connectable = None
        self.device_is_paired = None
        self.device_is_connected = False
        self.device_is_bluetooth_enabled = False
        self.device_is_location_enabled = False
        self.device_is_bluetooth_le_supported = False
        self.device_is_bluetooth_classic_supported = False
        self.device_is_bluetooth_api_available = False
        self.device_is_bluetooth_scan_mode_supported = False
        self.device_is_bluetooth_advertise_mode_supported = False
        self.device_is_bluetooth_multi_advertisement_supported = False
        self.device_is_bluetooth_offload_filter_supported = False
        self.device_is_bluetooth_offload_scan_batching_supported = False
        self.device_is_bluetooth_extended_advertising_supported = False
        self.device_is_bluetooth_periodic_advertising_supported = False
        self.device_is_bluetooth_iso_supported = False
        self.device_is_bluetooth_broadcast_supported = False
        self.device_is_bluetooth_a2dp_supported = False
        self.device_is_bluetooth_hfp_supported = False
        self.device_is_bluetooth_hid_supported = False
        self.device_is_bluetooth_opp_supported = False
        self.device_is_bluetooth_pan_supported = False
        self.device_is_bluetooth_pbap_supported = False
        self.device_is_bluetooth_map_supported = False
        self.device_is_bluetooth_sap_supported = False
        self.device_is_bluetooth_gatt_supported = False
        self.device_is_bluetooth_l2cap_supported = False
        self.device_is_bluetooth_rfcomm_supported = False
        self.device_is_bluetooth_avrcp_supported = False
        self.device_is_bluetooth_hsp_supported = False
        self.device_is_bluetooth_dun_supported = False
        self.device_is_bluetooth_bip_supported = False
        self.device_is_bluetooth_ftp_supported = False
        self.device_is_bluetooth_opp_client_supported = False
        self.device_is_bluetooth_opp_server_supported = False
        self.device_is_bluetooth_panu_supported = False
        self.device_is_bluetooth_nap_supported = False
        self.device_is_bluetooth_gn_supported = False
        self.device_is_bluetooth_dun_client_supported = False
        self.device_is_bluetooth_dun_server_supported = False
        self.device_is_bluetooth_bip_client_supported = False
        self.device_is_bluetooth_bip_server_supported = False
        self.device_is_bluetooth_ftp_client_supported = False
        self.device_is_bluetooth_ftp_server_supported = False
        self.device_is_bluetooth_map_client_supported = False
        self.device_is_bluetooth_map_server_supported = False
        self.device_is_bluetooth_sap_client_supported = False
        self.device_is_bluetooth_sap_server_supported = False
        self.device_is_bluetooth_avrcp_controller_supported = False
        self.device_is_bluetooth_avrcp_target_supported = False
        self.device_is_bluetooth_hsp_headset_supported = False
        self.device_is_bluetooth_hsp_audio_gateway_supported = False
        self.device_is_bluetooth_hfp_headset_supported = False
        self.device_is_bluetooth_hfp_audio_gateway_supported = False
        self.device_is_bluetooth_hid_host_supported = False
        self.device_is_bluetooth_hid_device_supported = False
        self.device_is_bluetooth_le_central_supported = False
        self.device_is_bluetooth_le_peripheral_supported = False
        self.device_is_bluetooth_le_broadcaster_supported = False
        self.device_is_bluetooth_le_observer_supported = False
        self.device_is_bluetooth_le_privacy_supported = False
        self.device_is_bluetooth_le_connection_oriented_channels_supported = False
        self.device_is_bluetooth_le_audio_supported = False
        self.device_is_bluetooth_le_data_length_extension_supported = False
        self.device_is_bluetooth_le_2m_phy_supported = False
        self.device_is_bluetooth_le_coded_phy_supported = False
        self.device_is_bluetooth_le_advertising_extensions_supported = False
        self.device_is_bluetooth_le_periodic_advertising_supported = False
        self.device_is_bluetooth_le_iso_supported = False
        self.device_is_bluetooth_le_broadcast_supported = False
        self.device_is_bluetooth_le_a2dp_supported = False
        self.device_is_bluetooth_le_hfp_supported = False
        self.device_is_bluetooth_le_hid_supported = False
        self.device_is_bluetooth_le_opp_supported = False
        self.device_is_bluetooth_le_pan_supported = False
        self.device_is_bluetooth_le_pbap_supported = False
        self.device_is_bluetooth_le_map_supported = False
        self.device_is_bluetooth_le_sap_supported = False
        self.device_is_bluetooth_le_avrcp_supported = False
        self.device_is_bluetooth_le_hsp_supported = False
        self.device_is_bluetooth_le_dun_supported = False
        self.device_is_bluetooth_le_bip_supported = False
        self.device_is_bluetooth_le_ftp_supported = False
        self.device_is_bluetooth_le_opp_client_supported = False
        self.device_is_bluetooth_le_opp_server_supported = False
        self.device_is_bluetooth_le_panu_supported = False
        self.device_is_bluetooth_le_nap_supported = False
        self.device_is_bluetooth_le_gn_supported = False
        self.device_is_bluetooth_le_dun_client_supported = False
        self.device_is_bluetooth_le_dun_server_supported = False
        self.device_is_bluetooth_le_bip_client_supported = False
        self.device_is_bluetooth_le_bip_server_supported = False
        self.device_is_bluetooth_le_ftp_client_supported = False
        self.device_is_bluetooth_le_ftp_server_supported = False
        self.device_is_bluetooth_le_map_client_supported = False
        self.device_is_bluetooth_le_map_server_supported = False
        self.device_is_bluetooth_le_sap_client_supported = False
        self.device_is_bluetooth_le_sap_server_supported = False
        self.device_is_bluetooth_le_avrcp_controller_supported = False
        self.device_is_bluetooth_le_avrcp_target_supported = False
        self.device_is_bluetooth_le_hsp_headset_supported = False
        self.device_is_bluetooth_le_hsp_audio_gateway_supported = False
        self.device_is_bluetooth_le_hfp_headset_supported = False
        self.device_is_bluetooth_le_hfp_audio_gateway_supported = False
        self.device_is_bluetooth_le_hid_host_supported = False
        self.device_is_bluetooth_le_hid_device_supported = False

    def is_connected(self):
        return getattr(self.ble_manager, 'is_connected', False)

    async def get_adapter_info(self) -> Dict[str, Any]:
        """Get information about the BLE adapter"""
        try:
            return await self.ble_manager.get_adapter_info()
        except Exception as e:
            logger.error(f"Error getting adapter info: {e}", exc_info=True)
            return {"error": str(e)}
            
    async def scan_devices(self, scan_time=5.0, timeout=5.0, active=True, **kwargs) -> List[Dict[str, Any]]:
        """
        Scan for BLE devices and return a list of found devices.
        
        Args:
            scan_time: Scan duration in seconds (alias for timeout, takes precedence)
            timeout: Scan duration in seconds (old parameter name, for compatibility)
            active: Whether to use active scanning
            **kwargs: Additional scan parameters (ignored if not supported)
        
        Returns:
            List of discovered devices with their information
        """
        try:
            # Handle parameter name differences - the route uses scan_time, but we also accept timeout
            # for backward compatibility
            actual_timeout = scan_time if scan_time != 5.0 else timeout
            
            # Log the scan parameters
            logger.info(f"Scanning for devices (timeout={actual_timeout}s, active={active})")
            
            # Only pass parameters that we know the manager accepts
            # This prevents errors with unknown parameters like 'allow_duplicates'
            scan_params = {
                "timeout": actual_timeout,
                "active": active
            }
            
            # Add supported parameters with validation
            if "name_prefix" in kwargs and kwargs["name_prefix"]:
                scan_params["name_prefix"] = kwargs["name_prefix"]
                
            if "services" in kwargs and kwargs["services"]:
                scan_params["services"] = kwargs["services"]
                
            # Log what we're actually passing to the underlying BLE manager
            logger.debug(f"Passing parameters to scan_for_devices: {scan_params}")
            
            # Perform the scan with only supported parameters
            devices = await self.ble_manager.scan_for_devices(**scan_params)
            
            # Process and normalize device information
            processed_devices = []
            for device in devices:
                # Handle the case where device is already a dict
                if isinstance(device, dict):
                    processed_device = {
                        "address": device.get("address", "unknown"),
                        "name": device.get("name", "Unknown Device"),
                        "rssi": device.get("rssi", -100),
                        "manufacturer_data": device.get("manufacturer_data", {}),
                        "service_data": device.get("service_data", {}),
                        "services": device.get("services", [])
                    }
                    processed_devices.append(processed_device)
                else:
                    # Handle object-based device representation
                    if not hasattr(device, 'address'):
                        logger.warning(f"Device missing address, skipping: {device}")
                        continue
                    
                    processed_device = {
                        "address": device.address,
                        "name": getattr(device, 'name', "Unknown Device"),
                        "rssi": getattr(device, 'rssi', -100),
                        "manufacturer_data": getattr(device, 'manufacturer_data', {}),
                        "service_data": getattr(device, 'service_data', {}),
                        "services": getattr(device, 'services', [])
                    }
                    processed_devices.append(processed_device)
            
            # Only cache if explicitly requested
            if kwargs.get('cache_results', False) and hasattr(self, 'device_cache'):
                self._update_device_cache(processed_devices)
            
            # Log scan results
            logger.info(f"Scan complete, found {len(processed_devices)} devices")
            
            return processed_devices
        except Exception as e:
            logger.error(f"Error during device scan: {e}", exc_info=True)
            # Re-raise the exception with a clearer message
            raise Exception(f"Scan failed: {str(e)}") from e
            
    def _update_device_cache(self, devices):
        """Update the device cache with new scan results"""
        # Skip if no device cache
        if not hasattr(self, 'device_cache'):
            return
            
        try:
            # Make sure the device cache has an update method
            if not hasattr(self.device_cache, 'update'):
                # If there's no update method but there is an add_device method, use that
                if hasattr(self.device_cache, 'add_device'):
                    for device in devices:
                        # Create a BLEDeviceInfo object from the device dict
                        device_info = BLEDeviceInfo(
                            address=device["address"],
                            name=device["name"],
                            rssi=device["rssi"],
                            manufacturer_data=device.get("manufacturer_data", {}),
                            service_data=device.get("service_data", {}),
                            service_uuids=device.get("services", []),
                            last_seen=time.time()
                        )
                        self.device_cache.add_device(device_info)
                else:
                    logger.warning("Device cache doesn't have update or add_device methods")
            else:
                # Use the existing update method
                self.device_cache.update(devices)
                
            logger.debug(f"Updated device cache with {len(devices)} devices")
        except Exception as e:
            logger.warning(f"Error updating device cache: {e}")
            
    async def connect_device(self, address: str) -> Dict[str, Any]:
        """Connect to a BLE device"""
        try:
            result = await self.ble_manager.connect(address)
            return result
        except Exception as e:
            logger.error(f"Error connecting to device {address}: {e}", exc_info=True)
            return {"connected": False, "error": str(e)}
            
    async def disconnect_device(self, address: str) -> Dict[str, Any]:
        """Disconnect from a BLE device"""
        try:
            result = await self.ble_manager.disconnect()
            return result
        except Exception as e:
            logger.error(f"Error disconnecting from device {address}: {e}", exc_info=True)
            return {"disconnected": False, "error": str(e)}
    
    async def reset_adapter(self) -> bool:
        """Reset the BLE adapter"""
        try:
            result = await self.ble_manager.reset_adapter()
            return result
        except Exception as e:
            logger.error(f"Error resetting adapter: {e}", exc_info=True)
            return False
            
    async def device_exists(self, address: str) -> bool:
        """
        Check if a device with the given address exists and is in range
        """
        try:
            # First check if we already have a connection to this device
            if self.ble_manager.is_connected and self.ble_manager.device_address == address:
                return True
                
            # Check if device is in cached devices
            cached_device = self.device_cache.get_device(address)
            if cached_device and time.time() - cached_device.last_seen < 60:  # If seen in last 60 seconds
                return True
                
            # Do a quick scan to check if device is in range
            devices = await self.ble_manager.scan_devices(
                scan_time=2.0,  # Quick 2-second scan
                active=True
            )
            
            # Check if device is in scan results
            for device in devices:
                if device.get('address') == address:
                    return True
                    
            return False
        except Exception as e:
            logger.error(f"Error checking if device exists: {e}")
            return False

    def get_cached_devices(self) -> List[BLEDeviceInfo]:
        """Get the list of recently discovered devices without performing a new scan."""
        logger.info("Getting cached devices...")
        try:
            logger.info(f"Cached devices: {self.device_cache.devices}")  # Log the cache content
            devices = list(self.device_cache.devices.values())
            logger.info(f"Returning cached devices: {devices}")
            return devices
        except Exception as e:
            logger.error(f"Error retrieving cached devices: {e}", exc_info=True)
            return []

    async def get_adapters(self) -> Dict[str, Any]:
        """Get information about all available Bluetooth adapters"""
        try:
            return await self.ble_manager.get_adapter_info()
        except Exception as e:
            logger.error(f"Error getting adapter list: {e}", exc_info=True)
            return {"adapters": [], "count": 0, "error": str(e)}

    async def set_active_adapter(self, adapter_address: str) -> bool:
        """Set the active Bluetooth adapter"""
        try:
            return await self.ble_manager.set_active_adapter(adapter_address)
        except Exception as e:
            logger.error(f"Error setting active adapter: {e}", exc_info=True)
            return False
            
    def is_connected(self) -> bool:
        """Check if a device is currently connected"""
        return getattr(self.ble_manager, 'is_connected', False)
        
    def get_connected_device_address(self) -> Optional[str]:
        """Get the address of the currently connected device"""
        return getattr(self.ble_manager, 'device_address', None)
        
    def get_connection_uptime(self) -> Optional[float]:
        """Get the connection uptime in seconds"""
        connection_time = getattr(self.ble_manager, 'connection_time', None)
        if connection_time:
            return time.time() - connection_time
        return None
        
    async def handle_notification(self, characteristic_uuid: str, value):
        """
        Handle characteristic notifications.
        
        Args:
            characteristic_uuid: UUID of the characteristic
            value: The notification value
        """
        try:
            # Log the notification
            logger.debug(f"Notification from {characteristic_uuid}: {value}")
            
            # You can't import notification_manager here due to circular import
            # We'll notify the notification manager indirectly through the event bus
            # Emit notification event
            from backend.modules.ble.events import ble_event_bus
            
            device_address = self.get_connected_device_address()
            ble_event_bus.emit('notification', {
                'characteristic': characteristic_uuid,
                'value': value,
                'device': device_address
            })
        except Exception as e:
            logger.error(f"Error handling notification: {e}")