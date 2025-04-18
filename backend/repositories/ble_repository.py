import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class BLERepository:
    """Repository for BLE devices and interactions."""
    
    def __init__(self):
        self.devices = {}
        self.scan_results = {}
        self.scan_id_counter = 0
        self.active_connections = {}
        
    async def start_scan(self, scan_time: int = 5, active: bool = True, 
                   name_prefix: Optional[str] = None, service_uuids: Optional[List[str]] = None) -> str:
        """
        Start a BLE scan with the given parameters.
        
        Args:
            scan_time: Duration of scan in seconds
            active: Whether to perform an active scan
            name_prefix: Filter for device name prefix
            service_uuids: Filter for service UUIDs
            
        Returns:
            Scan ID for retrieving results
        """
        scan_id = str(self.scan_id_counter)
        self.scan_id_counter += 1
        
        # Store scan configuration (would trigger actual scan in real implementation)
        self.scan_results[scan_id] = {
            "status": "completed",  # For demo purposes we'll say it completed instantly
            "config": {
                "scan_time": scan_time,
                "active": active,
                "name_prefix": name_prefix,
                "service_uuids": service_uuids
            },
            "devices": self._get_mock_devices()  # Mock devices for testing
        }
        
        logger.info(f"Started BLE scan with ID {scan_id}")
        return scan_id
        
    async def get_discovered_devices(self, scan_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get devices discovered in a previous scan.
        
        Args:
            scan_id: ID of the scan to retrieve results for
            
        Returns:
            List of discovered devices
        """
        if scan_id is not None and scan_id in self.scan_results:
            return self.scan_results[scan_id]["devices"]
        
        # Return mock devices if scan_id not found
        return self._get_mock_devices()
        
    async def connect_device(self, device_id: str) -> bool:
        """
        Connect to a BLE device.
        
        Args:
            device_id: Device ID to connect to
            
        Returns:
            True if connection successful
        """
        if device_id in self.active_connections:
            return True  # Already connected
            
        # Simulate connection success (would do actual connection in real impl)
        self.active_connections[device_id] = {
            "status": "connected",
            "services": self._get_mock_services(device_id)
        }
        
        logger.info(f"Connected to BLE device {device_id}")
        return True
        
    async def disconnect_device(self, device_id: str) -> bool:
        """
        Disconnect from a BLE device.
        
        Args:
            device_id: Device ID to disconnect from
            
        Returns:
            True if disconnection successful
        """
        if device_id in self.active_connections:
            del self.active_connections[device_id]
            logger.info(f"Disconnected from BLE device {device_id}")
            return True
            
        # Not connected
        return False
        
    async def get_device_services(self, device_id: str) -> List[Dict[str, Any]]:
        """
        Get services for a connected device.
        
        Args:
            device_id: Device ID
            
        Returns:
            List of service information
        """
        if device_id in self.active_connections:
            return self.active_connections[device_id]["services"]
            
        return []
        
    async def read_characteristic(self, device_id: str, service_uuid: str, 
                             characteristic_uuid: str) -> Dict[str, Any]:
        """
        Read a characteristic value.
        
        Args:
            device_id: Device ID
            service_uuid: Service UUID
            characteristic_uuid: Characteristic UUID
            
        Returns:
            Characteristic value
        """
        # Mock read operation
        return {
            "value": "0x1234",
            "encoding": "hex"
        }
        
    async def write_characteristic(self, device_id: str, service_uuid: str, 
                              characteristic_uuid: str, value: Any) -> bool:
        """
        Write a value to a characteristic.
        
        Args:
            device_id: Device ID
            service_uuid: Service UUID
            characteristic_uuid: Characteristic UUID
            value: Value to write
            
        Returns:
            True if write successful
        """
        # Mock write operation
        logger.info(f"Write value {value} to {device_id}/{service_uuid}/{characteristic_uuid}")
        return True
        
    async def subscribe_characteristic(self, device_id: str, service_uuid: str,
                                  characteristic_uuid: str) -> bool:
        """
        Subscribe to notifications from a characteristic.
        
        Args:
            device_id: Device ID
            service_uuid: Service UUID
            characteristic_uuid: Characteristic UUID
            
        Returns:
            True if subscription successful
        """
        # Mock subscription
        logger.info(f"Subscribed to {device_id}/{service_uuid}/{characteristic_uuid}")
        return True
        
    def _get_mock_devices(self) -> List[Dict[str, Any]]:
        """Get mock devices for testing."""
        return [
            {
                "id": "00:11:22:33:44:55",
                "name": "BLE Test Device 1",
                "address": "00:11:22:33:44:55",
                "rssi": -65,
                "connectable": True
            },
            {
                "id": "AA:BB:CC:DD:EE:FF",
                "name": "BLE Test Device 2",
                "address": "AA:BB:CC:DD:EE:FF",
                "rssi": -78,
                "connectable": True
            }
        ]
        
    def _get_mock_services(self, device_id: str) -> List[Dict[str, Any]]:
        """Get mock services for testing."""
        return [
            {
                "uuid": "1800",
                "name": "Generic Access",
                "characteristics": [
                    {
                        "uuid": "2A00",
                        "name": "Device Name",
                        "properties": ["read"]
                    }
                ]
            },
            {
                "uuid": "180F",
                "name": "Battery Service",
                "characteristics": [
                    {
                        "uuid": "2A19",
                        "name": "Battery Level",
                        "properties": ["read", "notify"]
                    }
                ]
            }
        ]
