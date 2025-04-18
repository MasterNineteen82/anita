import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class UWBRepository:
    """Repository for UWB devices and position tracking."""
    
    def __init__(self):
        self.devices = {}
        self.location_history = {}
        self.active_tracking = set()
        
    async def register_device(self, device_id: str, 
                          initial_location: Dict[str, float] = None) -> bool:
        """
        Register a new UWB device.
        
        Args:
            device_id: Unique identifier for the device
            initial_location: Optional initial location (x, y, z)
            
        Returns:
            True if registration successful
        """
        if not initial_location:
            initial_location = {"x": 0.0, "y": 0.0, "z": 0.0}
            
        # Add the device
        self.devices[device_id] = {
            "device_id": device_id,
            "registered_at": datetime.now().isoformat(),
            "current_location": initial_location,
            "status": "active"
        }
        
        # Initialize location history
        self.location_history[device_id] = [
            {
                "timestamp": datetime.now().isoformat(),
                "location": initial_location
            }
        ]
        
        logger.info(f"Registered UWB device {device_id}")
        return True
        
    async def get_active_devices(self) -> List[Dict[str, Any]]:
        """
        Get list of active UWB devices.
        
        Returns:
            List of active device information
        """
        return [device for device in self.devices.values() 
                if device["status"] == "active"]
                
    async def get_device_location(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current location for a UWB device.
        
        Args:
            device_id: Device ID to get location for
            
        Returns:
            Current location information or None if not found
        """
        if device_id not in self.devices:
            return None
            
        device = self.devices[device_id]
        return {
            "device_id": device_id,
            "location": device["current_location"],
            "timestamp": datetime.now().isoformat()
        }
        
    async def start_tracking(self, device_id: str) -> bool:
        """
        Start position tracking for a device.
        
        Args:
            device_id: Device ID to track
            
        Returns:
            True if tracking started successfully
        """
        if device_id not in self.devices:
            return False
            
        self.active_tracking.add(device_id)
        logger.info(f"Started tracking UWB device {device_id}")
        return True
        
    async def stop_tracking(self, device_id: str) -> bool:
        """
        Stop position tracking for a device.
        
        Args:
            device_id: Device ID to stop tracking
            
        Returns:
            True if tracking stopped successfully
        """
        if device_id in self.active_tracking:
            self.active_tracking.remove(device_id)
            logger.info(f"Stopped tracking UWB device {device_id}")
            return True
            
        return False
        
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
        if device_id not in self.location_history:
            return []
            
        # Return most recent entries first
        return list(reversed(self.location_history[device_id]))[:limit]
        
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
        if device_id not in self.devices:
            return False
            
        # Update current location
        self.devices[device_id]["current_location"] = location
        
        # Add to history
        self.location_history[device_id].append({
            "timestamp": datetime.now().isoformat(),
            "location": location
        })
        
        # Limit history size
        if len(self.location_history[device_id]) > 100:
            self.location_history[device_id] = self.location_history[device_id][-100:]
            
        return True
        
    def get_mock_devices(self) -> List[Dict[str, Any]]:
        """Get mock devices for testing."""
        if not self.devices:
            # Create some sample devices
            self.register_device("uwb-001", {"x": 1.2, "y": 3.4, "z": 0.0})
            self.register_device("uwb-002", {"x": 5.6, "y": 7.8, "z": 0.0})
            self.register_device("uwb-003", {"x": 9.0, "y": 2.1, "z": 0.0})
            
        return list(self.devices.values())
