"""Application-wide dependencies."""

from typing import Annotated
from fastapi import Depends
import logging

# Import the modules we need
from backend.modules.ble.core.adapter_manager import BleAdapterManager
from backend.modules.ble.core.device_manager import BleDeviceManager
from backend.modules.ble.core.ble_service_factory import get_ble_service  # Import from factory
from backend.modules.ble.utils.ble_metrics import BleMetricsCollector
from backend.modules.ble.core.ble_service import BleService  # Import BleService

# Set up logger
logger = logging.getLogger(__name__)

# Singleton instances
_adapter_manager = None
_device_manager = None
_ble_metrics = None

def get_adapter_manager() -> BleAdapterManager:
    """Get the BLE adapter manager singleton instance."""
    global _adapter_manager
    if _adapter_manager is None:
        from backend.modules.ble.core.adapter_manager import BleAdapterManager
        logger.info("Initializing BLE Adapter Manager")
        _adapter_manager = BleAdapterManager()
        
        # Create a task to initialize adapters if needed -- REMOVED AS MANAGER INIT HANDLES THIS
    return _adapter_manager

def get_device_manager() -> BleDeviceManager:
    """Get the BLE device manager singleton instance."""
    global _device_manager
    if _device_manager is None:
        from backend.modules.ble.core.device_manager import BleDeviceManager
        logger.info("Initializing BLE Device Manager")
        _device_manager = BleDeviceManager()
    return _device_manager

def get_ble_metrics():
    """
    Get a singleton BleMetricsCollector instance.
    """
    global _ble_metrics
    if _ble_metrics is None:
        from backend.modules.ble.utils.ble_metrics import BleMetricsCollector
        logger.info("Initializing BLE Metrics Collector")
        _ble_metrics = BleMetricsCollector()
    return _ble_metrics

# FastAPI dependency annotations
BleServiceDep = Annotated[BleService, Depends(get_ble_service)]  # Use factory function
BleMetricsDep = Annotated[BleMetricsCollector, Depends(get_ble_metrics)]