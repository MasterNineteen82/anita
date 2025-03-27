"""Test BLE device persistence functionality."""

import pytest
import json
import os
from unittest.mock import MagicMock, mock_open, patch
from backend.modules.ble.ble_persistence import BLEDeviceStorage

@pytest.fixture
def ble_storage():
    """Create a BLEDeviceStorage instance for testing."""
    return BLEDeviceStorage(logger=MagicMock())

def test_device_storage_initialization(ble_storage):
    """Test initialization of device storage."""
    # Verify initial state
    assert isinstance(ble_storage.devices, dict)
    assert len(ble_storage.devices) == 0

def test_device_update_and_retrieval(ble_storage):
    """Test updating and retrieving device information."""
    # Update a device
    device_address = "00:11:22:33:44:55"
    updates = {
        "name": "Test Device",
        "rssi": -65,
        "services": ["1800", "1801"],
        "bonded": True
    }
    
    ble_storage.update_device(device_address, updates)
    
    # Retrieve the device
    device = ble_storage.get_device(device_address)
    
    # Verify device information
    assert device is not None
    assert device["address"] == device_address
    assert device["name"] == "Test Device"
    assert device["rssi"] == -65
    assert device["services"] == ["1800", "1801"]
    assert device["bonded"] is True

def test_get_nonexistent_device(ble_storage):
    """Test retrieving a device that doesn't exist."""
    device = ble_storage.get_device("nonexistent")
    assert device is None

def test_list_devices(ble_storage):
    """Test listing all devices."""
    # Add multiple devices
    devices_data = {
        "00:11:22:33:44:55": {"name": "Device 1", "bonded": True},
        "AA:BB:CC:DD:EE:FF": {"name": "Device 2", "bonded": False},
        "11:22:33:44:55:66": {"name": "Device 3", "bonded": True}
    }
    
    for address, data in devices_data.items():
        ble_storage.update_device(address, data)
    
    # List all devices
    all_devices = ble_storage.list_devices()
    
    # Verify results
    assert len(all_devices) == 3
    
    # Verify device addresses
    addresses = [d["address"] for d in all_devices]
    assert "00:11:22:33:44:55" in addresses
    assert "AA:BB:CC:DD:EE:FF" in addresses
    assert "11:22:33:44:55:66" in addresses

def test_list_bonded_devices(ble_storage):
    """Test listing only bonded devices."""
    # Add multiple devices with different bonding states
    devices_data = {
        "00:11:22:33:44:55": {"name": "Device 1", "bonded": True},
        "AA:BB:CC:DD:EE:FF": {"name": "Device 2", "bonded": False},
        "11:22:33:44:55:66": {"name": "Device 3", "bonded": True}
    }
    
    for address, data in devices_data.items():
        ble_storage.update_device(address, data)
    
    # List only bonded devices
    bonded_devices = ble_storage.list_bonded_devices()
    
    # Verify results
    assert len(bonded_devices) == 2
    
    # Verify bonded status
    for device in bonded_devices:
        assert device["bonded"] is True

def test_remove_device(ble_storage):
    """Test removing a device."""
    # Add a device
    device_address = "00:11:22:33:44:55"
    ble_storage.update_device(device_address, {"name": "Test Device"})
    
    # Verify device exists
    assert ble_storage.get_device(device_address) is not None
    
    # Remove the device
    ble_storage.remove_device(device_address)
    
    # Verify device was removed
    assert ble_storage.get_device(device_address) is None

def test_persistence_save_load():
    """Test saving and loading device data from file."""
    # Mock filesystem operations
    mock_data = {
        "00:11:22:33:44:55": {"address": "00:11:22:33:44:55", "name": "Device 1", "bonded": True},
        "AA:BB:CC:DD:EE:FF": {"address": "AA:BB:CC:DD:EE:FF", "name": "Device 2", "bonded": False}
    }
    
    # Mock file operations
    with patch('builtins.open', mock_open()) as m, \
         patch('json.dump') as mock_json_dump, \
         patch('os.path.exists', return_value=True), \
         patch('json.load', return_value=mock_data):
        
        # Create storage instance
        storage = BLEDeviceStorage(logger=MagicMock())
        
        # Save data
        storage.save_devices()
        mock_json_dump.assert_called_once()
        
        # Load data
        storage.load_devices()
        
        # Verify loaded data
        assert len(storage.devices) == 2
        assert "00:11:22:33:44:55" in storage.devices
        assert "AA:BB:CC:DD:EE:FF" in storage.devices

def test_persistence_file_not_found():
    """Test loading when file doesn't exist."""
    # Mock file not found
    with patch('os.path.exists', return_value=False), \
         patch('builtins.open', mock_open()) as m:
        
        # Create storage instance
        storage = BLEDeviceStorage(logger=MagicMock())
        
        # Load data (should not raise exception)
        storage.load_devices()
        
        # Verify empty devices dictionary
        assert len(storage.devices) == 0

def test_persistence_error_handling():
    """Test error handling during file operations."""
    # Mock file operation errors
    with patch('builtins.open', side_effect=IOError("File error")), \
         patch('os.path.exists', return_value=True):
        
        # Create storage instance
        storage = BLEDeviceStorage(logger=MagicMock())
        
        # Load data (should not raise exception)
        storage.load_devices()
        
        # Verify logger was called with error
        storage.logger.error.assert_called_once()
        
        # Save data (should not raise exception)
        storage.save_devices()
        
        # Verify logger was called again
        assert storage.logger.error.call_count == 2