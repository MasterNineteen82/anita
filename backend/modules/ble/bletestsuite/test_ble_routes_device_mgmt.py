import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.modules.ble.ble_routes import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)

@pytest.mark.asyncio
async def test_bond_device():
    """Test bonding with a device."""
    mock_storage = MagicMock()
    mock_storage.add_bonded_device = AsyncMock(return_value=True)
    
    with patch("backend.modules.ble.ble_routes.get_device_storage", return_value=mock_storage):
        response = client.post("/api/ble/bond", json={"address": "00:11:22:33:44:55"})
        assert response.status_code == 200
        assert response.json()["success"] is True

@pytest.mark.asyncio
async def test_get_bonded_devices():
    """Test retrieving bonded devices."""
    mock_storage = MagicMock()
    mock_storage.get_bonded_devices = AsyncMock(return_value=[
        {"address": "00:11:22:33:44:55", "name": "Bonded Device 1"}
    ])
    
    with patch("backend.modules.ble.ble_routes.get_device_storage", return_value=mock_storage):
        response = client.get("/api/ble/bonded")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["address"] == "00:11:22:33:44:55"