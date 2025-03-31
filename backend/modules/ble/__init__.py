"""
Bluetooth Low Energy (BLE) module.
"""

# Version information
__version__ = "1.0.0"
__author__ = "BLE Module Team"

# Import main API router from api package
from .api import ble_router

# CRITICAL: Export ble_routes as a direct reference to the router
from .api.ble_routes import router as ble_routes

# Import WebSocket endpoint from comms package
from .comms import websocket_endpoint, websocket_manager

# Import core BLE components
from .core.ble_service import BleService, get_ble_service
from .core.adapter_manager import BleAdapterManager, get_adapter_manager
from .core.device_manager import BleDeviceManager as BleManager, get_device_manager
from .core.scanner import BleScanner, get_scanner

# Re-export key models for convenience
from .models import (
    # Main types
    BLEDeviceInfo, ConnectionStatus, CharacteristicValue,
    # Message types
    MessageType, BaseMessage, ScanResultMessage, ConnectResultMessage,
    # Health models
    BluetoothHealthReport, SystemMetric
)

# Create top-level bridge for BLE manager
from .ble_manager import BLEManager, get_ble_manager

# Define public API
__all__ = [
    # API components
    "ble_router",
    "websocket_endpoint",
    "websocket_manager",
    
    # Core components
    "BleService",
    "get_ble_service",
    "BleAdapterManager",
    "get_adapter_manager",
    "BleManager",
    "get_device_manager",
    "BleScanner",
    "get_scanner",
    
    # Utility components
    "get_system_monitor",
    "get_metrics_collector",
    "get_ble_metrics",
    "get_error_recovery",
    "get_persistence_service",
    
    # Key models
    "BLEDeviceInfo",
    "ConnectionStatus",
    "CharacteristicValue",
    "MessageType",
    "BaseMessage",
    "ScanResultMessage",
    "ConnectResultMessage",
    "BluetoothHealthReport",
    "SystemMetric",
    
    # Legacy bridge
    "BLEManager",
    "get_ble_manager",
    
    # Module metadata
    "__version__",
    
    # Export ble_routes
    "ble_routes"
]

# Module initialization - DO NOT RUN AT IMPORT TIME
def initialize_module():
    """Initialize the BLE module. Should be called explicitly, not during import."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Initializing BLE module")
    
    try:
        # Import utility modules here to avoid circular imports
        from .utils.system_monitor import get_system_monitor
        from .utils.ble_metrics import get_metrics_collector
        from .utils.ble_recovery import get_error_recovery
        from .utils.events import ble_event_bus
        
        # Get singletons to ensure they're created
        get_system_monitor()
        get_metrics_collector()
        get_error_recovery()
        
        # Listen for events
        ble_event_bus.on("ble_error", lambda data: get_metrics_collector().record_error(
            data.get("type", "unknown"),
            device_address=data.get("device_address")
        ))
        
        logger.info("BLE module initialization complete")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize BLE module: {e}")
        return False

# CRITICAL: Remove automatic initialization during import
# import sys
# if not any(arg.endswith('sphinx') for arg in sys.argv):
#     initialize_module()