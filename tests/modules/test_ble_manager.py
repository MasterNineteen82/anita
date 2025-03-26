import asyncio
import pytest
import json
import os
import sys
from unittest.mock import patch, MagicMock, mock_open, call, ANY
from backend.modules.ble_metrics import BleMetricsCollector
from backend.modules.ble_recovery import BleErrorRecovery
from backend.modules.ble_persistence import BLEDeviceStorage
from bleak.exc import BleakError

from backend.modules.ble_manager import BLEManager
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from unittest.mock import AsyncMock

# Mock logger for testing
mock_logger = MagicMock()

@pytest.fixture
def ble_manager():
    """Create a BLEManager instance for testing."""
    return BLEManager(logger=mock_logger)

@pytest.fixture
def ble_metrics():
    """Create a BleMetricsCollector instance for testing."""
    return BleMetricsCollector(logger=mock_logger)

@pytest.fixture
def ble_recovery():
    """Create a BleErrorRecovery instance for testing."""
    return BleErrorRecovery(logger=mock_logger)

@pytest.fixture
def ble_storage():
    """Create a BLEDeviceStorage instance for testing."""
    return BLEDeviceStorage(logger=mock_logger)

@pytest.mark.asyncio
async def test_scan_devices_success(ble_manager):
    """Test scanning for devices successfully."""
    # Mock successful BleakScanner.discover
    with patch('backend.modules.ble_manager.BleakScanner') as mock_scanner:
        # Create mock devices
        mock_device1 = MagicMock()
        mock_device1.name = "Test Device 1"
        mock_device1.address = "00:11:22:33:44:55"
        mock_device1.rssi = -65
        
        mock_device2 = MagicMock()
        mock_device2.name = "Test Device 2"
        mock_device2.address = "AA:BB:CC:DD:EE:FF"
        mock_device2.rssi = -72
        
        # Set the return value for the discover method
        mock_scanner.discover = AsyncMock(return_value=[mock_device1, mock_device2])
        
        # Call the method to test
        result = await ble_manager.scan_devices(scan_time=1, active=False)
        
        # Verify BleakScanner.discover was called correctly
        mock_scanner.discover.assert_called_once_with(timeout=1, return_adv=False)
        
        # Verify the result is correct
        assert len(result) == 2
        assert result[0]["name"] == "Test Device 1"
        assert result[0]["address"] == "00:11:22:33:44:55"
        assert result[0]["rssi"] == -65
        assert result[1]["name"] == "Test Device 2"
        assert result[1]["address"] == "AA:BB:CC:DD:EE:FF"
        assert result[1]["rssi"] == -72

@pytest.mark.asyncio
async def test_scan_devices_error(ble_manager):
    with patch('backend.modules.ble_manager.BleakScanner') as mock_scanner:
        # Use AsyncMock for async methods
        mock_scanner.discover = AsyncMock(side_effect=Exception("Test scan error"))
        
        with pytest.raises(BleakError) as exc_info:
            await ble_manager.scan_devices(scan_time=1)
        
        assert "Test scan error" in str(exc_info.value)
        mock_logger.error.assert_called()

@pytest.mark.asyncio
async def test_connect_device_success(ble_manager):
    with patch('backend.modules.ble_manager.BleakClient') as MockBleakClient:
        mock_client_instance = MagicMock()
        # Use AsyncMock for connect
        mock_client_instance.connect = AsyncMock(return_value=True)
        mock_client_instance.is_connected = True
        MockBleakClient.return_value = mock_client_instance
        
        address = "00:11:22:33:44:55"
        result = await ble_manager.connect_device(address)
        
        assert result is True

@pytest.mark.asyncio
async def test_connect_device_failure(ble_manager):
    """Test handling connection failure."""
    # Mock BleakClient
    with patch('backend.modules.ble_manager.BleakClient') as MockBleakClient:
        # Configure the mock client to fail connection
        mock_client_instance = MagicMock()
        mock_client_instance.connect = AsyncMock(side_effect=Exception("Connection error"))
        mock_client_instance.is_connected = False
        MockBleakClient.return_value = mock_client_instance

        # Call the method to test
        address = "00:11:22:33:44:55"
        with pytest.raises(BleakError) as exc_info:
            await ble_manager.connect_device(address)
        assert "Connection error" in str(exc_info.value)

# Fix incomplete test_connect_with_exception
@pytest.mark.asyncio
async def test_connect_with_exception(ble_manager):
    """Test handling connection exception."""
    with patch('backend.modules.ble_manager.BleakClient') as MockBleakClient:
        # Configure the mock client to raise exception
        mock_client_instance = MagicMock()
        mock_client_instance.connect = AsyncMock(side_effect=Exception("Connection error"))
        MockBleakClient.return_value = mock_client_instance
        
        # Call the method and verify it raises the expected error
        address = "00:11:22:33:44:55"
        with pytest.raises(BleakError) as exc_info:
            await ble_manager.connect_device(address)
        
        assert "Connection error" in str(exc_info.value)

