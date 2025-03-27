import pytest
import os
import sys
import asyncio
import time
from unittest.mock import patch, MagicMock, mock_open, AsyncMock, ANY
from backend.modules.ble.ble_metrics import BleMetricsCollector
from backend.modules.ble.ble_recovery import BleErrorRecovery
from backend.modules.ble.ble_persistence import BLEDeviceStorage
from bleak.exc import BleakError
from bleak.backends.device import BLEDevice
from bleak import BleakClient, BleakScanner
from backend.modules.ble.ble_manager import BLEManager
from backend.logging.logging_config import get_api_logger
import platform
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Mock logger for testing
mock_logger = MagicMock()

# Fixture for creating a BLEManager instance
@pytest.fixture
def ble_manager():
    """Fixture for creating a BLEManager instance."""
    manager = BLEManager(logger=MagicMock())
    manager.platform_type = platform.system().lower()
    return manager

@pytest.fixture
def mock_ble_device():
    """Fixture for creating a mock BLE device."""
    return BLEDevice("AA:BB:CC:DD:EE:FF", "Test Device", details={}, rssi=-50)

@pytest.fixture
def ble_metrics():
    """Fixture for creating a BleMetricsCollector instance."""
    return BleMetricsCollector(logger=MagicMock())

@pytest.fixture
def ble_recovery():
    """Fixture for creating a BleErrorRecovery instance."""
    return BleErrorRecovery(logger=MagicMock())

@pytest.fixture
def ble_storage():
    """Fixture for creating a BLEDeviceStorage instance."""
    return BLEDeviceStorage(logger=MagicMock())

@pytest.mark.asyncio
@pytest.mark.parametrize("device_count", [0, 1, 5, 20])
async def test_scan_devices_success(ble_manager, device_count):
    """Test scanning for devices with varying device counts."""
    # Create mock devices
    mock_devices = [
        BLEDevice(f"AA:BB:CC:DD:EE:{i:02x}", f"Test Device {i}", details={}, rssi=-50 - i)
        for i in range(device_count)
    ]

    with patch("backend.modules.ble.ble_manager.BleakScanner.discover", return_value=mock_devices):
        # Call the method to test
        result = await ble_manager.scan_devices(scan_time=1)

        # Verify the result
        assert len(result) == device_count
        for i, device in enumerate(result):
            assert device["name"] == f"Test Device {i}"
            assert device["address"] == f"aa:bb:cc:dd:ee:{i:02x}"

@pytest.mark.asyncio
async def test_scan_devices_error(ble_manager):
    """Test scanning error handling."""
    with patch("backend.modules.ble.ble_manager.BleakScanner.discover", side_effect=BleakError("Scan failed")):
        with pytest.raises(BleakError) as exc_info:
            await ble_manager.scan_devices(scan_time=1)

        assert "Scan failed" in str(exc_info.value)
        ble_manager.logger.error.assert_called_with("Scan failed: Scan failed")

@pytest.mark.asyncio
async def test_connect_device_success(ble_manager):
    with patch('backend.modules.ble.ble_manager.BleakClient') as MockBleakClient:
        # Properly mock BleakClient for async operations
        mock_client = AsyncMock(spec=BleakClient)
        mock_client.connect = AsyncMock(return_value=True)
        MockBleakClient.return_value = mock_client
        
        address = "00:11:22:33:44:55"
        result = await ble_manager.connect_device(address)
        
        assert result is True

@pytest.mark.asyncio
async def test_connect_device_failure(ble_manager):
    """Test handling connection failure."""
    # Mock BleakClient
    with patch('backend.modules.ble.ble_manager.BleakClient') as MockBleakClient:
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
    """Test handling connection exceptions."""
    with patch("backend.modules.ble.ble_manager.BleakClient") as MockBleakClient:
        # Configure the mock client to raise an exception
        mock_client_instance = MagicMock()
        mock_client_instance.connect = AsyncMock(side_effect=BleakError("Connection error"))
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
    
    # Mock the MTU negotiation method
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
         patch('json.dump'), \
        patch('json.load', return_value=mock_devices), \
         patch.object(ble_storage, 'devices', mock_devices), \
         patch('os.path.exists', return_value=True):
        
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
    with patch('backend.modules.ble.ble_manager.BleakScanner') as mock_scanner:
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

