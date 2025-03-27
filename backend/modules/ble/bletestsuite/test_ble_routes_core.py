import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.modules.ble.ble_routes import router, get_ble_adapter

app = FastAPI()
app.include_router(router)
client = TestClient(app)

@pytest.mark.asyncio
async def test_scan_for_devices():
    """Test the scan_for_devices function."""
    mock_adapter = MagicMock()
    mock_adapter.scan_devices = AsyncMock(return_value=[
        {"address": "00:11:22:33:44:55", "name": "Test Device 1"},
        {"address": "AA:BB:CC:DD:EE:FF", "name": "Test Device 2"}
    ])
    
    with patch("backend.modules.ble.ble_routes.get_ble_service", return_value=mock_adapter):
        # Test API endpoint
        response = client.get("/api/ble/scan?timeout=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Test Device 1"

@pytest.mark.asyncio
async def test_connect_to_device():
    """Test connecting to a device."""
    mock_adapter = MagicMock()
    mock_adapter.connect_device = AsyncMock(return_value=True)
    
    with patch("backend.modules.ble.ble_routes.get_ble_service", return_value=mock_adapter):
        response = client.post("/api/ble/connect", json={"address": "00:11:22:33:44:55"})
        assert response.status_code == 200
        assert response.json()["success"] is True