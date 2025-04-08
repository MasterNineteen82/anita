"""
BLE scanner module for discovering nearby devices.

This module provides functionality for scanning and discovering BLE devices.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Set, Callable
import time

from backend.modules.ble.models import BLEDeviceInfo
from backend.modules.ble.utils.ble_metrics import get_metrics_collector
from backend.modules.ble.utils.events import ble_event_bus

logger = logging.getLogger(__name__)

class BleScanner:
    """BLE device scanner."""
    
    def __init__(self):
        """Initialize the BLE scanner."""
        self.client = None
        self.scanning = False
        self.discovered_devices = {}  # Address -> device info
        self.scan_filters = {}  # Filters to apply during scans
        self.metrics = get_metrics_collector()
        
        # Scan results callback
        self._scan_callback = None
        
        logger.info("BLE scanner initialized")
    
    # Implementation methods as defined in the previous message

# Singleton instance
_scanner = None

def get_scanner() -> BleScanner:
    """Get the singleton scanner instance."""
    global _scanner
    if _scanner is None:
        _scanner = BleScanner()
    return _scanner

def set_client(self, client):
    """
    Set the BLE client for the scanner
    
    Args:
        client: The BLE client to use for scanning
    """
    self.client = client
    return self