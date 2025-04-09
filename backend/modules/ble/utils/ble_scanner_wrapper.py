"""
Bluetooth Low Energy Scanner Wrapper.
Provides a thread-safe wrapper around BleakScanner to handle platform-specific issues.
"""
import asyncio
import logging
import platform
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional, Any, Set

# Import necessary BLE libraries
try:
    from bleak import BleakScanner, BleakError
    from bleak.backends.device import BLEDevice
    import binascii
except ImportError:
    logging.error("Bleak package not found. Please install with 'pip install bleak'")
    raise

logger = logging.getLogger(__name__)

class BLEScannerWrapper:
    """
    Thread-safe wrapper for BleakScanner that works around platform-specific issues.
    """
    
    def __init__(self):
        self.system = platform.system()
        self.logger = logging.getLogger(__name__)
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._scan_lock = threading.Lock()
        self._cached_devices = []
    
    async def discover_devices(
        self,
        timeout: float = 5.0,
        service_uuids: Optional[List[str]] = None,
        active: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Discover BLE devices using a platform-specific approach.
        
        Args:
            timeout: Scan duration in seconds
            service_uuids: Optional list of service UUIDs to filter by
            active: Whether to use active scanning
            
        Returns:
            List of device dictionaries
        """
        if self.system == "Windows":
            return await self._discover_windows(timeout, service_uuids, active)
        else:
            # For non-Windows platforms, use standard BleakScanner
            return await self._discover_standard(timeout, service_uuids, active)
    
    async def _discover_standard(
        self,
        timeout: float,
        service_uuids: Optional[List[str]],
        active: bool
    ) -> List[Dict[str, Any]]:
        """Standard discovery method for non-Windows platforms."""
        try:
            self.logger.info(f"Starting BLE scan (standard method) for {timeout}s")
            devices = await BleakScanner.discover(
                timeout=timeout,
                service_uuids=service_uuids,
                scanning_mode="active" if active else "passive",
            )
            return self._process_devices(devices)
        except BleakError as e:
            self.logger.error(f"BLE scan failed: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error in BLE scan: {e}")
            return []
    
    async def _discover_windows(
        self,
        timeout: float,
        service_uuids: Optional[List[str]],
        active: bool
    ) -> List[Dict[str, Any]]:
        """
        Windows-specific discovery method that works around thread issues.
        Uses a dedicated thread to avoid GUI thread conflicts.
        """
        try:
            self.logger.info(f"Starting BLE scan (Windows method) for {timeout}s")
            
            # First try the standard method - it might work depending on the environment
            try:
                devices = await BleakScanner.discover(
                    timeout=timeout,
                    service_uuids=service_uuids,
                    scanning_mode="active" if active else "passive",
                )
                processed = self._process_devices(devices)
                if processed:
                    return processed
            except Exception as e:
                if "Thread is configured for Windows GUI" in str(e):
                    self.logger.warning(f"Windows GUI thread issue detected: {e}")
                    # Fall through to alternative method
                else:
                    # This is some other unrelated error
                    raise
            
            # If standard method failed with thread issue, use our dedicated thread method
            self.logger.info("Trying BLE scan with dedicated thread")
            
            # Create a future to store the result
            loop = asyncio.get_event_loop()
            result_future = loop.create_future()
            
            # Function to run in separate thread
            def thread_scan():
                try:
                    # Run asyncio in thread
                    thread_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(thread_loop)
                    
                    # Execute the scan in this thread
                    scanner = BleakScanner(
                        service_uuids=service_uuids,
                        scanning_mode="active" if active else "passive",
                    )
                    
                    async def scan_and_return():
                        try:
                            # Start and run scanner
                            await scanner.start()
                            await asyncio.sleep(timeout)
                            await scanner.stop()
                            
                            # Get discovered devices
                            devices = scanner.discovered_devices
                            processed = self._process_devices(devices)
                            
                            # Set the result
                            if not result_future.done():
                                loop.call_soon_threadsafe(
                                    result_future.set_result, processed
                                )
                        except Exception as e:
                            if not result_future.done():
                                loop.call_soon_threadsafe(
                                    result_future.set_exception, e
                                )
                    
                    # Run the scan
                    thread_loop.run_until_complete(scan_and_return())
                    thread_loop.close()
                except Exception as e:
                    if not result_future.done():
                        loop.call_soon_threadsafe(
                            result_future.set_exception, e
                        )
            
            # Start the dedicated thread
            threading.Thread(target=thread_scan, daemon=True).start()
            
            # Wait for the result
            try:
                return await result_future
            except Exception as e:
                self.logger.error(f"Thread-based BLE scan failed: {e}")
                return self._get_test_devices()
        except Exception as e:
            self.logger.error(f"All Windows BLE scan methods failed: {e}")
            return self._get_test_devices()
    
    def _process_devices(self, devices: List[BLEDevice]) -> List[Dict[str, Any]]:
        """Process discovered BLE devices into serializable dictionaries."""
        processed_devices = []
        
        for device in devices:
            # Process metadata to ensure serializability
            serializable_metadata = {}
            if hasattr(device, 'metadata') and device.metadata:
                for key, value in device.metadata.items():
                    if isinstance(value, dict):
                        # Handle nested dicts like manufacturer_data
                        serializable_metadata[key] = {
                            m_key: binascii.hexlify(m_value).decode('ascii') 
                                   if isinstance(m_value, bytes) else m_value
                            for m_key, m_value in value.items()
                        }
                    elif isinstance(value, bytes):
                        serializable_metadata[key] = binascii.hexlify(value).decode('ascii')
                    else:
                        serializable_metadata[key] = value
            
            # Create the device info dict
            device_info = {
                "address": device.address,
                "name": device.name or "Unknown Device",
                "metadata": serializable_metadata,
                # Use getattr for safer access to advertisement_data and its rssi
                "rssi": getattr(getattr(device, 'advertisement_data', None), 'rssi', None),
                "is_real": True,
                "source": "scan"
            }
            processed_devices.append(device_info)
        
        self._cached_devices = processed_devices
        self.logger.info(f"Processed {len(processed_devices)} BLE devices")
        return processed_devices
    
    def _get_test_devices(self) -> List[Dict[str, Any]]:
        """Generate test devices when real scanning fails."""
        self.logger.info("Generating test BLE devices")
        
        test_devices = [
            {
                "address": "11:22:33:44:55:66",
                "name": "Fitness Tracker Pro",
                "rssi": -65,
                "is_real": False,
                "metadata": {
                    "manufacturer_data": {"76": "1403010b13187164"},
                    "service_uuids": ["180d", "180f"]  # Heart rate and battery services
                },
                "source": "test_windows"
            },
            {
                "address": "22:33:44:55:66:77",
                "name": "Smart Watch XR40",
                "rssi": -58,
                "is_real": False,
                "metadata": {
                    "manufacturer_data": {"89": "0300"},
                    "service_uuids": ["1800", "1801", "180a"]  # Generic services
                },
                "source": "test_windows"
            },
            {
                "address": "33:44:55:66:77:88",
                "name": "BLE Temperature Sensor",
                "rssi": -72,
                "is_real": False,
                "metadata": {
                    "manufacturer_data": {"106": "07569abcd"},
                    "service_uuids": ["181a"]  # Environmental sensing service
                },
                "source": "test_windows"
            }
        ]
        
        self._cached_devices = test_devices
        return test_devices

# Singleton instance
_scanner_instance = None

def get_ble_scanner() -> BLEScannerWrapper:
    """Get the singleton BLE scanner instance."""
    global _scanner_instance
    if _scanner_instance is None:
        _scanner_instance = BLEScannerWrapper()
    return _scanner_instance