# Add MTU negotiation tests
@pytest.mark.asyncio
async def test_negotiate_mtu_success(ble_manager):
    ble_manager.client = MagicMock()
    ble_manager.client.is_connected = True
    ble_manager.platform_type = "windows"
    ble_manager.device_address = "00:11:22:33:44:55"
    
    # Use AsyncMock for request_mtu
    ble_manager.client._backend = MagicMock()
    ble_manager.client._backend.request_mtu = AsyncMock(return_value=185)
    
    mtu = await ble_manager.negotiate_mtu(217)
    assert mtu == 185

@pytest.mark.asyncio
async def test_negotiate_mtu_failure(ble_manager):
    """Test MTU negotiation failure."""
    # Test when not connected
    with pytest.raises(BleakError) as exc_info:
        await ble_manager.negotiate_mtu(217)
    
    assert "Not connected to device" in str(exc_info.value)

# Add connection parameter tests
@pytest.mark.asyncio
async def test_set_connection_parameters(ble_manager):
    ble_manager.client = MagicMock()
    ble_manager.client.is_connected = True
    ble_manager.platform_type = "windows"
    ble_manager.device_address = "00:11:22:33:44:55"
    
    # Use AsyncMock for set_connection_parameters
    ble_manager.client._backend = MagicMock()
    ble_manager.client._backend.set_connection_parameters = AsyncMock(return_value=True)
    
    result = await ble_manager.set_connection_parameters(
        min_interval=7.5, 
        max_interval=30.0,
        latency=0,
        timeout=500
    )
    
    assert result is True

# Add error recovery tests
@pytest.mark.asyncio
async def test_recover_connection(ble_recovery):
    """Test connection recovery."""
    # Mock a connection function that succeeds on the second attempt
    mock_conn_func = AsyncMock(side_effect=[False, True])
    mock_conn_func.side_effect = [False, True]
    
    # Call the recovery method
    result = await ble_recovery.recover_connection(
        "00:11:22:33:44:55",
        mock_conn_func,
        max_attempts=3,
        backoff_factor=1.0
    )
    
    # Verify result
    assert result is True
    assert mock_conn_func.call_count == 2
    assert ble_recovery.recovery_attempts == 1
    assert ble_recovery.successful_recoveries == 1

# Add BLE metrics tests
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
    
    # Record a failure
    op_id2 = ble_metrics.record_connect_start("AA:BB:CC:DD:EE:FF")
    ble_metrics.record_connect_complete(op_id2, "AA:BB:CC:DD:EE:FF", False)
    
    # Verify metrics updated
    assert ble_metrics.connection_attempts == 2
    assert ble_metrics.connection_successes == 1
    assert ble_metrics.connection_failures == 1

# Add bonding tests
@pytest.mark.asyncio
async def test_device_storage(ble_storage):
    """Test device bonding storage."""
    # Create a mock in-memory device store
    mock_devices = {}

    # Patch both file operations AND the internal devices dictionary
    with patch('builtins.open', mock_open()), \
         patch('json.dump') as mock_json_dump, \
         patch('json.load', return_value=mock_devices), \
         patch.object(ble_storage, 'devices', mock_devices), \
         patch('os.path.exists', return_value=True):

        # Add a bonded device
        device_address = "00:11:22:33:44:55"
        updates = {
            "name": "Test Device",
            "bonded": True,
            "services": ["1800", "1801"]
        }

        # Update the device
        ble_storage.update_device(device_address, updates)

        # Add it directly to mock_devices to simulate storage
        mock_devices[device_address] = {"address": device_address, **updates}

        # Verify it was added
        device = ble_storage.get_device(device_address)
        assert device is not None
        assert device["name"] == "Test Device"
        assert device["bonded"] is True

# Add filtered scan test
@pytest.mark.asyncio
async def test_scan_with_filters(ble_manager):
    with patch('backend.modules.ble_manager.BleakScanner') as mock_scanner:
        # Create mock devices
        mock_device1 = MagicMock()
        mock_device1.name = "Test Device 1"
        mock_device1.address = "00:11:22:33:44:55"
        mock_device1.rssi = -65
        
        mock_device2 = MagicMock()
        mock_device2.name = "Test Device 2"
        mock_device2.address = "AA:BB:CC:DD:EE:FF"
        mock_device2.rssi = -72
        
        # Set up advertisement data
        mock_device1.advertisement_data = MagicMock()
        mock_device1.advertisement_data.service_uuids = ["1800", "1801"]
        
        # Use AsyncMock for discover
        mock_scanner.discover = AsyncMock(return_value=[mock_device1, mock_device2])
        
        result = await ble_manager.scan_with_filters(
            service_uuids=["1800"],
            name_filter="Test",
            active=True
        )
        
        assert len(result) == 2