"""BLE device scanner implementation."""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from bleak import BleakScanner

logger = logging.getLogger(__name__)

async def scan_for_devices(
    scan_time: float = 5.0, 
    active: bool = True,
    service_uuids: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Scan for BLE devices using Bleak.
    
    Args:
        scan_time: Duration of scan in seconds
        active: Whether to perform active scanning
        service_uuids: Optional list of service UUIDs to filter by
        
    Returns:
        List of discovered devices
    """
    logger.info(f"Scanning for devices (scan_time={scan_time}, active={active})")
    
    try:
        # Use BleakScanner directly
        devices = await BleakScanner.discover(
            timeout=scan_time,
            return_adv=active
        )
        
        # Convert to standard format
        result = []
        for device in devices:
            device_info = {
                "address": device.address,
                "name": device.name or "Unknown Device",
                "rssi": device.rssi,
                "metadata": {}
            }
            
            # Add advertisement data if available
            if hasattr(device, 'metadata'):
                device_info["metadata"] = {
                    "manufacturer_data": device.metadata.get("manufacturer_data", {}),
                    "service_data": device.metadata.get("service_data", {}),
                    "service_uuids": device.metadata.get("service_uuids", []),
                }
                
            result.append(device_info)
            
        logger.info(f"Found {len(result)} devices")
        return result
        
    except Exception as e:
        logger.error(f"Error scanning for devices: {e}", exc_info=True)
        raise