import time
import threading
import logging
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Optional, Union
from enum import Enum

# Import centralized models
from backend.models import (
    UWBAnchor, UWBPosition, UWBRangingResult,
    SuccessResponse, ErrorResponse
)

# Configure logging
logger = logging.getLogger(__name__)

# Define UWBMode Enum
class UWBMode(str, Enum):
    ANCHOR = "anchor"
    TAG = "tag"

# Determine if UWB hardware is available (replace with actual check)
UWB_HARDWARE_AVAILABLE = os.environ.get('UWB_HARDWARE', 'False').lower() == 'true'

# Simulation mode
SIMULATION_MODE = os.environ.get('SIMULATION_MODE', 'False').lower() == 'true'

class UWBDevice:
    def __init__(self, device_id: str, device_type: UWBMode, location: Optional[UWBPosition] = None):
        self.device_id = device_id
        self.device_type = device_type
        self.location = location
        self.last_seen = None
        self.lock = threading.Lock()

    def update_location(self, new_location: UWBPosition):
        self.location = new_location
        self.last_seen = time.time()

    def get_location(self) -> Optional[UWBPosition]:
        with self.lock:
            return self.location

    def get_last_seen(self) -> Optional[float]:
        with self.lock:
            return self.last_seen

    def __repr__(self):
        return f"UWBDevice(id={self.device_id}, type={self.device_type}, location={self.location}, last_seen={self.last_seen})"

