from typing import TYPE_CHECKING
from backend.modules.ble.core.device_manager import get_device_manager
from backend.modules.ble.core.adapter_manager import get_adapter_manager
import logging

if TYPE_CHECKING:
    from backend.modules.ble.core.ble_service import BleService

logger = logging.getLogger(__name__)

_ble_service = None

def get_ble_service() -> 'BleService':
    """Get a singleton BleService instance."""
    global _ble_service
    if _ble_service is None:
        logger.info("Initializing BLE Service")
        from backend.modules.ble.core.ble_service import BleService  # Inline import
        _ble_service = BleService(config={
            "device_manager": get_device_manager(),
            "adapter_manager": get_adapter_manager()
        })
    return _ble_service