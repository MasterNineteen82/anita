import pytest
from unittest.mock import AsyncMock, patch
from backend.modules.ble.core.ble_service import BleService

@pytest.mark.asyncio
async def test_scan_devices():
    ble_service = BleService()
    with patch("backend.modules.ble.core.device_manager.BleDeviceManager.scan_devices", new_callable=AsyncMock) as mock_scan:
        mock_scan.return_value = [{"name": "Test Device", "address": "00:11:22:33:44:55"}]
        devices = await ble_service.scan_devices(scan_time=1.0)
        assert isinstance(devices, list)
        assert len(devices) == 1
        assert devices[0]["name"] == "Test Device"

@pytest.mark.asyncio
async def test_connect_device():
    ble_service = BleService()
    with patch("backend.modules.ble.core.device_manager.BleDeviceManager.connect_device", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = True
        result = await ble_service.connect_device("00:11:22:33:44:55")
        assert result["status"] == "connected"
        assert result["address"] == "00:11:22:33:44:55"

@pytest.mark.asyncio
async def test_disconnect_device():
    ble_service = BleService()
    with patch("backend.modules.ble.core.device_manager.BleDeviceManager.disconnect_device", new_callable=AsyncMock) as mock_disconnect:
        mock_disconnect.return_value = True
        result = await ble_service.disconnect_device("00:11:22:33:44:55")
        assert result["status"] == "disconnected"
        assert result["address"] == "00:11:22:33:44:55"