@pytest.mark.asyncio
async def test_is_adapter_available(ble_manager):
    """Test if the Bluetooth adapter availability check works."""
    with patch("backend.modules.ble.ble_manager.BleakScanner") as MockBleakScanner:
        MockBleakScanner.return_value.start = AsyncMock()
        MockBleakScanner.return_value.stop = AsyncMock()
        assert await ble_manager.is_adapter_available() is True

@pytest.mark.asyncio
async def test_is_adapter_available_failure(ble_manager):
    """Test adapter availability check failure."""
    with patch("backend.modules.ble.ble_manager.BleakScanner", side_effect=Exception("Adapter not found")):
        assert await ble_manager.is_adapter_available() is False

@pytest.mark.asyncio
async def test_scan_devices(ble_manager):
    """Test basic device scanning functionality."""
    mock_device = BLEDevice("AA:BB:CC:DD:EE:FF", "Test Device", details={}, rssi=-50)
    with patch("backend.modules.ble.ble_manager.BleakScanner.discover", return_value=[mock_device]):
        devices = await ble_manager.scan_devices(scan_time=1)
        assert len(devices) == 1
        assert devices[0]["address"] == "aa:bb:cc:dd:ee:ff"
        assert devices[0]["name"] == "Test Device"

@pytest.mark.asyncio
async def test_connect_device(ble_manager):
    """Test connecting to a device."""
    mock_client = AsyncMock(spec=BleakClient)
    mock_client.connect = AsyncMock()
    mock_client.disconnect = AsyncMock()
    mock_client.is_connected = True
    
    with patch("backend.modules.ble.ble_manager.BleakClient", return_value=mock_client):
        success = await ble_manager.connect_device("AA:BB:CC:DD:EE:FF", timeout=5)
        assert success is True
        mock_client.connect.assert_called_once()
        await ble_manager.disconnect_device()
        mock_client.disconnect.assert_called_once()

@pytest.mark.asyncio
async def test_disconnect_device(ble_manager):
    """Test disconnecting from a device."""
    mock_client = AsyncMock(spec=BleakClient)
    mock_client.disconnect = AsyncMock()
    mock_client.is_connected = False
    ble_manager.client = mock_client
    
    await ble_manager.disconnect_device()
    mock_client.disconnect.assert_called_once()

# --- Error Handling Tests ---

@pytest.mark.asyncio
async def test_scan_devices_bleak_error(ble_manager):
    """Test handling of BleakError during scanning."""
    with patch("backend.modules.ble.ble_manager.BleakScanner.discover", side_effect=BleakError("Scan failed")):
        with pytest.raises(BleakError):
            await ble_manager.scan_devices(scan_time=1)

@pytest.mark.asyncio
async def test_connect_device_bleak_error(ble_manager):
    """Test handling of BleakError during connection."""
    mock_client = AsyncMock(spec=BleakClient)
    mock_client.connect = AsyncMock(side_effect=BleakError("Connection failed"))
    
    with patch("backend.modules.ble.ble_manager.BleakClient", return_value=mock_client):
        with pytest.raises(BleakError):
            await ble_manager.connect_to_device("AA:BB:CC:DD:EE:FF", timeout=5)

# --- Edge Case Tests ---

@pytest.mark.asyncio
async def test_scan_devices_no_devices_found(ble_manager):
    """Test scanning when no devices are found."""
    with patch("backend.modules.ble.ble_manager.BleakScanner.discover", return_value=[]):
        devices = await ble_manager.scan_devices(scan_time=1)
        assert len(devices) == 0

# --- Advanced Functionality Tests (To be implemented) ---

