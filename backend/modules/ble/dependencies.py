"""BLE module dependencies - delegate to application-wide dependencies."""

import logging
from backend.dependencies import get_ble_service, get_ble_metrics, get_ble_manager

# Just re-export the application-wide dependencies
__all__ = ["get_ble_service", "get_ble_metrics", "get_ble_manager"]

logger = logging.getLogger(__name__)
logger.info("Using application-wide dependency system for BLE services")