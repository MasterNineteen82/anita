import json
import os
import logging
from typing import Dict, List, Any, Optional

class BLEDeviceStorage:
    """Persistent storage for BLE device information and bonding."""
    
    def __init__(self, storage_path: str = None, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.storage_path = storage_path or os.path.join(os.path.expanduser("~"), ".anita", "ble_devices.json")
        self._ensure_storage_dir()
        self.devices = self._load_devices()
    
    def _ensure_storage_dir(self):
        """Ensure the storage directory exists."""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
    
    def _load_devices(self) -> Dict[str, Any]:
        """Load devices from storage."""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"Error loading BLE devices: {e}")
            return {}
    
    def _save_devices(self):
        """Save devices to storage."""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.devices, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving BLE devices: {e}")
    
    def get_device(self, address: str) -> Optional[Dict[str, Any]]:
        """Get device information by address."""
        return self.devices.get(address)
    
    def get_all_devices(self) -> List[Dict[str, Any]]:
        """Get all stored devices."""
        return [
            {"address": addr, **info} 
            for addr, info in self.devices.items()
        ]
    
    def get_bonded_devices(self) -> List[Dict[str, Any]]:
        """Get all bonded devices."""
        return [
            {"address": addr, **info} 
            for addr, info in self.devices.items() 
            if info.get("bonded", False)
        ]
    
    def save_device(self, address: str, info: Dict[str, Any]):
        """Save device information."""
        self.devices[address] = info
        self._save_devices()
    
    def update_device(self, address: str, updates: Dict[str, Any]):
        """Update device information."""
        if address in self.devices:
            self.devices[address].update(updates)
            self._save_devices()
    
    def remove_device(self, address: str):
        """Remove a device from storage."""
        if address in self.devices:
            del self.devices[address]
            self._save_devices()
    
    def set_bonded(self, address: str, bonded: bool = True):
        """Mark a device as bonded/unbonded."""
        if address in self.devices:
            self.devices[address]["bonded"] = bonded
        else:
            self.devices[address] = {"bonded": bonded}
        self._save_devices()