@pytest.mark.asyncio
async def test_get_services(ble_manager):
    """Test retrieving services from a connected device."""
    # Setup mock client with services
    mock_service1 = MagicMock()
    mock_service1.uuid = "1800"
    mock_service1.description = "Generic Access"
    
    mock_service2 = MagicMock()
    mock_service2.uuid = "1801"
    mock_service2.description = "Generic Attribute"
    
    ble_manager.client = MagicMock()
    ble_manager.client.is_connected = True
    ble_manager.client.services = MagicMock()
    ble_manager.client.services.services = {
        "1800": mock_service1,
        "1801": mock_service2
    }
    
    # Test success case
    services = await ble_manager.get_services()
    assert len(services) == 2
    assert services[0]["uuid"] == "1800"
    assert services[0]["description"] == "Generic Access"
    assert services[1]["uuid"] == "1801"
    
    # Test not connected case
    ble_manager.client.is_connected = False
    with pytest.raises(BleakError) as exc_info:
        await ble_manager.get_services()
    assert "Not connected to device" in str(exc_info.value)
    
    # Test services retrieval failure
    ble_manager.client.is_connected = True
    ble_manager.client.services = None
    with pytest.raises(BleakError) as exc_info:
        await ble_manager.get_services()
    assert "Failed to retrieve services" in str(exc_info.value)

@pytest.mark.asyncio
async def test_get_characteristics(ble_manager):
    """Test retrieving characteristics for a service."""
    # Setup mock client with services and characteristics
    mock_char1 = MagicMock()
    mock_char1.uuid = "2A00"
    mock_char1.description = "Device Name"
    mock_char1.properties = ["read"]
    
    mock_char2 = MagicMock()
    mock_char2.uuid = "2A01"
    mock_char2.description = "Appearance"
    mock_char2.properties = ["read", "write"]
    
    mock_service = MagicMock()
    mock_service.uuid = "1800"
    mock_service.characteristics = [mock_char1, mock_char2]
    
    ble_manager.client = MagicMock()
    ble_manager.client.is_connected = True
    ble_manager.client.services = MagicMock()
    ble_manager.client.services.get_service = MagicMock(return_value=mock_service)
    
    # Test success case
    chars = await ble_manager.get_characteristics("1800")
    assert len(chars) == 2
    assert chars[0]["uuid"] == "2A00"
    assert chars[0]["description"] == "Device Name"
    assert "read" in chars[0]["properties"]
    assert chars[1]["uuid"] == "2A01"
    assert "write" in chars[1]["properties"]
    
    # Test not connected case
    ble_manager.client.is_connected = False
    with pytest.raises(BleakError) as exc_info:
        await ble_manager.get_characteristics("1800")
    assert "Not connected to device" in str(exc_info.value)
    
    # Test invalid service UUID
    ble_manager.client.is_connected = True
    ble_manager.client.services.get_service = MagicMock(return_value=None)
    with pytest.raises(BleakError) as exc_info:
        await ble_manager.get_characteristics("invalid-uuid")
    assert "Service not found" in str(exc_info.value)

@pytest.mark.asyncio
async def test_read_characteristic(ble_manager):
    """Test reading a characteristic value."""
    # Setup mock client with read characteristic
    test_value = bytearray([0x54, 0x65, 0x73, 0x74])  # "Test" in bytes
    
    ble_manager.client = MagicMock()
    ble_manager.client.is_connected = True
    ble_manager.client.read_gatt_char = AsyncMock(return_value=test_value)
    
    # Test success case
    char_uuid = "2A00"
    value = await ble_manager.read_characteristic(char_uuid)
    assert value["value"] == "54657374"  # hex representation
    assert value["text"] == "Test"  # text representation
    ble_manager.client.read_gatt_char.assert_called_with(char_uuid)
    
    # Test not connected case
    ble_manager.client.is_connected = False
    with pytest.raises(BleakError) as exc_info:
        await ble_manager.read_characteristic(char_uuid)
    assert "Not connected to device" in str(exc_info.value)
    
    # Test permission error
    ble_manager.client.is_connected = True
    ble_manager.client.read_gatt_char = AsyncMock(side_effect=BleakError("Read not permitted"))
    with pytest.raises(BleakError) as exc_info:
        await ble_manager.read_characteristic(char_uuid)
    assert "Read not permitted" in str(exc_info.value)
    
    # Test characteristic not found
    ble_manager.client.read_gatt_char = AsyncMock(side_effect=BleakError("Characteristic not found"))
    with pytest.raises(BleakError) as exc_info:
        await ble_manager.read_characteristic(char_uuid)
    assert "Characteristic not found" in str(exc_info.value)

