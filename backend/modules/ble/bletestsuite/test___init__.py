"""Test backend BLE module initialization."""

import pytest

def test_module_initialization():
    """Test that the BLE module can be imported correctly."""
    from backend.modules.ble import ble_manager, ble_metrics, ble_recovery, ble_persistence, ble_models
    
    # Verify module imports
    assert hasattr(ble_manager, 'BLEManager')
    assert hasattr(ble_metrics, 'BleMetricsCollector')
    assert hasattr(ble_recovery, 'BleErrorRecovery')
    assert hasattr(ble_persistence, 'BLEDeviceStorage')