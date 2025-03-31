"""Application-wide dependencies."""

from typing import Annotated
from fastapi import Depends
import logging

# Import the modules we need
from backend.modules.ble.ble_manager import BLEManager
from backend.modules.ble.ble_service import BleService
from backend.modules.ble.ble_metrics import BleMetricsCollector

# Set up logger
logger = logging.getLogger(__name__)

# Singleton instances
_ble_manager = None
_ble_service = None
_ble_metrics = None

def get_ble_manager() -> BLEManager:
    """Get the BLE manager singleton instance."""
    global _ble_manager
    if _ble_manager is None:
        from backend.modules.ble.ble_manager import BLEManager
        logger.info("Initializing BLE Manager")
        _ble_manager = BLEManager()
    return _ble_manager

def get_ble_service():
    """
    Get a singleton BleService instance.
    """
    global _ble_service
    if _ble_service is None:
        # Import here to avoid circular imports
        from backend.modules.ble.ble_service import BleService 
        manager = get_ble_manager()
        logger.info("Initializing BLE Service")
        _ble_service = BleService(manager)
    return _ble_service

def get_ble_metrics():
    """
    Get a singleton BleMetricsCollector instance.
    """
    global _ble_metrics
    if _ble_metrics is None:
        from backend.modules.ble.ble_metrics import BleMetricsCollector
        logger.info("Initializing BLE Metrics Collector")
        _ble_metrics = BleMetricsCollector()
    return _ble_metrics

# FastAPI dependency annotations
BleServiceDep = Annotated[BleService, Depends(get_ble_service)]
BleMetricsDep = Annotated[BleMetricsCollector, Depends(get_ble_metrics)]