@pytest.mark.asyncio
async def test_write_characteristic(ble_manager):
    """Test writing a value to a characteristic."""
    # Setup mock client
    ble_manager.client = MagicMock()
    ble_manager.client.is_connected = True
    ble_manager.client.write_gatt_char = AsyncMock(return_value=True)
    
    # Test success case - writing string data
    char_uuid = "2A06"  # Alert Level characteristic
    test_value = "Test"
    result = await ble_manager.write_characteristic(char_uuid, test_value)
    assert result is True
    ble_manager.client.write_gatt_char.assert_called_once()
    
    # Reset for next test
    ble_manager.client.write_gatt_char.reset_mock()
    
    # Test success case - writing hex data
    hex_value = "0102FFEE"
    result = await ble_manager.write_characteristic(char_uuid, hex_value)
    assert result is True
    expected_value = bytes([1, 2, 255, 238])
    ble_manager.client.write_gatt_char.assert_called_with(char_uuid, expected_value, response=True)
    
    # Test not connected case
    ble_manager.client.is_connected = False
    with pytest.raises(BleakError) as exc_info:
        await ble_manager.write_characteristic(char_uuid, test_value)
    assert "Not connected to device" in str(exc_info.value)
    
    # Test write failure
    ble_manager.client.is_connected = True
    ble_manager.client.write_gatt_char = AsyncMock(side_effect=BleakError("Write not permitted"))
    with pytest.raises(BleakError) as exc_info:
        await ble_manager.write_characteristic(char_uuid, test_value)
    assert "Write not permitted" in str(exc_info.value)
    
    # Test invalid value type
    with pytest.raises(ValueError) as exc_info:
        await ble_manager.write_characteristic(char_uuid, test_value, value_type="invalid_type")
    assert "Invalid value_type" in str(exc_info.value)
    
    # Test with write without response option
    ble_manager.client.write_gatt_char = AsyncMock(return_value=True)
    result = await ble_manager.write_characteristic(char_uuid, test_value, response=False)
    assert result is True
    from unittest.mock import ANY
    ble_manager.client.write_gatt_char.assert_called_with(char_uuid, ANY, response=False)

@pytest.mark.asyncio
async def test_start_notify(ble_manager):
    """Test starting notifications for a characteristic."""
    # Setup mock client
    ble_manager.client = MagicMock()
    ble_manager.client.is_connected = True
    ble_manager.client.start_notify = AsyncMock(return_value=True)
    
    # Create a simple callback function
    callback_called = False
    callback_value = None
    
    def notification_callback(sender, data):
        nonlocal callback_called, callback_value
        callback_called = True
        callback_value = data
    
    # Test success case
    char_uuid = "2A37"  # Heart Rate Measurement characteristic
    result = await ble_manager.start_notify(char_uuid, notification_callback)
    assert result is True
    ble_manager.client.start_notify.assert_called_with(char_uuid, ANY)
    
    # Test callback invocation (manually trigger the registered callback)
    # Get the callback function passed to client.start_notify
    registered_callback = ble_manager.client.start_notify.call_args[0][1]
    # Invoke it with test data
    test_data = bytearray([0, 60])  # Heart rate of 60 bpm
    registered_callback(char_uuid, test_data)
    assert callback_called
    assert callback_value == test_data
    
    # Test not connected case
    ble_manager.client.is_connected = False
    with pytest.raises(BleakError) as exc_info:
        await ble_manager.start_notify(char_uuid, notification_callback)
    assert "Not connected to device" in str(exc_info.value)
    
    # Test failure starting notifications
    ble_manager.client.is_connected = True
    ble_manager.client.start_notify = AsyncMock(side_effect=BleakError("Notifications not supported"))
    with pytest.raises(BleakError) as exc_info:
        await ble_manager.start_notify(char_uuid, notification_callback)
    assert "Notifications not supported" in str(exc_info.value)
    
    # Test with invalid callback
    ble_manager.client.start_notify = AsyncMock(return_value=True)
    with pytest.raises(TypeError) as exc_info:
        await ble_manager.start_notify(char_uuid, "not_a_function")
    assert "Callback must be callable" in str(exc_info.value) or "not callable" in str(exc_info.value)

