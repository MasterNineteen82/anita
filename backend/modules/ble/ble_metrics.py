"""
Re-export of BLE metrics from utils module.
This file ensures backward compatibility with existing import patterns.
"""

from backend.modules.ble.utils.ble_metrics import BleMetricsCollector, get_metrics_collector

# Re-export for backward compatibility
__all__ = ['BleMetricsCollector', 'get_metrics_collector']