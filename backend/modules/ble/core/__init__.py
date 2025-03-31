"""BLE core modules."""

# Import from core modules
from .adapter_manager import BleAdapterManager, get_adapter_manager
from .device_manager import BleDeviceManager, get_device_manager
from .ble_service import BleService, get_ble_service
from .scanner import BleScanner, get_scanner

# Import utilities needed by core components
from ..utils.ble_metrics import BleMetricsCollector, get_metrics_collector
from ..utils.system_monitor import SystemMonitor, get_system_monitor
from ..utils.events import ble_event_bus

# Import from utilities that were expected to be in core
from ..utils.ble_recovery import BleErrorRecovery, get_error_recovery

# Version information
__version__ = "1.3.0"

# Define public API
__all__ = [
    # Main service 
    "BleService",
    "get_ble_service",
    
    # Manager classes
    "BleDeviceManager",
    "get_device_manager",
    "BleAdapterManager", 
    "get_adapter_manager",
    
    # Utilities now included from utils
    "BleMetricsCollector",
    "get_metrics_collector",
    "SystemMonitor",
    "get_system_monitor",
    "BleErrorRecovery",
    "get_error_recovery",
    
    # Utilities
    "BleScanner",
    "get_scanner",
    "ble_event_bus"
]