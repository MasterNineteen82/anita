import pytest
from unittest.mock import AsyncMock, patch
from backend.modules.ble.core.device_manager import BleDeviceManager

@pytest.mark.asyncio
async def test_scan_devices():
    device_manager = BleDeviceManager()
    with patch("backend.modules.ble.core.device_manager.BleakScanner.discover", return_value=[]):
        devices = await device_manager.scan_devices(scan_time=1.0)
        assert isinstance(devices, list)
        assert len(devices) == 0

@pytest.mark.asyncio
async def test_connect_device():
    device_manager = BleDeviceManager()
    with patch("backend.modules.ble.core.device_manager.BleakClient.connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = True
        result = await device_manager.connect_device("00:11:22:33:44:55")
        assert result is True

@pytest.mark.asyncio
async def test_disconnect_device():
    device_manager = BleDeviceManager()
    with patch("backend.modules.ble.core.device_manager.BleakClient.disconnect", new_callable=AsyncMock) as mock_disconnect:
        # Simulate a connected device
        device_manager._connected_devices["00:11:22:33:44:55"] = AsyncMock()
        mock_disconnect.return_value = True
        result = await device_manager.disconnect_device("00:11:22:33:44:55")
        assert result is True

def test_get_cached_devices():
    device_manager = BleDeviceManager()
    device_manager._cached_devices = [{"name": "Test Device", "address": "00:11:22:33:44:55"}]
    cached_devices = device_manager.get_cached_devices()
    assert isinstance(cached_devices, list)
    assert len(cached_devices) == 1
    assert cached_devices[0]["name"] == "Test Device"

def test_get_connected_devices():
    device_manager = BleDeviceManager()
    device_manager._connected_devices = {"00:11:22:33:44:55": AsyncMock()}
    connected_devices = device_manager.get_connected_devices()
    assert isinstance(connected_devices, list)
    assert len(connected_devices) == 1
    assert connected_devices[0] == "00:11:22:33:44:55"