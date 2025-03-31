"""
Bluetooth Low Energy (BLE) module.

This module provides functionality for working with BLE devices:
- Device discovery and connection
- Service and characteristic operations
- Adapter management
- Notifications and events
"""

# Version information
__version__ = "1.0.0"
__author__ = "BLE Module Team"

# Import main API router from api package
from .api import ble_router

# Import WebSocket endpoint from comms package
from .comms import websocket_endpoint, websocket_manager

# Import core BLE components
from .core.ble_service import BleService, get_ble_service
from .core.adapter_manager import BleAdapterManager, get_adapter_manager
from .core.device_manager import BleDeviceManager as BleManager, get_device_manager

# Import metric and monitoring utilities
from .utils.system_monitor import SystemMonitor, get_system_monitor
from .utils.ble_metrics import BleMetricsCollector, get_metrics_collector, get_ble_metrics
from .utils.ble_recovery import BleErrorRecovery, get_error_recovery
from .utils.ble_persistence import BLEDeviceStorage, get_persistence_service
from .utils.events import ble_event_bus

# Re-export key models for convenience
from .models import (
    # Main types
    BLEDeviceInfo, ConnectionStatus, CharacteristicValue,
    # Message types
    MessageType, BaseMessage, ScanResultMessage, ConnectResultMessage,
    # Health models
    BluetoothHealthReport, SystemMetric
)

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
    
    # Utility components
    "SystemMonitor",
    "get_system_monitor",
    "BleMetricsCollector",
    "get_metrics_collector",
    "get_ble_metrics",
    "BleErrorRecovery",
    "get_error_recovery",
    "BLEDeviceStorage",
    "get_persistence_service",
    "ble_event_bus",
    
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
    
    # Module metadata
    "__version__"
]

# Module initialization
def initialize_module():
    """Initialize the BLE module."""
    # Get singletons to ensure they're created
    get_system_monitor()
    get_metrics_collector()
    get_error_recovery()
    
    # Listen for events
    ble_event_bus.on("ble_error", lambda data: get_metrics_collector().record_error(
        data.get("type", "unknown"),
        device_address=data.get("device_address")
    ))

# Perform initialization if not imported for documentation only
import sys
if not any(arg.endswith('sphinx') for arg in sys.argv):
    initialize_module()