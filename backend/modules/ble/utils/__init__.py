"""
BLE Utilities Package.

This package provides utility classes and functions for the BLE module:
- Metrics collection and system monitoring
- Device persistence and storage
- Error recovery mechanisms
- Event bus for communication

Usage:
    from backend.modules.ble.utils import get_metrics_collector, get_system_monitor
    from backend.modules.ble.utils import get_persistence_service
    from backend.modules.ble.utils import ble_event_bus
    
    # Track a BLE operation
    metrics = get_metrics_collector()
    metrics.record_connect_start("00:11:22:33:44:55")
    
    # Get system health information
    monitor = get_system_monitor()
    health_report = await monitor.get_bluetooth_health_report()
    
    # Publish an event
    ble_event_bus.emit("device_connected", {"address": "00:11:22:33:44:55"})
"""

import logging
from typing import Optional

# Import from the utility modules
from .ble_metrics import BleMetricsCollector
from .system_monitor import SystemMonitor
from .ble_persistence import BLEDeviceStorage, get_persistence_service
from .ble_recovery import BleErrorRecovery
from .events import BleEventBus, ble_event_bus

# Private singleton instances
_metrics_collector: Optional[BleMetricsCollector] = None
_system_monitor: Optional[SystemMonitor] = None
_error_recovery: Optional[BleErrorRecovery] = None

# Export the most important components
__all__ = [
    # Classes
    "BleMetricsCollector",
    "SystemMonitor",
    "BLEDeviceStorage",
    "BleErrorRecovery",
    "BleEventBus",
    
    # Singleton accessors
    "get_metrics_collector",
    "get_system_monitor",
    "get_persistence_service",
    "get_error_recovery",
    "ble_event_bus",
]

def get_metrics_collector() -> BleMetricsCollector:
    """
    Get the singleton BleMetricsCollector instance.
    
    Returns:
        BleMetricsCollector: The metrics collector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = BleMetricsCollector()
    return _metrics_collector

def get_system_monitor() -> SystemMonitor:
    """
    Get the singleton SystemMonitor instance.
    
    Returns:
        SystemMonitor: The system monitor instance
    """
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = SystemMonitor()
    return _system_monitor

def get_error_recovery() -> BleErrorRecovery:
    """
    Get the singleton BleErrorRecovery instance.
    
    Returns:
        BleErrorRecovery: The error recovery instance
    """
    global _error_recovery
    if _error_recovery is None:
        _error_recovery = BleErrorRecovery()
    return _error_recovery

# Version information
__version__ = "1.0.0"