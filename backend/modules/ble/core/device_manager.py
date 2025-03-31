"""BLE device discovery and connection management."""

import logging
import asyncio
import platform
import time
from typing import Dict, Any, List, Optional, Tuple, Set, Union, Callable
import uuid

import bleak
from bleak import BleakScanner, BleakClient, BleakError

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

class BleDeviceManager:
    """
    Manages BLE device discovery and connections.
    
    Provides capabilities for:
    - Scanning for nearby devices
    - Connecting to specific devices
    - Managing device connections
    - Device state tracking
    - Reconnection handling
    """
    
    def __init__(self, logger=None):
        """
        Initialize the device manager.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self._adapter_manager = get_adapter_manager()
        self._metrics_collector = get_metrics_collector()
        self._persistence_service = get_persistence_service()
        self._error_recovery = get_error_recovery()
        
        # State tracking
        self._discovered_devices = {}
        self._connected_devices = {}
        self._clients = {}
        self._connection_info = {}
        self._scanning = False
        self._last_scan_time = 0
        self._last_scan_params = None
        
        # Scanner instance (to be initialized on first scan)
        self._scanner = None
        
        # Current client (the last one connected)
        self.client = None
        
        # Platform-specific settings
        self._is_windows = platform.system() == "Windows"
        self._is_linux = platform.system() == "Linux"
        self._is_mac = platform.system() == "Darwin"
        
        # Register for events
        ble_event_bus.on("recovery_action", self._handle_recovery_action)
        ble_event_bus.on("adapter_reset", self._handle_adapter_reset)
    
    async def scan_devices(
        self, 
        params: Optional[Union[ScanParams, Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Scan for nearby BLE devices.
        
        Args:
            params: Optional scan parameters
            
        Returns:
            List of discovered devices
        """
        # Convert dict to model if necessary
        if isinstance(params, dict):
            params = ScanParams(**params)
            
        # Use defaults if not provided
        if params is None:
            params = ScanParams()
        
        try:
            self._scanning = True
            self._last_scan_params = params
            self._last_scan_time = time.time()
            
            # Start metrics tracking
            self._metrics_collector.record_scan_start()
            
            # Emit event
            ble_event_bus.emit("scan_started", {
                "timeout": params.scan_time,
                "filter_duplicates": params.filter_duplicates,
                "service_uuids": params.service_uuids
            })
            
            # Initialize scanner if needed
            if self._scanner is None:
                self._scanner = BleakScanner()
            
            # Configure scanner with service UUIDs if provided
            if params.service_uuids:
                service_filters = []
                for service_uuid in params.service_uuids:
                    try:
                        # Ensure valid UUID
                        service_filters.append(uuid.UUID(service_uuid))
                    except ValueError:
                        self.logger.warning(f"Invalid service UUID: {service_uuid}")
                
                if service_filters:
                    self._scanner = BleakScanner(service_uuids=service_filters)
            
            # Run the scan
            self.logger.info(f"Starting BLE scan for {params.scan_time} seconds")
            scan_duration = params.scan_time or 5.0
            
            discovered_devices = await self._scanner.discover(
                timeout=scan_duration,
                service_uuids=None,  # Already configured in scanner
                return_adv=True  # Include advertisement data
            )
            
            # Process the results
            device_list = []
            for device, adv_data in discovered_devices.items():
                try:
                    # Get rssi
                    rssi = None
                    if adv_data and hasattr(adv_data, "rssi"):
                        rssi = adv_data.rssi
                    
                    # Get service UUIDs
                    service_uuids = []
                    if adv_data and hasattr(adv_data, "service_uuids"):
                        service_uuids = adv_data.service_uuids
                    
                    # Extract manufacturer data
                    manufacturer_data = {}
                    if adv_data and hasattr(adv_data, "manufacturer_data"):
                        for key, value in adv_data.manufacturer_data.items():
                            # Convert bytes to hex string for JSON serialization
                            manufacturer_data[key] = value.hex()
                    
                    # Create device info
                    device_info = {
                        "address": device.address,
                        "name": device.name or "Unknown",
                        "rssi": rssi,
                        "service_uuids": service_uuids,
                        "manufacturer_data": manufacturer_data,
                        "last_seen": time.time(),
                        "connected": device.address in self._connected_devices
                    }
                    
                    # Track the device
                    self._discovered_devices[device.address] = device_info
                    
                    # Add to results
                    device_list.append(device_info)
                except Exception as e:
                    self.logger.warning(f"Error processing device {device}: {e}")
            
            # Filter duplicates if requested
            if params.filter_duplicates:
                # Create a set of addresses to track uniqueness
                unique_addresses = set()
                unique_devices = []
                
                for device in device_list:
                    if device["address"] not in unique_addresses:
                        unique_addresses.add(device["address"])
                        unique_devices.append(device)
                
                device_list = unique_devices
            
            # Sort by signal strength (strongest first)
            device_list.sort(key=lambda d: d.get("rssi", -100), reverse=True)
            
            # Record scan completion
            self._metrics_collector.record_scan_complete(
                success=True,
                device_count=len(device_list)
            )
            
            # Emit event
            ble_event_bus.emit("scan_completed", {
                "devices": device_list,
                "count": len(device_list)
            })
            
            self._scanning = False
            return device_list
        except Exception as e:
            self._scanning = False
            self.logger.error(f"Error scanning for devices: {e}", exc_info=True)
            
            # Record scan failure
            self._metrics_collector.record_scan_complete(
                success=False,
                error=str(e)
            )
            
            # Emit event
            ble_event_bus.emit("scan_error", {
                "error": str(e)
            })
            
            raise BleOperationError(f"Error scanning for devices: {e}")
    
    async def connect_to_device(
        self, 
        address: str,
        params: Optional[Union[ConnectionParams, Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Connect to a BLE device.
        
        Args:
            address: Device address
            params: Optional connection parameters
            
        Returns:
            Connection result with connection status
        """
        # Convert dict to model if necessary
        if isinstance(params, dict):
            params = ConnectionParams(**params)
            
        # Use defaults if not provided
        if params is None:
            params = ConnectionParams()
            
        try:
            # Check if already connected
            if address in self._connected_devices and self._connected_devices[address]:
                client = self._clients.get(address)
                if client and client.is_connected:
                    self.logger.info(f"Already connected to {address}")
                    
                    # Use this client for convenience
                    self.client = client
                    
                    # Return successful connection
                    return {
                        "status": ConnectionStatus.CONNECTED,
                        "device_address": address,
                        "connection_time": self._connection_info.get(address, {}).get("connection_time", 0),
                        "message": "Already connected"
                    }
            
            # Start metrics tracking
            self._metrics_collector.record_connect_start(address)
            
            # Emit event
            ble_event_bus.emit("connection_started", {
                "address": address,
                "timeout": params.timeout
            })
            
            # Create a new client
            self.logger.info(f"Connecting to device {address}")
            
            # Set up connection options based on platform
            connection_options = {}
            
            # Add timeout
            if params.timeout:
                connection_options["timeout"] = params.timeout
                
            # Add platform-specific options
            if self._is_windows:
                if params.use_bluetooth_le_device:
                    connection_options["use_cached_services"] = params.use_cached_services
                    connection_options["connection_type"] = "BluetoothLEDevice"
            elif self._is_linux:
                pass  # No specific Linux options yet
            elif self._is_mac:
                pass  # No specific macOS options yet
            
            # Create and connect the client
            client = BleakClient(address, **connection_options)
            
            # Attempt connection
            connected = False
            try:
                connection_start = time.time()
                connected = await client.connect()
                connection_time = time.time() - connection_start
            except Exception as e:
                self.logger.error(f"Error connecting to {address}: {e}", exc_info=True)
                
                # Record failed connection
                self._metrics_collector.record_connect_complete(
                    address,
                    success=False,
                    error=str(e)
                )
                
                # Emit event
                ble_event_bus.emit("connection_failed", {
                    "address": address,
                    "error": str(e)
                })
                
                # Try to recover
                await self._error_recovery.recover_from_error(
                    "connection_timeout",
                    device_address=address,
                    error_details={"message": str(e)}
                )
                
                raise BleConnectionError(f"Error connecting to device {address}: {e}")
            
            if connected:
                # Store connection info
                self._connected_devices[address] = True
                self._clients[address] = client
                self._connection_info[address] = {
                    "connection_time": connection_time,
                    "connected_at": time.time(),
                    "last_operation": time.time(),
                    "disconnect_requested": False,
                    "auto_reconnect": params.auto_reconnect
                }
                
                # Set as current client
                self.client = client
                
                # Set up disconnection callback for auto-reconnect
                if params.auto_reconnect:
                    client.set_disconnected_callback(
                        lambda c: asyncio.create_task(
                            self._handle_disconnection(address, c)
                        )
                    )
                
                # Record successful connection
                self._metrics_collector.record_connect_complete(
                    address,
                    success=True,
                    connection_time=connection_time
                )
                
                # Emit event
                ble_event_bus.emit("device_connected", {
                    "address": address,
                    "connection_time": connection_time
                })
                
                # Store in persistence service if requested
                if params.remember_device:
                    try:
                        # Get device info
                        device_info = self._discovered_devices.get(address, {})
                        if not device_info:
                            device_info = {
                                "address": address,
                                "name": client.address, # Use address as name if not discovered
                                "last_connected": time.time()
                            }
                        else:
                            device_info["last_connected"] = time.time()
                        
                        # Store device
                        await self._persistence_service.add_bonded_device(device_info)
                    except Exception as e:
                        self.logger.warning(f"Error storing device in persistence service: {e}")
                
                # Return connection result
                return {
                    "status": ConnectionStatus.CONNECTED,
                    "device_address": address,
                    "connection_time": connection_time,
                    "message": "Connected successfully"
                }
            else:
                # Connection failed
                self.logger.error(f"Failed to connect to {address}")
                
                # Record failed connection
                self._metrics_collector.record_connect_complete(
                    address,
                    success=False,
                    error="Connection failed"
                )
                
                # Emit event
                ble_event_bus.emit("connection_failed", {
                    "address": address,
                    "error": "Connection failed"
                })
                
                # Try to recover
                await self._error_recovery.recover_from_error(
                    "connection_failed",
                    device_address=address,
                    error_details={"message": "Connection failed"}
                )
                
                return {
                    "status": ConnectionStatus.FAILED,
                    "device_address": address,
                    "message": "Failed to establish connection"
                }
        except BleConnectionError:
            raise
        except Exception as e:
            self.logger.error(f"Error connecting to device: {e}", exc_info=True)
            
            # Record failed connection
            self._metrics_collector.record_connect_complete(
                address,
                success=False,
                error=str(e)
            )
            
            # Emit event
            ble_event_bus.emit("connection_failed", {
                "address": address,
                "error": str(e)
            })
            
            raise BleConnectionError(f"Error connecting to device: {e}")
    
    async def disconnect_from_device(self, address: str) -> Dict[str, Any]:
        """
        Disconnect from a BLE device.
        
        Args:
            address: Device address
            
        Returns:
            Dictionary with disconnection result
        """
        try:
            # Check if connected
            if address not in self._connected_devices or not self._connected_devices[address]:
                return {
                    "status": ConnectionStatus.DISCONNECTED,
                    "device_address": address,
                    "message": "Not connected"
                }
            
            # Get the client
            client = self._clients.get(address)
            if not client:
                return {
                    "status": ConnectionStatus.DISCONNECTED,
                    "device_address": address,
                    "message": "Not connected (no client)"
                }
            
            # Mark as disconnect requested (to prevent auto-reconnect)
            if address in self._connection_info:
                self._connection_info[address]["disconnect_requested"] = True
            
            # Disconnect
            self.logger.info(f"Disconnecting from device {address}")
            
            # Emit event
            ble_event_bus.emit("disconnection_started", {
                "address": address
            })
            
            try:
                # Try to disconnect cleanly
                await client.disconnect()
            except Exception as e:
                self.logger.warning(f"Error disconnecting from {address}: {e}")
                # Continue with cleanup even if disconnection fails
            
            # Cleanup resources
            self._connected_devices[address] = False
            
            if self.client == client:
                self.client = None
            
            # Emit event
            ble_event_bus.emit("device_disconnected", {
                "address": address,
                "reason": "user_requested"
            })
            
            return {
                "status": ConnectionStatus.DISCONNECTED,
                "device_address": address,
                "message": "Disconnected successfully"
            }
        except Exception as e:
            self.logger.error(f"Error disconnecting from device: {e}", exc_info=True)
            raise BleConnectionError(f"Error disconnecting from device: {e}")
    
    async def get_device_details(self, address: str) -> Dict[str, Any]:
        """
        Get details about a device.
        
        Args:
            address: Device address
            
        Returns:
            Dictionary with device details
        """
        try:
            # Check if discovered
            if address not in self._discovered_devices:
                # Try to find in connected devices
                if address in self._connected_devices and self._connected_devices[address]:
                    # Device is connected but not in discovered list
                    # Create a basic info
                    device_info = {
                        "address": address,
                        "name": "Unknown",
                        "connected": True,
                        "last_seen": time.time()
                    }
                else:
                    # Not discovered or connected
                    return {
                        "device_found": False,
                        "message": "Device not found"
                    }
            else:
                # Get from discovered devices
                device_info = self._discovered_devices[address]
            
            # Check connection state
            connected = address in self._connected_devices and self._connected_devices[address]
            client = self._clients.get(address) if connected else None
            
            # Get connection info
            connection_info = self._connection_info.get(address, {}) if connected else {}
            
            # Create result
            result = {
                "device_found": True,
                "device_info": device_info,
                "connected": connected,
                "connection_info": connection_info
            }
            
            return result
        except Exception as e:
            self.logger.error(f"Error getting device details: {e}", exc_info=True)
            raise BleOperationError(f"Error getting device details: {e}")
    
    async def get_saved_devices(self) -> List[Dict[str, Any]]:
        """
        Get list of previously saved/bonded devices.
        
        Returns:
            List of saved device dictionaries
        """
        try:
            # Get from persistence service
            devices = await self._persistence_service.get_bonded_devices()
            
            # Update connected status
            for device in devices:
                address = device.get("address")
                if address:
                    device["connected"] = (
                        address in self._connected_devices and
                        self._connected_devices[address]
                    )
            
            return devices
        except Exception as e:
            self.logger.error(f"Error getting saved devices: {e}", exc_info=True)
            raise BleOperationError(f"Error getting saved devices: {e}")
    
    async def remove_saved_device(self, address: str) -> bool:
        """
        Remove a device from saved devices.
        
        Args:
            address: Device address
            
        Returns:
            True if successful
        """
        try:
            # Remove from persistence service
            devices = await self._persistence_service.get_bonded_devices()
            
            # Filter out the device
            updated_devices = [d for d in devices if d.get("address") != address]
            
            # If no changes, nothing to do
            if len(updated_devices) == len(devices):
                return True
            
            # Update persistence
            # Note: We're using a hack here since we don't have a proper API for this
            # Ideally, the persistence service would have a remove_bonded_device method
            bonded_devices_file = self._persistence_service.bonded_devices_file
            
            # Write the updated devices
            with open(bonded_devices_file, 'w') as f:
                import json
                json.dump(updated_devices, f, indent=2)
            
            return True
        except Exception as e:
            self.logger.error(f"Error removing saved device: {e}", exc_info=True)
            raise BleOperationError(f"Error removing saved device: {e}")
    
    def get_connection_status(self, address: Optional[str] = None) -> Dict[str, Any]:
        """
        Get connection status.
        
        Args:
            address: Optional device address (returns all if None)
            
        Returns:
            Dictionary with connection status
        """
        if address:
            # Get status for a specific device
            connected = (
                address in self._connected_devices and
                self._connected_devices[address]
            )
            
            client = self._clients.get(address) if connected else None
            client_connected = client.is_connected if client else False
            
            connection_info = self._connection_info.get(address, {}) if connected else {}
            
            return {
                "address": address,
                "connected": connected and client_connected,
                "connection_info": connection_info
            }
        else:
            # Get status for all devices
            connected_devices = []
            
            for addr, connected in self._connected_devices.items():
                if connected:
                    client = self._clients.get(addr)
                    if client and client.is_connected:
                        connection_info = self._connection_info.get(addr, {})
                        device_info = self._discovered_devices.get(addr, {"address": addr})
                        
                        connected_devices.append({
                            "address": addr,
                            "name": device_info.get("name", "Unknown"),
                            "connected_at": connection_info.get("connected_at", 0),
                            "connection_time": connection_info.get("connection_time", 0)
                        })
            
            return {
                "connected_devices": connected_devices,
                "count": len(connected_devices)
            }
    
    async def clear_all_connections(self) -> Dict[str, Any]:
        """
        Disconnect from all connected devices.
        
        Returns:
            Dictionary with result
        """
        disconnected_devices = []
        errors = []
        
        # Get a copy of connected devices
        connected_addresses = [
            addr for addr, connected in self._connected_devices.items()
            if connected
        ]
        
        # Disconnect from each device
        for address in connected_addresses:
            try:
                result = await self.disconnect_from_device(address)
                if result.get("status") == ConnectionStatus.DISCONNECTED:
                    disconnected_devices.append(address)
            except Exception as e:
                self.logger.warning(f"Error disconnecting from {address}: {e}")
                errors.append({
                    "address": address,
                    "error": str(e)
                })
        
        # Reset all tracking
        self.client = None
        self._connected_devices = {}
        self._clients = {}
        self._connection_info = {}
        
        return {
            "disconnected_devices": disconnected_devices,
            "count": len(disconnected_devices),
            "errors": errors
        }
    
    # Event handlers
    async def _handle_disconnection(self, address: str, client: BleakClient) -> None:
        """Handle device disconnection."""
        self.logger.info(f"Device {address} disconnected")
        
        # Check if this was user requested
        disconnect_requested = (
            address in self._connection_info and
            self._connection_info[address].get("disconnect_requested", False)
        )
        
        # Update connection state
        self._connected_devices[address] = False
        
        if self.client == client:
            self.client = None
        
        # Emit event
        ble_event_bus.emit("device_disconnected", {
            "address": address,
            "reason": "user_requested" if disconnect_requested else "device_initiated"
        })
        
        # Check if we should auto-reconnect
        auto_reconnect = (
            not disconnect_requested and
            address in self._connection_info and
            self._connection_info[address].get("auto_reconnect", False)
        )
        
        if auto_reconnect:
            self.logger.info(f"Auto-reconnecting to {address}")
            
            # Emit event
            ble_event_bus.emit("reconnection_started", {
                "address": address
            })
            
            try:
                # Wait a moment before reconnecting
                await asyncio.sleep(1)
                
                # Try to reconnect
                result = await self.connect_to_device(
                    address,
                    ConnectionParams(auto_reconnect=True)
                )
                
                if result.get("status") == ConnectionStatus.CONNECTED:
                    self.logger.info(f"Auto-reconnected to {address}")
                else:
                    self.logger.warning(f"Auto-reconnect failed for {address}")
            except Exception as e:
                self.logger.error(f"Error during auto-reconnect to {address}: {e}")
    
    async def _handle_recovery_action(self, event_data: Dict[str, Any]) -> None:
        """Handle recovery action events."""
        action = event_data.get("action")
        address = event_data.get("device_address")
        
        if not action or not address:
            return
        
        self.logger.info(f"Handling recovery action: {action} for device {address}")
        
        if action == "retry_connection":
            # Try to reconnect
            try:
                # Wait a moment before reconnecting
                await asyncio.sleep(1)
                
                # Try to reconnect
                await self.connect_to_device(
                    address,
                    ConnectionParams(timeout=15.0)  # Longer timeout for recovery
                )
            except Exception as e:
                self.logger.error(f"Error during recovery connection to {address}: {e}")
        elif action == "reconnect":
            # First disconnect if connected
            try:
                if address in self._connected_devices and self._connected_devices[address]:
                    await self.disconnect_from_device(address)
                    await asyncio.sleep(1)
                
                # Try to reconnect
                await self.connect_to_device(
                    address,
                    ConnectionParams(timeout=15.0)  # Longer timeout for recovery
                )
            except Exception as e:
                self.logger.error(f"Error during recovery reconnection to {address}: {e}")
        
        # Add more recovery actions as needed
    
    async def _handle_adapter_reset(self, event_data: Dict[str, Any]) -> None:
        """Handle adapter reset events."""
        self.logger.info("Adapter reset detected, cleaning up connections")
        
        # Clean up all connections
        await self.clear_all_connections()
        
        # Clear discovered devices
        self._discovered_devices = {}

# Singleton instance (to be initialized on first use)
_device_manager = None

def get_device_manager() -> BleDeviceManager:
    """Get the singleton device manager instance."""
    global _device_manager
    if _device_manager is None:
        _device_manager = BleDeviceManager()
    return _device_manager