"""Test BLE metrics collection functionality."""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from backend.modules.ble.ble_metrics import BleMetricsCollector

# Fixture for metrics
@pytest.fixture
def ble_metrics():
    """Create a BleMetricsCollector instance for testing."""
    return BleMetricsCollector(logger=MagicMock())

@pytest.mark.asyncio
async def test_metrics_connection_recording(ble_metrics):
    """Test recording connection metrics."""
    # Record a connection start
    op_id = ble_metrics.record_connect_start("00:11:22:33:44:55")
    
    # Verify operation was recorded
    assert op_id in ble_metrics.operations
    assert ble_metrics.operations[op_id]["type"] == "connect"
    assert ble_metrics.operations[op_id]["address"] == "00:11:22:33:44:55"
    
    # Record successful completion
    ble_metrics.record_connect_complete(op_id, "00:11:22:33:44:55", True)
    
    # Verify metrics updated
    assert ble_metrics.connection_attempts == 1
    assert ble_metrics.connection_successes == 1
    assert ble_metrics.connection_failures == 0

@pytest.mark.asyncio
async def test_metrics_scan_recording(ble_metrics):
    """Test recording scan metrics."""
    # Record a scan start
    op_id = ble_metrics.record_scan_start()
    
    # Record completion with devices found
    devices = [
        {"address": "00:11:22:33:44:55", "name": "Device 1"},
        {"address": "AA:BB:CC:DD:EE:FF", "name": "Device 2"}
    ]
    ble_metrics.record_scan_complete(op_id, devices)
    
    # Verify metrics
    assert ble_metrics.scan_count == 1
    assert ble_metrics.devices_found == 2

@pytest.mark.asyncio
async def test_metrics_read_write_recording(ble_metrics):
    """Test recording characteristic read/write metrics."""
    # Record read operation
    read_op_id = ble_metrics.record_read_start("2A00")
    ble_metrics.record_read_complete(read_op_id, "2A00", success=True)
    
    # Record write operation
    write_op_id = ble_metrics.record_write_start("2A06")
    ble_metrics.record_write_complete(write_op_id, "2A06", success=True)
    
    # Verify metrics
    assert ble_metrics.read_count == 1
    assert ble_metrics.read_success_count == 1
    assert ble_metrics.write_count == 1
    assert ble_metrics.write_success_count == 1

@pytest.mark.asyncio
async def test_metrics_edge_cases(ble_metrics):
    """Test edge cases in metrics collection."""
    # Test tracking large number of operations
    op_ids = []
    for i in range(1000):
        op_id = ble_metrics.record_connect_start(f"00:11:22:33:44:{i:02x}")
        op_ids.append(op_id)
    
    # Complete all operations
    for i, op_id in enumerate(op_ids):
        ble_metrics.record_connect_complete(op_id, f"00:11:22:33:44:{i:02x}", i % 2 == 0)
    
    # Verify metrics
    assert ble_metrics.connection_attempts == 1000
    assert ble_metrics.connection_successes == 500
    assert ble_metrics.connection_failures == 500

@pytest.mark.asyncio
async def test_metrics_performance(ble_metrics):
    """Test metrics collection performance."""
    # Measure time to record many operations
    import time
    
    start_time = time.time()
    for i in range(10000):
        op_id = ble_metrics.record_connect_start(f"00:11:22:33:44:{i % 256:02x}")
        ble_metrics.record_connect_complete(op_id, f"00:11:22:33:44:{i % 256:02x}", True)
    
    duration = time.time() - start_time
    # Ensure performance is reasonable (less than 1 second for 10,000 operations)
    assert duration < 1.0, f"Metrics collection took {duration:.2f} seconds for 10,000 operations"

@pytest.mark.asyncio
async def test_metrics_reset(ble_metrics):
    """Test resetting metrics."""
    # Record some operations
    ble_metrics.record_connect_start("00:11:22:33:44:55")
    ble_metrics.record_scan_start()
    
    # Reset metrics
    ble_metrics.reset()
    
    # Verify all metrics are reset
    assert ble_metrics.connection_attempts == 0
    assert ble_metrics.connection_successes == 0
    assert ble_metrics.connection_failures == 0
    assert ble_metrics.scan_count == 0
    assert ble_metrics.devices_found == 0
    assert len(ble_metrics.operations) == 0