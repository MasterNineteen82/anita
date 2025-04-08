import logging
from typing import Optional, Dict, List, Any

from backend.modules.ble.ble_manager import BLEManager
from backend.modules.ble.core.ble_service import BleService 
from backend.modules.ble.core.ble_service_factory import get_ble_service


"""
Re-export of the BLE Service from core module.
This file ensures backward compatibility with existing import patterns.
"""

"""BLE service implementation."""


logger = logging.getLogger(__name__)

class BleService:
    """Service for BLE operations."""
    
    def __init__(self, ble_manager: BLEManager):
        """
        Initialize the BLE service.
        
        Args:
            ble_manager: The BLE manager instance
        """
        self.ble_manager = ble_manager
        self._initialized = False
        logger.info("BLE service created")
    
    async def initialize(self):
        """
        Perform async initialization tasks.
        This should be called after construction.
        """
        if self._initialized:
            return
            
        # Perform any async initialization here
        logger.info("Initializing BLE service")
        # Example: await self.ble_manager.discover_adapters()
        
        self._initialized = True
        logger.info("BLE service initialized")
        
    async def get_devices(self) -> List[Dict[str, Any]]:
        """
        Get a list of available BLE devices.
        
        Returns:
            List of device dictionaries
        """
        if not self._initialized:
            await self.initialize()
            
        # Implementation...
        return await self.ble_manager.get_discovered_devices()
    
    async def get_adapters(self):
        """Get all available BLE adapters with fallback implementation."""
        try:
            # Try the device manager first
            if hasattr(self, 'device_manager') and self.device_manager:
                if hasattr(self.device_manager, 'get_available_adapters'):
                    self.logger.debug("Using device_manager.get_available_adapters()")
                    return self.device_manager.get_available_adapters()
                    
            # Try BLE manager next
            if hasattr(self, 'ble_manager') and self.ble_manager:
                if hasattr(self.ble_manager, 'get_adapters'):
                    self.logger.debug("Using ble_manager.get_adapters()")
                    return self.ble_manager.get_adapters()
                    
                # Try older method names
                if hasattr(self.ble_manager, 'get_adapter_list'):
                    self.logger.debug("Using ble_manager.get_adapter_list()")
                    return self.ble_manager.get_adapter_list()
                    
            # If all else fails, create a minimal implementation
            self.logger.warning("No adapter methods found, using fallback implementation")
            import platform
            
            # On Windows, provide a Windows-specific adapter
            if platform.system() == "Windows":
                return [{
                    "id": "win-default",
                    "name": f"Windows Bluetooth Adapter ({platform.release()})",
                    "address": "00:00:00:00:00:00",
                    "available": True,
                    "status": "available",
                    "platform": "windows"
                }]
            # On Linux, provide a Linux-specific adapter
            elif platform.system() == "Linux":
                return [{
                    "id": "linux-default",
                    "name": f"Linux Bluetooth Adapter ({platform.release()})",
                    "address": "00:00:00:00:00:00", 
                    "available": True,
                    "status": "available",
                    "platform": "linux"
                }]
            # Generic fallback
            else:
                return [{
                    "id": "default",
                    "name": f"Default Bluetooth Adapter ({platform.system()})",
                    "address": "00:00:00:00:00:00",
                    "available": True,
                    "status": "available", 
                    "platform": platform.system().lower()
                }]
        except Exception as e:
            self.logger.error(f"Error in get_adapters fallback: {e}")
            return [{
                "id": "error",
                "name": "Error Adapter",
                "address": "00:00:00:00:00:00",
                "available": False,
                "status": "error",
                "error": str(e)
            }]

    async def get_current_adapter(self):
        """Get the currently selected adapter with fallback implementation."""
        try:
            # Try the device manager first
            if hasattr(self, 'device_manager') and self.device_manager:
                if hasattr(self.device_manager, 'get_current_adapter'):
                    return self.device_manager.get_current_adapter()
                    
            # Try BLE manager next
            if hasattr(self, 'ble_manager') and self.ble_manager:
                if hasattr(self.ble_manager, 'get_current_adapter'):
                    return self.ble_manager.get_current_adapter()
                    
            # If methods above don't exist or fail, just return the first adapter
            adapters = await self.get_adapters()
            return adapters[0] if adapters else {
                "id": "unknown",
                "name": "Unknown Adapter",
                "status": "unknown"
            }
        except Exception as e:
            self.logger.error(f"Error in get_current_adapter fallback: {e}")
            return {
                "id": "error",
                "name": "Error Adapter",
                "status": "error",
                "error": str(e)
            }


# Ensure these are included in __all__ for proper importing
__all__ = ['BleService', 'get_ble_service']