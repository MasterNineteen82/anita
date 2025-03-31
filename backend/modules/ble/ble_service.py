"""
Re-export of the BLE Service from core module.
This file ensures backward compatibility with existing import patterns.
"""

"""BLE service implementation."""

import logging
from typing import Optional, Dict, List, Any

from backend.modules.ble.ble_manager import BLEManager

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
    
    # Add other methods as needed...

# Re-export BleService and get_ble_service from core implementation
from backend.modules.ble.core.ble_service import BleService, get_ble_service

# Ensure these are included in __all__ for proper importing
__all__ = ['BleService', 'get_ble_service']