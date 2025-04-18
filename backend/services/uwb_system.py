import logging
from typing import Dict, List, Optional, Any

from backend.repositories.uwb_repository import UWBRepository

logger = logging.getLogger(__name__)

class UWBSystem:
    """Service for UWB operations and position tracking."""
    
    def __init__(self):
        self.repository = UWBRepository()
        
    async def register_device(self, device_id: str, 
                          initial_location: Optional[Dict[str, float]] = None) -> bool:
        """
        Register a new UWB device.
        
        Args:
            device_id: Unique identifier for the device
            initial_location: Optional initial location (x, y, z)
            
        Returns:
            True if registration successful
        """
        return await self.repository.register_device(device_id, initial_location)
        
    async def get_active_devices(self) -> List[Dict[str, Any]]:
        """
        Get list of active UWB devices.
        
        Returns:
            List of active device information
        """
        return await self.repository.get_active_devices()
        
    async def get_device_location(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current location for a UWB device.
        
        Args:
            device_id: Device ID to get location for
            
        Returns:
            Current location information or None if not found
        """
        return await self.repository.get_device_location(device_id)
        
    async def start_tracking(self, device_ids: List[str] = None) -> Dict[str, bool]:
        """
        Start position tracking for devices.
        
        Args:
            device_ids: List of device IDs to track, or None for all devices
            
        Returns:
            Dictionary of device IDs to success status
        """
        if device_ids is None:
            # Get all active devices
            devices = await self.repository.get_active_devices()
            device_ids = [d["device_id"] for d in devices]
            
        results = {}
        for device_id in device_ids:
            results[device_id] = await self.repository.start_tracking(device_id)
            
        return results
        
    async def stop_tracking(self, device_ids: List[str] = None) -> Dict[str, bool]:
        """
        Stop position tracking for devices.
        
        Args:
            device_ids: List of device IDs to stop tracking, or None for all tracking
            
        Returns:
            Dictionary of device IDs to success status
        """
        if device_ids is None:
            # Get all active devices
            devices = await self.repository.get_active_devices()
            device_ids = [d["device_id"] for d in devices]
            
        results = {}
        for device_id in device_ids:
            results[device_id] = await self.repository.stop_tracking(device_id)
            
        return results
        
    async def get_location_history(self, device_id: str, 
                               limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get location history for a device.
        
        Args:
            device_id: Device ID to get history for
            limit: Maximum number of history entries to return
            
        Returns:
            List of location history entries
        """
        return await self.repository.get_location_history(device_id, limit)
        
    async def update_device_location(self, device_id: str, 
                                location: Dict[str, float]) -> bool:
        """
        Update location for a device.
        
        Args:
            device_id: Device ID to update
            location: New location (x, y, z)
            
        Returns:
            True if update successful
        """
        return await self.repository.update_device_location(device_id, location)
