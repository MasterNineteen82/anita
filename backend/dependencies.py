"""Application-wide dependencies."""

from typing import Annotated
from fastapi import Depends

from backend.modules.ble.ble_service import BleService
from backend.modules.ble.ble_metrics import BleMetricsCollector
from backend.modules.ble.ble_manager import BLEManager  # Add this line

# Singleton instances
_ble_service = None
_ble_metrics = None

def get_ble_service(ble_manager: BLEManager = Depends(None)) -> BleService:
    """
    Get a singleton BleService instance.

    Returns:
        BleService: The BLE service instance
    """
    global _ble_service
    if _ble_service is None:
        if ble_manager is None:
            from backend.modules.ble.ble_manager import BLEManager
            ble_manager = BLEManager()
        _ble_service = BleService(ble_manager)
    return _ble_service

def get_ble_metrics() -> BleMetricsCollector:
    """
    Get a singleton BleMetricsCollector instance.

    Returns:
        BleMetricsCollector: The BLE metrics collector instance
    """
    global _ble_metrics
    if _ble_metrics is None:
        _ble_metrics = BleMetricsCollector()
    return _ble_metrics

# FastAPI dependency annotations
BleServiceDep = Annotated[BleService, Depends(get_ble_service)]
BleMetricsDep = Annotated[BleMetricsCollector, Depends(get_ble_metrics)]