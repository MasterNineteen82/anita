"""
High-level BLE service facade.

This module provides the main API entry point for the BLE module.
It coordinates the various manager classes to provide a unified interface.
"""

import logging
import asyncio
import time
from typing import Dict, Any, List, Optional, Union, Callable

from backend.modules.ble.utils.events import ble_event_bus
from backend.modules.ble.utils.ble_metrics import get_metrics_collector
from backend.modules.ble.utils.ble_recovery import get_error_recovery
from backend.modules.ble.utils.system_monitor import get_system_monitor
from backend.modules.ble.models import (
    BLEDeviceInfo, ScanParams, ConnectionParams, CharacteristicValue, 
    ConnectionStatus, MessageType
)
from .adapter_manager import get_adapter_manager
from .device_manager import get_device_manager
from .service_manager import BleServiceManager
from .notification_manager import BleNotificationManager
from .exceptions import (
    BleConnectionError, BleServiceError, BleAdapterError,
    BleOperationError, BleNotSupportedError
)

class BleService:
    """
    Main BLE service class.
    
    This class provides a high-level API for all BLE operations by coordinating
    the various specialized manager classes. It acts as a facade that simplifies
    the underlying complexity of BLE operations.
    """
    
    def __init__(self, logger=None):
        """
        Initialize the BLE service.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Get manager instances
        self.adapter_manager = get_adapter_manager()
        self.device_manager = get_device_manager()
        self.service_manager = BleServiceManager()
        self.notification_manager = BleNotificationManager()
        
        # Set up cross-references
        self.notification_manager.set_service_manager(self.service_manager)
        
        # Get utility instances
        self.metrics_collector = get_metrics_collector()
        self.error_recovery = get_error_recovery()
        self.system_monitor = get_system_monitor()
        
        # Set up event handlers
        ble_event_bus.on("device_connected", self._handle_device_connected)
        ble_event_bus.on("device_disconnected", self._handle_device_disconnected)
        
        self.logger.info("BLE service initialized")
    
    # ======================================================================
    # Adapter Management Methods
    # ======================================================================
    
    async def get_adapters(self) -> List[Dict[str, Any]]:
        """
        Get list of available Bluetooth adapters.
        
        Returns:
            List of adapter dictionaries
        """
        try:
            return await self.adapter_manager.discover_adapters()
        except Exception as e:
            self.logger.error(f"Error getting adapters: {e}", exc_info=True)
            raise BleAdapterError(f"Error getting adapters: {e}")
    
    async def select_adapter(self, adapter_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Select a specific Bluetooth adapter.
        
        Args:
            adapter_info: Dictionary with address or index of adapter to select
            
        Returns:
            Dictionary with selection result
        """
        try:
            return await self.adapter_manager.select_adapter(adapter_info)
        except Exception as e:
            self.logger.error(f"Error selecting adapter: {e}", exc_info=True)
            raise BleAdapterError(f"Error selecting adapter: {e}")
    
    async def get_adapter_status(self) -> Dict[str, Any]:
        """
        Get status of the current Bluetooth adapter.
        
        Returns:
            Dictionary with adapter status
        """
        try:
            return await self.adapter_manager.get_adapter_status()
        except Exception as e:
            self.logger.error(f"Error getting adapter status: {e}", exc_info=True)
            raise BleAdapterError(f"Error getting adapter status: {e}")
    
    async def reset_adapter(self, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Reset the Bluetooth adapter.
        
        Args:
            options: Optional dictionary with reset options
            
        Returns:
            Dictionary with reset result
        """
        try:
            return await self.adapter_manager.reset_adapter(options)
        except Exception as e:
            self.logger.error(f"Error resetting adapter: {e}", exc_info=True)
            raise BleAdapterError(f"Error resetting adapter: {e}")
    
    async def get_adapters(self):
        """Get all available BLE adapters.
        
        Returns:
            list: A list of adapter information dictionaries
        """
        try:
            # Check if we have a device manager with the method
            if hasattr(self, 'device_manager') and hasattr(self.device_manager, 'get_available_adapters'):
                return self.device_manager.get_available_adapters()
            
            # Fallback implementation
            if hasattr(self, 'ble_manager') and hasattr(self.ble_manager, 'get_adapters'):
                return self.ble_manager.get_adapters()
                
            # Last resort fallback
            return [{
                "id": "default",
                "name": "Default Adapter",
                "address": "00:00:00:00:00:00", 
                "available": True,
                "status": "active"
            }]
        except Exception as e:
            self.logger.error(f"Error getting adapters: {e}")
            # Return a minimal adapter list in case of error
            return [{
                "id": "default",
                "name": "Default Adapter (Error)",
                "address": "00:00:00:00:00:00",
                "available": False,
                "status": "error",
                "error": str(e)
            }]

    async def get_current_adapter(self):
        """Get the currently selected adapter.
        
        Returns:
            dict: Information about the current adapter
        """
        try:
            # Try to get from device manager
            if hasattr(self, 'device_manager') and hasattr(self.device_manager, 'get_current_adapter'):
                return self.device_manager.get_current_adapter()
                
            # Try to get from BLE manager
            if hasattr(self, 'ble_manager') and hasattr(self.ble_manager, 'get_current_adapter'):
                return self.ble_manager.get_current_adapter()
                
            # Fallback
            return {
                "id": "default",
                "name": "Default Adapter",
                "address": "00:00:00:00:00:00",
                "status": "active"
            }
        except Exception as e:
            self.logger.error(f"Error getting current adapter: {e}")
            return {
                "id": "unknown",
                "name": "Unknown Adapter",
                "status": "error",
                "error": str(e)
            }
    
    # ======================================================================
    # Device Discovery and Connection Methods
    # ======================================================================
    
    async def scan_devices(self, scan_time: float = 5.0, **kwargs) -> List[Dict[str, Any]]:
        """
        Scan for nearby BLE devices.
        
        Args:
            scan_time: Scan duration in seconds
            **kwargs: Additional scan parameters
            
        Returns:
            List of discovered devices
        """
        try:
            # Create scan parameters
            params = ScanParams(scan_time=scan_time, **kwargs)
            
            # Run the scan
            return await self.device_manager.scan_devices(params)
        except Exception as e:
            self.logger.error(f"Error scanning for devices: {e}", exc_info=True)
            raise BleOperationError(f"Error scanning for devices: {e}")
    
    async def connect_device(self, address: str, **kwargs) -> Dict[str, Any]:
        """
        Connect to a BLE device.
        
        Args:
            address: Device address
            **kwargs: Additional connection parameters
            
        Returns:
            Connection result dictionary
        """
        try:
            # Create connection parameters
            params = ConnectionParams(**kwargs)
            
            # Connect to the device
            result = await self.device_manager.connect_to_device(address, params)
            
            # If connected, set the client in service manager
            if result.get("status") == ConnectionStatus.CONNECTED:
                self.service_manager.set_client(self.device_manager.client)
            
            return result
        except Exception as e:
            self.logger.error(f"Error connecting to device: {e}", exc_info=True)
            raise BleConnectionError(f"Error connecting to device: {e}")
    
    async def disconnect_device(self, address: str) -> Dict[str, Any]:
        """
        Disconnect from a BLE device.
        
        Args:
            address: Device address
            
        Returns:
            Disconnection result dictionary
        """
        try:
            # Clear any notifications first
            if self.device_manager.client:
                await self.notification_manager.clear_all_subscriptions()
            
            # Disconnect from the device
            return await self.device_manager.disconnect_from_device(address)
        except Exception as e:
            self.logger.error(f"Error disconnecting from device: {e}", exc_info=True)
            raise BleConnectionError(f"Error disconnecting from device: {e}")
    
    async def get_connected_devices(self) -> Dict[str, Any]:
        """
        Get list of currently connected devices.
        
        Returns:
            Dictionary with connected devices
        """
        try:
            return self.device_manager.get_connection_status()
        except Exception as e:
            self.logger.error(f"Error getting connected devices: {e}", exc_info=True)
            raise BleOperationError(f"Error getting connected devices: {e}")
    
    async def get_saved_devices(self) -> List[Dict[str, Any]]:
        """
        Get list of previously saved/bonded devices.
        
        Returns:
            List of saved devices
        """
        try:
            return await self.device_manager.get_saved_devices()
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
            return await self.device_manager.remove_saved_device(address)
        except Exception as e:
            self.logger.error(f"Error removing saved device: {e}", exc_info=True)
            raise BleOperationError(f"Error removing saved device: {e}")
    
    # ======================================================================
    # GATT Service and Characteristic Methods
    # ======================================================================
    
    async def get_services(self) -> List[Dict[str, Any]]:
        """
        Get services from connected device.
        
        Returns:
            List of service dictionaries
        """
        try:
            return await self.service_manager.get_services()
        except Exception as e:
            self.logger.error(f"Error getting services: {e}", exc_info=True)
            raise BleServiceError(f"Error getting services: {e}")
    
    async def get_characteristics(self, service_uuid: str) -> List[Dict[str, Any]]:
        """
        Get characteristics for a service.
        
        Args:
            service_uuid: Service UUID
            
        Returns:
            List of characteristic dictionaries
        """
        try:
            return await self.service_manager.get_characteristics(service_uuid)
        except Exception as e:
            self.logger.error(f"Error getting characteristics: {e}", exc_info=True)
            raise BleServiceError(f"Error getting characteristics: {e}")
    
    async def read_characteristic(self, characteristic_uuid: str) -> Dict[str, Any]:
        """
        Read a characteristic value.
        
        Args:
            characteristic_uuid: Characteristic UUID
            
        Returns:
            Dictionary with characteristic value
        """
        try:
            value = await self.service_manager.read_characteristic(characteristic_uuid)
            return value.dict()
        except Exception as e:
            self.logger.error(f"Error reading characteristic: {e}", exc_info=True)
            
            # Try to recover
            await self.error_recovery.recover_from_error(
                "gatt_error",
                device_address=getattr(self.device_manager.client, "address", None),
                error_details={"message": str(e), "operation": "read", "characteristic_uuid": characteristic_uuid}
            )
            
            raise BleServiceError(f"Error reading characteristic: {e}")
    
    async def write_characteristic(
        self, 
        characteristic_uuid: str, 
        value: Union[str, bytes, bytearray, int],
        value_type: str = "hex",
        response: bool = True
    ) -> bool:
        """
        Write a value to a characteristic.
        
        Args:
            characteristic_uuid: Characteristic UUID
            value: Value to write
            value_type: Type of value (hex, text, bytes, int)
            response: Whether to wait for response
            
        Returns:
            True if successful
        """
        try:
            return await self.service_manager.write_characteristic(
                characteristic_uuid,
                value,
                value_type=value_type,
                response=response
            )
        except Exception as e:
            self.logger.error(f"Error writing characteristic: {e}", exc_info=True)
            
            # Try to recover
            await self.error_recovery.recover_from_error(
                "gatt_error",
                device_address=getattr(self.device_manager.client, "address", None),
                error_details={"message": str(e), "operation": "write", "characteristic_uuid": characteristic_uuid}
            )
            
            raise BleServiceError(f"Error writing characteristic: {e}")
    
    # ======================================================================
    # Notification Methods
    # ======================================================================
    
    async def subscribe_to_notifications(
        self, 
        characteristic_uuid: str,
        enable: bool = True
    ) -> bool:
        """
        Subscribe to notifications for a characteristic.
        
        Args:
            characteristic_uuid: Characteristic UUID
            enable: Whether to enable (True) or disable (False) notifications
            
        Returns:
            True if successful
        """
        try:
            return await self.notification_manager.subscribe_to_characteristic(
                characteristic_uuid, enable
            )
        except Exception as e:
            self.logger.error(f"Error subscribing to notifications: {e}", exc_info=True)
            
            # Try to recover
            await self.error_recovery.recover_from_error(
                "gatt_error",
                device_address=getattr(self.device_manager.client, "address", None),
                error_details={
                    "message": str(e), 
                    "operation": "subscribe", 
                    "characteristic_uuid": characteristic_uuid
                }
            )
            
            raise BleServiceError(f"Error subscribing to notifications: {e}")
    
    async def get_notification_history(
        self, 
        characteristic_uuid: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get notification history.
        
        Args:
            characteristic_uuid: Optional characteristic UUID filter
            limit: Maximum number of notifications to return
            
        Returns:
            Dictionary with notification history
        """
        try:
            return self.notification_manager.get_notification_history(
                characteristic_uuid, limit
            )
        except Exception as e:
            self.logger.error(f"Error getting notification history: {e}", exc_info=True)
            raise BleOperationError(f"Error getting notification history: {e}")
    
    async def clear_notification_history(
        self, 
        characteristic_uuid: Optional[str] = None
    ) -> None:
        """
        Clear notification history.
        
        Args:
            characteristic_uuid: Optional characteristic UUID filter
        """
        try:
            self.notification_manager.clear_notification_history(characteristic_uuid)
        except Exception as e:
            self.logger.error(f"Error clearing notification history: {e}", exc_info=True)
            raise BleOperationError(f"Error clearing notification history: {e}")
    
    # ======================================================================
    # System and Health Methods
    # ======================================================================
    
    async def get_system_health(self) -> Dict[str, Any]:
        """
        Get system health information.
        
        Returns:
            Dictionary with system health information
        """
        try:
            # Get adapter status
            adapter_status = await self.adapter_manager.get_adapter_status()
            
            # Get system diagnostics
            diagnostics = await self.system_monitor.run_diagnostics()
            
            # Get metrics
            metrics = self.metrics_collector.get_metrics()
            
            # Create health report
            health_report = {
                "timestamp": time.time(),
                "adapter_status": adapter_status,
                "system_diagnostics": diagnostics,
                "ble_metrics": metrics,
            }
            
            return health_report
        except Exception as e:
            self.logger.error(f"Error getting system health: {e}", exc_info=True)
            raise BleOperationError(f"Error getting system health: {e}")
    
    async def diagnose_connection_issues(
        self, 
        device_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Diagnose connection issues.
        
        Args:
            device_address: Optional device address
            
        Returns:
            Dictionary with diagnostic information
        """
        try:
            return await self.error_recovery.diagnose_connection_issues(device_address)
        except Exception as e:
            self.logger.error(f"Error diagnosing connection issues: {e}", exc_info=True)
            raise BleOperationError(f"Error diagnosing connection issues: {e}")
    
    async def perform_automatic_recovery(
        self, 
        error_type: str,
        device_address: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform automatic recovery for a BLE error.
        
        Args:
            error_type: Type of error
            device_address: Optional device address
            error_details: Optional error details
            
        Returns:
            Dictionary with recovery result
        """
        try:
            return await self.error_recovery.recover_from_error(
                error_type, device_address, error_details
            )
        except Exception as e:
            self.logger.error(f"Error performing recovery: {e}", exc_info=True)
            raise BleOperationError(f"Error performing recovery: {e}")
    
    # ======================================================================
    # Event Handlers
    # ======================================================================
    
    async def _handle_device_connected(self, event_data: Dict[str, Any]) -> None:
        """Handle device connected event."""
        address = event_data.get("address")
        if address:
            # Make sure the service manager has the client
            self.service_manager.set_client(self.device_manager.client)
    
    async def _handle_device_disconnected(self, event_data: Dict[str, Any]) -> None:
        """Handle device disconnected event."""
        # Clear any subscriptions
        await self.notification_manager.clear_all_subscriptions()
    
    # ======================================================================
    # Utility Methods
    # ======================================================================
    
    async def cleanup(self) -> None:
        """
        Clean up resources.
        
        This should be called when the application is shutting down.
        """
        try:
            # Disconnect from all devices
            await self.device_manager.clear_all_connections()
            
            # Clear notification subscriptions
            await self.notification_manager.clear_all_subscriptions()
            
            self.logger.info("BLE service cleaned up")
        except Exception as e:
            self.logger.error(f"Error cleaning up BLE service: {e}", exc_info=True)

# Singleton instance (to be initialized on first use)
_ble_service = None

def get_ble_service() -> BleService:
    """Get the singleton BLE service instance."""
    global _ble_service
    if _ble_service is None:
        _ble_service = BleService()
    return _ble_service