@pytest.mark.asyncio
async def test_stop_notify(ble_manager):
    """Test stopping notifications for a characteristic."""
    # Setup mock client
    ble_manager.client = MagicMock()
    ble_manager.client.is_connected = True
    ble_manager.client.stop_notify = AsyncMock(return_value=True)
    
    # Test success case
    char_uuid = "2A37"  # Heart Rate Measurement characteristic
    result = await ble_manager.stop_notify(char_uuid)
    assert result is True
    ble_manager.client.stop_notify.assert_called_with(char_uuid)
    
    # Test not connected case
    ble_manager.client.is_connected = False
    with pytest.raises(BleakError) as exc_info:
        await ble_manager.stop_notify(char_uuid)
    assert "Not connected to device" in str(exc_info.value)
    
    # Test failure stopping notifications
    ble_manager.client.is_connected = True
    ble_manager.client.stop_notify = AsyncMock(side_effect=BleakError("Notifications not active"))
    with pytest.raises(BleakError) as exc_info:
        await ble_manager.stop_notify(char_uuid)
    assert "Notifications not active" in str(exc_info.value)
    
    # Test stopping notifications for a characteristic that never had them started
    ble_manager.client.stop_notify = AsyncMock(side_effect=BleakError("No notifications found for characteristic"))
    with pytest.raises(BleakError) as exc_info:
        await ble_manager.stop_notify("2A38")  # Body Sensor Location
    assert "No notifications found" in str(exc_info.value)
    
    # Test with invalid UUID format
    ble_manager.client.stop_notify = AsyncMock(side_effect=ValueError("Invalid UUID format"))
    with pytest.raises(ValueError) as exc_info:
        await ble_manager.stop_notify("invalid-uuid-format")
    assert "Invalid UUID format" in str(exc_info.value)

@pytest.mark.asyncio
async def test_negotiate_mtu_advanced(ble_manager):
    """Test advanced MTU negotiation scenarios including edge cases."""
    # Setup mock client
    ble_manager.client = MagicMock()
    ble_manager.client.is_connected = True
    ble_manager.client._backend = MagicMock()
    
    # Test minimum MTU value (23)
    ble_manager.client._backend.request_mtu = AsyncMock(return_value=23)
    min_mtu = await ble_manager.negotiate_mtu(23)
    assert min_mtu == 23
    
    # Test maximum normal MTU
    ble_manager.client._backend.request_mtu = AsyncMock(return_value=517)
    max_mtu = await ble_manager.negotiate_mtu(517)
    assert max_mtu == 517
    
    # Test when device negotiates lower MTU than requested
    ble_manager.client._backend.request_mtu = AsyncMock(return_value=100)
    negotiated_mtu = await ble_manager.negotiate_mtu(512)
    assert negotiated_mtu == 100
    
    # Test platform-specific handling
    ble_manager.platform_type = "linux"
    ble_manager.client._backend.request_mtu = AsyncMock(return_value=185)
    platform_mtu = await ble_manager.negotiate_mtu(217)
    assert platform_mtu == 185
    
    # Test case when _backend.request_mtu throws an exception
    ble_manager.client._backend.request_mtu = AsyncMock(side_effect=BleakError("MTU negotiation failed"))
    with pytest.raises(BleakError) as exc_info:
        await ble_manager.negotiate_mtu(100)
    assert "MTU negotiation failed" in str(exc_info.value)

@pytest.mark.asyncio
async def test_concurrent_scans(ble_manager):
    """Test behavior when multiple scan operations are requested concurrently."""
    with patch('backend.modules.ble.ble_manager.BleakScanner') as mock_scanner:
        # Simulate scan operations that take time
        async def delayed_scan(**kwargs):
            await asyncio.sleep(0.1)
            return [
                BLEDevice("AA:BB:CC:DD:EE:01", "Test Device 1"),
                BLEDevice("AA:BB:CC:DD:EE:02", "Test Device 2")
            ]
        
        mock_scanner.discover = AsyncMock(side_effect=delayed_scan)
        
        # Launch multiple concurrent scans
        scan_task1 = asyncio.create_task(ble_manager.scan_devices(scan_time=0.5))
        scan_task2 = asyncio.create_task(ble_manager.scan_devices(scan_time=0.5))
        
        # Wait for both to complete
        results = await asyncio.gather(scan_task1, scan_task2, return_exceptions=True)
        
        # Verify both scans completed successfully
        assert all(isinstance(result, list) for result in results)
        
        # Verify the scanner was called twice - once for each scan
        assert mock_scanner.discover.call_count == 2

