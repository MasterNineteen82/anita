import logging
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class BLEDeviceStorage:
    """Storage class for BLE device information and configurations."""
    
    def __init__(self, storage_dir: str = None):
        self.storage_dir = storage_dir or os.path.join(os.path.expanduser("~"), ".blemanager")
        os.makedirs(self.storage_dir, exist_ok=True)
        self.bonded_devices_file = os.path.join(self.storage_dir, "bonded_devices.json")
        self.device_preferences_file = os.path.join(self.storage_dir, "device_preferences.json")
        
    async def get_bonded_devices(self) -> List[Dict[str, Any]]:
        """Get list of bonded/paired devices."""
        try:
            if not os.path.exists(self.bonded_devices_file):
                return []
                
            with open(self.bonded_devices_file, 'r') as f:
                devices = json.load(f)
            return devices
        except Exception as e:
            logger.error(f"Error loading bonded devices: {e}", exc_info=True)
            return []
            
    async def add_bonded_device(self, device: Dict[str, Any]) -> bool:
        """Add a device to the bonded devices list."""
        try:
            devices = await self.get_bonded_devices()
            
            # Check if device already exists
            if any(d.get("address") == device.get("address") for d in devices):
                # Update the existing device
                devices = [device if d.get("address") == device.get("address") else d for d in devices]
            else:
                # Add timestamp to the device info
                device["bonded_at"] = datetime.now().isoformat()
                devices.append(device)
                
            with open(self.bonded_devices_file, 'w') as f:
                json.dump(devices, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error adding bonded device: {e}", exc_info=True)
            return False
            
    async def remove_bonded_device(self, address: str) -> bool:
        """Remove a device from the bonded devices list."""
        try:
            devices = await self.get_bonded_devices()
            devices = [d for d in devices if d.get("address") != address]
            
            with open(self.bonded_devices_file, 'w') as f:
                json.dump(devices, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error removing bonded device: {e}", exc_info=True)
            return False
            
    async def get_device_preferences(self, address: str) -> Dict[str, Any]:
        """Get preferences for a specific device."""
        try:
            if not os.path.exists(self.device_preferences_file):
                return {}
                
            with open(self.device_preferences_file, 'r') as f:
                all_preferences = json.load(f)
                
            return all_preferences.get(address, {})
        except Exception as e:
            logger.error(f"Error loading device preferences: {e}", exc_info=True)
            return {}
            
    async def save_device_preferences(self, address: str, preferences: Dict[str, Any]) -> bool:
        """Save preferences for a specific device."""
        try:
            all_preferences = {}
            
            if os.path.exists(self.device_preferences_file):
                with open(self.device_preferences_file, 'r') as f:
                    all_preferences = json.load(f)
                    
            all_preferences[address] = preferences
            
            with open(self.device_preferences_file, 'w') as f:
                json.dump(all_preferences, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving device preferences: {e}", exc_info=True)
            return False

# Singleton persistence service
_persistence_service = None

def get_persistence_service():
    """Get the BLE persistence service singleton."""
    global _persistence_service
    if _persistence_service is None:
        _persistence_service = BLEDeviceStorage()
    return _persistence_service