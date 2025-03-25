from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod

# Repository interface
class BleRepositoryInterface(ABC):
    """Interface for BLE repository implementations."""
    
    @abstractmethod
    async def scan_devices(self, timeout: int) -> List[Dict[str, Any]]:
        """Scan for BLE devices."""
        pass
    
    @abstractmethod
    async def connect_device(self, device_id: str) -> bool:
        """Connect to a BLE device."""
        pass
    
    @abstractmethod
    async def disconnect_device(self, device_id: str) -> bool:
        """Disconnect from a BLE device."""
        pass
    
    @abstractmethod
    async def get_device_info(self, device_id: str) -> Dict[str, Any]:
        """Get information about a connected device."""
        pass

# Service implementation
class BleService:
    """Service for BLE operations using repository pattern."""
    
    def __init__(self, repository: Optional[BleRepositoryInterface] = None, logger = None):
        """Initialize the BLE service.
        
        Args:
            repository: Repository for BLE device interactions
            logger: Logger for service operations
        """
        self.repository = repository
        self.logger = logger
    
    async def scan_for_devices(self, timeout: int = 10) -> List[Dict[str, Any]]:
        """Scan for available BLE devices.
        
        Args:
            timeout: The scan timeout in seconds
            
        Returns:
            List of device dictionaries with device information
        """
        if self.logger:
            self.logger.info(f"Scanning for BLE devices with timeout {timeout}s")
        
        if not self.repository:
            # Fallback implementation if no repository
            return []
        
        return await self.repository.scan_devices(timeout)
    
    async def connect_to_device(self, device_id: str) -> bool:
        """Connect to a specific BLE device.
        
        Args:
            device_id: The ID of the device to connect to
            
        Returns:
            True if connection successful, False otherwise
        """
        if self.logger:
            self.logger.info(f"Connecting to BLE device: {device_id}")
        
        if not self.repository:
            # Fallback implementation if no repository
            return False
        
        return await self.repository.connect_device(device_id)
    
    async def disconnect_from_device(self, device_id: str) -> bool:
        """Disconnect from a specific BLE device.
        
        Args:
            device_id: The ID of the device to disconnect from
            
        Returns:
            True if disconnection successful, False otherwise
        """
        if self.logger:
            self.logger.info(f"Disconnecting from BLE device: {device_id}")
        
        if not self.repository:
            # Fallback implementation if no repository
            return False
        
        return await self.repository.disconnect_device(device_id)
    
    async def get_device_details(self, device_id: str) -> Dict[str, Any]:
        """Get detailed information about a connected device.
        
        Args:
            device_id: The ID of the device to get information for
            
        Returns:
            Dictionary containing device details
        """
        if self.logger:
            self.logger.info(f"Getting details for BLE device: {device_id}")
        
        if not self.repository:
            # Fallback implementation if no repository
            return {"device_id": device_id, "status": "unknown"}
        
        return await self.repository.get_device_info(device_id)