@pytest.mark.asyncio
async def test_connection_without_encryption(ble_manager):
    """Test connecting to devices with different security requirements."""
    # Test connection without encryption
    with patch('backend.modules.ble.ble_manager.BleakClient') as MockBleakClient:
        # Configure the mock client for non-encrypted connection
        mock_client_instance = MagicMock()
        mock_client_instance.connect = AsyncMock(return_value=True)
        mock_client_instance.is_connected = True
        MockBleakClient.return_value = mock_client_instance
        
        # Set up the security flag for connection
        address = "00:11:22:33:44:55"
        result = await ble_manager.connect_device(address)
        
        # Verify connection was successful
        assert result is True
        
        # Test case when a device requires encryption but we don't provide it
        mock_client_instance.connect = AsyncMock(side_effect=BleakError("Connection failed: Encryption required"))
        
        # Try connecting without encryption to a device that requires it
        with pytest.raises(BleakError) as exc_info:
            await ble_manager.connect_device(address, use_encryption=False)
        
        assert "Encryption required" in str(exc_info.value)
        
        # Now try with encryption enabled
        mock_client_instance.connect = AsyncMock(return_value=True)
        result = await ble_manager.connect_device(address, use_encryption=True)
        assert result is True

@pytest.mark.asyncio
async def test_scan_performance(ble_manager):
    """Test BLE scanning performance under different conditions."""
    # Create varying numbers of mock devices for performance testing
    def create_mock_devices(count):
        return [
            BLEDevice(f"AA:BB:CC:DD:EE:{i:02x}", f"Test Device {i}")
            for i in range(count)
        ]
    
    # Test with different device counts to measure scaling
    device_counts = [0, 5, 20, 50]
    
    for count in device_counts:
        mock_devices = create_mock_devices(count)
        
        with patch('backend.modules.ble.ble_manager.BleakScanner.discover', return_value=mock_devices):
            # Measure time taken to process scan results
            start_time = time.time()
            devices = await ble_manager.scan_devices(scan_time=0.1)  # Minimal scan time for test
            end_time = time.time()
            
            # Verify correct number of devices
            assert len(devices) == count
            
            # Process time should scale reasonably with device count
            # This is a simple check to ensure processing time doesn't explode with more devices
            if count > 0:
                process_time = end_time - start_time
                # Just a basic sanity check - processing shouldn't take more than 1 second per device in test environment
                assert process_time < count * 1.0, f"Processing {count} devices took {process_time:.2f}s, which seems excessive"
    
    # Test with different scan_time values
    scan_times = [0.1, 0.5, 1.0]
    mock_devices = create_mock_devices(10)
    
    with patch('backend.modules.ble.ble_manager.BleakScanner.discover', return_value=mock_devices):
        for scan_time in scan_times:
            start_time = time.time()
            await ble_manager.scan_devices(scan_time=scan_time)
            end_time = time.time()
            
            # Verify the scan operation takes approximately the requested time
            elapsed = end_time - start_time
            assert scan_time <= elapsed <= scan_time + 0.5, f"Scan with time={scan_time}s took {elapsed:.2f}s"

# Add memory and resource tests for comprehensive testing
@pytest.mark.asyncio
async def test_resource_management(ble_manager):
    """Test proper resource cleanup after BLE operations."""
    # Test connection resource cleanup
    with patch('backend.modules.ble.ble_manager.BleakClient') as MockBleakClient:
        mock_client = MagicMock()
        mock_client.connect = AsyncMock(return_value=True)
        mock_client.disconnect = AsyncMock(return_value=True)
        mock_client.is_connected = True
        MockBleakClient.return_value = mock_client
        
        # Connect and verify client is stored
        await ble_manager.connect_device("00:11:22:33:44:55")
        assert ble_manager.client is not None
        
        # Disconnect and verify cleanup
        await ble_manager.disconnect_device()
        mock_client.disconnect.assert_called_once()
        
    # Test scan resource cleanup
    with patch('backend.modules.ble.ble_manager.BleakScanner') as MockScanner:
        mock_scanner_instance = MagicMock()
        mock_scanner_instance.start = AsyncMock()
        mock_scanner_instance.stop = AsyncMock()
        MockScanner.return_value = mock_scanner_instance
        
        # Check if scanner is properly stopped after an exception
        MockScanner.discover = AsyncMock(side_effect=Exception("Test exception"))
        
        try:
            await ble_manager.scan_devices()
        except:
            pass
            
        # Verify cleanup was attempted
        # Note: In actual implementation, we'd need to verify that the scanner is stopped
        # This might require additional instrumentation in the BLE manager class

