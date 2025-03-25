from typing import Optional
from fastapi import Depends

# Import services
from backend.domain.services.ble_service import BleService

# Import repositories
from backend.infrastructure.repositories.ble_repository import BleRepository

# Create repository instances
_ble_repository = BleRepository()

# Service dependencies
def get_ble_service() -> BleService:
    """Get the BLE service instance with dependencies."""
    return BleService(repository=_ble_repository)