class UWBManager:
    """Manager for Ultra-Wideband (UWB) positioning operations"""
    
    # Class variables
    executor = ThreadPoolExecutor()
    _anchors = {}  # Known UWB anchors
    _tags = {}  # Tracked UWB tags
    _devices: Dict[str, UWBDevice] = {}
    _lock = threading.Lock()

    @classmethod
    async def register_device(cls, device_id: str, device_type: UWBMode) -> SuccessResponse:
        """Register a new UWB device."""
        logger.info(f"Registering UWB device: {device_id} as type {device_type}")
        with cls._lock:
            if device_id not in cls._devices:
                cls._devices[device_id] = UWBDevice(device_id, device_type)
                return SuccessResponse(
                    status="success",
                    message=f"Device {device_id} registered as {device_type}."
                )
            else:
                return ErrorResponse(
                    status="error",
                    message=f"Device {device_id} already registered."
                )

    @classmethod
    async def update_device_location(cls, device_id: str, location: UWBPosition) -> SuccessResponse:
        """Update the location of a UWB device."""
        logger.info(f"Updating location of UWB device: {device_id} to {location}")
        with cls._lock:
            if device_id in cls._devices:
                cls._devices[device_id].update_location(location)
                return SuccessResponse(
                    status="success",
                    message=f"Device {device_id} location updated to {location}."
                )
            else:
                return ErrorResponse(
                    status="error",
                    message=f"Device {device_id} not registered."
                )

    @classmethod
    async def get_device_location(cls, device_id: str) -> SuccessResponse:
        """Get the location of a UWB device."""
        logger.info(f"Getting location of UWB device: {device_id}")
        with cls._lock:
            if device_id in cls._devices:
                device = cls._devices[device_id]
                location = device.get_location()
                if location:
                    return SuccessResponse(
                        status="success",
                        message=f"Location of device {device_id} retrieved.",
                        data=location.dict()
                    )
                else:
                    return ErrorResponse(
                        status="warning",
                        message=f"Location for device {device_id} not yet set."
                    )
            else:
                return ErrorResponse(
                    status="error",
                    message=f"Device {device_id} not registered."
                )

    @classmethod
    async def get_all_devices(cls) -> SuccessResponse:
        """Get a list of all registered UWB devices."""
        logger.info("Getting all UWB devices.")
        with cls._lock:
            devices = list(cls._devices.values())
            device_list = [
                {"device_id": d.device_id, "device_type": d.device_type, "location": d.location.dict() if d.location else None, "last_seen": d.last_seen}
                for d in devices
            ]
            return SuccessResponse(
                status="success",
                message="List of all devices retrieved.",
                data=device_list
            )

    @classmethod
    async def remove_device(cls, device_id: str) -> SuccessResponse:
        """Remove a UWB device."""
        logger.info(f"Removing UWB device: {device_id}")
        with cls._lock:
            if device_id in cls._devices:
                del cls._devices[device_id]
                return SuccessResponse(
                    status="success",
                    message=f"Device {device_id} removed."
                )
            else:
                return ErrorResponse(
                    status="error",
                    message=f"Device {device_id} not registered."
                )

    @classmethod
    async def add_anchor(cls, anchor: UWBAnchor) -> SuccessResponse:
        """
        Add a new UWB anchor
        
        Args:
            anchor: UWBAnchor object containing anchor information
            
        Returns:
            SuccessResponse with the result
        """
        logger.info(f"Adding new UWB anchor: {anchor.anchor_id}")
        
        if SIMULATION_MODE:
            cls._anchors[anchor.anchor_id] = anchor
            return SuccessResponse(
                status="success",
                message="UWB anchor added successfully (simulated)",
                data={'anchor_id': anchor.anchor_id}
            )
        
        if not UWB_HARDWARE_AVAILABLE:
            return ErrorResponse(
                status="error",
                message="UWB hardware not available"
            )
            
        try:
            # Execute anchor addition in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                cls.executor, 
                lambda: cls._add_anchor_sync(anchor)
            )
            return result
                
        except Exception as e:
            logger.exception("Error adding UWB anchor: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f"Failed to add UWB anchor: {str(e)}"
            )
    
    @classmethod
    def _add_anchor_sync(cls, anchor: UWBAnchor) -> SuccessResponse:
        """Synchronous method to add a UWB anchor"""
        try:
            # In a real implementation, this would configure the UWB hardware
            # to recognize the new anchor
            
            # For now, we'll just store the anchor in memory
            cls._anchors[anchor.anchor_id] = anchor
            
            return SuccessResponse(
                status="success",
                message="UWB anchor added successfully",
                data={'anchor_id': anchor.anchor_id}
            )
                
        except Exception as e:
            logger.exception("Error in synchronous UWB anchor addition: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f"UWB anchor addition error: {str(e)}"
            )
    
    @classmethod
    async def get_position(cls, tag_id: str) -> SuccessResponse:
        """
        Get the current position of a UWB tag
        
        Args:
            tag_id: ID of the UWB tag
            
        Returns:
            SuccessResponse with the UWBPosition data
        """
        logger.info(f"Getting position for UWB tag: {tag_id}")
        
        if SIMULATION_MODE:
            # Simulate position data
            position = UWBPosition(
                x=1.0,
                y=2.0,
                z=0.5,
                timestamp=time.time()
            )
            return SuccessResponse(
                status="success",
                message="UWB position retrieved successfully (simulated)",
                data=position.dict()
            )
        
        if not UWB_HARDWARE_AVAILABLE:
            return ErrorResponse(
                status="error",
                message="UWB hardware not available"
            )
            
        try:
            # Execute position retrieval in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                cls.executor, 
                lambda: cls._get_position_sync(tag_id)
            )
            return result
                
        except Exception as e:
            logger.exception("Error getting UWB position: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f"Failed to get UWB position: {str(e)}"
            )
    
    @classmethod
    def _get_position_sync(cls, tag_id: str) -> SuccessResponse:
        """Synchronous method to get the current position of a UWB tag"""
        try:
            # In a real implementation, this would use UWB ranging data
            # from multiple anchors to calculate the tag's position
            
            # For now, we'll simulate position data
            position = UWBPosition(
                x=1.0,
                y=2.0,
                z=0.5,
                timestamp=time.time()
            )
            
            return SuccessResponse(
                status="success",
                message="UWB position retrieved successfully",
                data=position.dict()
            )
                
        except Exception as e:
            logger.exception("Error in synchronous UWB position retrieval: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f"UWB position retrieval error: {str(e)}"
            )
    
    @classmethod
    async def get_ranging(cls, anchor_id: str, tag_id: str) -> SuccessResponse:
        """
        Get the ranging data between a UWB anchor and a tag
        
        Args:
            anchor_id: ID of the UWB anchor
            tag_id: ID of the UWB tag
            
        Returns:
            SuccessResponse with the UWBRangingResult data
        """
        logger.info(f"Getting ranging data between anchor {anchor_id} and tag {tag_id}")
        
        if SIMULATION_MODE:
            # Simulate ranging data
            ranging_result = UWBRangingResult(
                anchor_id=anchor_id,
                tag_id=tag_id,
                distance=5.0,
                timestamp=time.time()
            )
            return SuccessResponse(
                status="success",
                message="UWB ranging data retrieved successfully (simulated)",
                data=ranging_result.dict()
            )
        
        if not UWB_HARDWARE_AVAILABLE:
            return ErrorResponse(
                status="error",
                message="UWB hardware not available"
            )
            
        try:
            # Execute ranging retrieval in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                cls.executor, 
                lambda: cls._get_ranging_sync(anchor_id, tag_id)
            )
            return result
                
        except Exception as e:
            logger.exception("Error getting UWB ranging data: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f"Failed to get UWB ranging data: {str(e)}"
            )
    
    @classmethod
    def _get_ranging_sync(cls, anchor_id: str, tag_id: str) -> SuccessResponse:
        """Synchronous method to get the ranging data between a UWB anchor and a tag"""
        try:
            # In a real implementation, this would query the UWB hardware
            # to get the distance between the anchor and the tag
            
            # For now, we'll simulate ranging data
            ranging_result = UWBRangingResult(
                anchor_id=anchor_id,
                tag_id=tag_id,
                distance=5.0,
                timestamp=time.time()
            )
            
            return SuccessResponse(
                status="success",
                message="UWB ranging data retrieved successfully",
                data=ranging_result.dict()
            )
                
        except Exception as e:
            logger.exception("Error in synchronous UWB ranging retrieval: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f"UWB ranging retrieval error: {str(e)}"
            )

# Example Usage (can be placed in a separate main.py or test file)
if __name__ == "__main__":
    async def main():
        # Register some devices
        await UWBManager.register_device("UWB001", UWBMode.TAG)
        await UWBManager.register_device("UWB002", UWBMode.ANCHOR)

        # Update device locations
        pos1 = UWBPosition(x=1.0, y=2.0, z=3.0, timestamp=time.time())
        await UWBManager.update_device_location("UWB001", pos1)
        pos2 = UWBPosition(x=4.0, y=5.0, z=6.0, timestamp=time.time())
        await UWBManager.update_device_location("UWB002", pos2)

        # Get device locations
        loc1_result = await UWBManager.get_device_location("UWB001")
        if loc1_result.status == "success":
            print(f"Location of UWB001: {loc1_result.data}")

        loc2_result = await UWBManager.get_device_location("UWB002")
        if loc2_result.status == "success":
            print(f"Location of UWB002: {loc2_result.data}")

        # List all devices
        all_devices_result = await UWBManager.get_all_devices()
        if all_devices_result.status == "success":
            print("All devices:", all_devices_result.data)

        # Remove a device
        await UWBManager.remove_device("UWB001")

        # Try to get the location of the removed device
        loc1_result = await UWBManager.get_device_location("UWB001")
        print(f"Location of UWB001: {loc1_result.message}") # This will print "Device UWB001 not registered."

    asyncio.run(main())