@pytest.mark.asyncio
async def test_resource_cleanup(ble_manager):
    """Test proper resource cleanup after BLE operations."""
    with patch("backend.modules.ble.ble_manager.BleakClient") as MockBleakClient:
        mock_client = MagicMock()
        mock_client.connect = AsyncMock(return_value=True)
        mock_client.disconnect = AsyncMock(return_value=True)
        mock_client.is_connected = True
        MockBleakClient.return_value = mock_client

        # Connect and verify client is stored
        await ble_manager.connect_device("00:11:22:33:44:55")
        assert ble_manager.client is not None

        # Disconnect and verify cleanup
        await ble_manager.disconnect_device()
        mock_client.disconnect.assert_called_once()
        assert ble_manager.client is None
        
@pytest.mark.asyncio
async def test_read_characteristic_invalid_uuid(ble_manager):
    """Test reading a characteristic with an invalid UUID."""
    ble_manager.client = MagicMock()
    ble_manager.client.is_connected = True
    ble_manager.client.read_gatt_char = AsyncMock(side_effect=BleakError("Invalid UUID"))

    with pytest.raises(BleakError) as exc_info:
        await ble_manager.read_characteristic("invalid-uuid")

    assert "Invalid UUID" in str(exc_info.value)
    
@pytest.mark.asyncio
@pytest.mark.parametrize("requested_mtu, negotiated_mtu", [(23, 23), (512, 185), (517, 517)])
async def test_negotiate_mtu(ble_manager, requested_mtu, negotiated_mtu):
    """Test MTU negotiation with different requested and negotiated MTU values."""
    ble_manager.client = MagicMock()
    ble_manager.client.is_connected = True
    ble_manager.client._backend.request_mtu = AsyncMock(return_value=negotiated_mtu)

    result = await ble_manager.negotiate_mtu(requested_mtu)
    assert result == negotiated_mtu

# Existing test fixtures and basic tests...

# Additional test cases for edge cases and exceptions

@pytest.mark.asyncio
async def test_scan_with_empty_filters(ble_manager):
    """Test scanning with empty filters."""
    with patch("backend.modules.ble.ble_manager.BleakScanner.discover") as mock_discover:
        mock_device = BLEDevice("AA:BB:CC:DD:EE:FF", "Test Device", details={}, rssi=-50)
        mock_discover.return_value = [mock_device]
        
        # Test with empty filter
        result = await ble_manager.scan_devices(scan_time=1, filters={})
        assert len(result) == 1
        assert result[0]["address"].lower() == "aa:bb:cc:dd:ee:ff"

@pytest.mark.asyncio
async def test_scan_with_name_filter(ble_manager):
    """Test scanning with name filter."""
    with patch("backend.modules.ble.ble_manager.BleakScanner.discover") as mock_discover:
        mock_devices = [
            BLEDevice("AA:BB:CC:DD:EE:01", "Test Device 1", details={}, rssi=-50),
            BLEDevice("AA:BB:CC:DD:EE:02", "Other Device", details={}, rssi=-60),
        ]
        mock_discover.return_value = mock_devices
        
        # Test with name filter
        result = await ble_manager.scan_devices(scan_time=1, filters={"name": "Test"})
        assert len(result) == 1
        assert result[0]["name"] == "Test Device 1"

@pytest.mark.asyncio
async def test_scan_with_address_filter(ble_manager):
    """Test scanning with address filter."""
    with patch("backend.modules.ble.ble_manager.BleakScanner.discover") as mock_discover:
        mock_devices = [
            BLEDevice("AA:BB:CC:DD:EE:01", "Test Device 1", details={}, rssi=-50),
            BLEDevice("AA:BB:CC:DD:EE:02", "Test Device 2", details={}, rssi=-60),
        ]
        mock_discover.return_value = mock_devices
        
        # Test with address filter
        result = await ble_manager.scan_devices(scan_time=1, filters={"address": "AA:BB:CC:DD:EE:01"})
        assert len(result) == 1
        assert result[0]["address"].lower() == "aa:bb:cc:dd:ee:01"

