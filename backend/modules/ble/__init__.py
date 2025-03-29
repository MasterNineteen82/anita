"""Backend BLE module package."""

# Import main components for easier access
# from backend.modules.ble.ble_manager import BLEManager  # Remove this line
from backend.modules.ble.ble_service import BleService
from backend.modules.ble.ble_metrics import BleMetricsCollector, SystemMonitor
from backend.modules.ble.ble_recovery import BleErrorRecovery

# Version information
__version__ = "1.2.0"