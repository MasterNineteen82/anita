from typing import Optional
from fastapi import Depends

# Update this file to use the correct import path
from backend.modules.ble_manager import BLEManager as BleService

# Service dependencies
def get_ble_service() -> BleService:
    """Dependency function to provide BleService instance."""
    return BleService()