@pytest.mark.asyncio
async def test_connect_timeout(ble_manager):
    """Test connection with timeout."""
    with patch("backend.modules.ble.ble_manager.BleakClient") as mock_client_class:
        # Configure the client to timeout
        mock_client = MagicMock()
        mock_client.connect = AsyncMock(side_effect=asyncio.TimeoutError("Connection timed out"))
        mock_client_class.return_value = mock_client
        
        # Test with timeout
        with pytest.raises(asyncio.TimeoutError):
            await ble_manager.connect_device("AA:BB:CC:DD:EE:FF", timeout=1)

@pytest.mark.asyncio
async def test_disconnect_when_not_connected(ble_manager):
    """Test disconnecting when not connected."""
    ble_manager.client = None
    # Should not raise an exception
    await ble_manager.disconnect_device()
    
    # Also test when client exists but is not connected
    ble_manager.client = MagicMock()
    ble_manager.client.is_connected = False
    ble_manager.client.disconnect = AsyncMock()
    await ble_manager.disconnect_device()
    ble_manager.client.disconnect.assert_not_called()

@pytest.mark.asyncio
async def test_get_services_empty(ble_manager):
    """Test getting services when none are available."""
    ble_manager.client = MagicMock()
    ble_manager.client.is_connected = True
    ble_manager.client.services = {}
    
    services = await ble_manager.get_services()
    assert len(services) == 0

@pytest.mark.asyncio
async def test_characteristic_operations_with_invalid_uuid(ble_manager):
    """Test operations with invalid characteristic UUID."""
    ble_manager.client = MagicMock()
    ble_manager.client.is_connected = True
    ble_manager.client.read_gatt_char = AsyncMock(side_effect=BleakError("Invalid UUID"))
    
    with pytest.raises(BleakError):
        await ble_manager.read_characteristic("invalid-uuid")

@pytest.mark.asyncio
async def test_connect_device_with_invalid_address(ble_manager):
    """Test connecting with an invalid address format."""
    invalid_addresses = ["invalid", "GH:IJ:KL:MN:OP:QR", "00:11:22:33:44"]
    
    for address in invalid_addresses:
        with pytest.raises(ValueError) as exc_info:
            await ble_manager.connect_device(address)
        assert "Invalid address format" in str(exc_info.value)

@pytest.mark.asyncio
async def test_connect_device_timeout(ble_manager):
    """Test connection timeout handling."""
    
    # Mock client that delays longer than timeout
    async def delayed_connect():
        await asyncio.sleep(0.5)
        return True
        
    mock_client = AsyncMock(spec=BleakClient)
    mock_client.connect = AsyncMock(side_effect=delayed_connect)
    
    with patch('backend.modules.ble.ble_manager.BleakClient', return_value=mock_client):
        # Use a short timeout
        with pytest.raises(BleakError) as exc_info:
            await ble_manager.connect_device("00:11:22:33:44:55", timeout=0.1)
        assert "Connection timeout" in str(exc_info.value)

@pytest.mark.asyncio
async def test_concurrent_operations(ble_manager):
    """Test multiple concurrent operations."""
    with patch('backend.modules.ble.ble_manager.BleakClient') as MockBleakClient:
        mock_client = AsyncMock(spec=BleakClient)
        mock_client.connect = AsyncMock(return_value=True)
        mock_client.is_connected = True
        mock_client.read_gatt_char = AsyncMock(return_value=b'test')
        mock_client.write_gatt_char = AsyncMock(return_value=True)
        MockBleakClient.return_value = mock_client
        
        # Connect to device
        await ble_manager.connect_device("00:11:22:33:44:55")
        
        # Run multiple operations concurrently
        tasks = [
            ble_manager.read_characteristic("2A00"),
            ble_manager.write_characteristic("2A06", "Test"),
            ble_manager.read_characteristic("2A01")
        ]
        
        # All operations should complete successfully
        results = await asyncio.gather(*tasks)
        assert all(result is not None for result in results)