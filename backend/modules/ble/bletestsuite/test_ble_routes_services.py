import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.modules.ble.ble_routes import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)

@pytest.mark.asyncio
async def test_get_ble_services():
    """Test retrieving BLE services."""
    mock_adapter = MagicMock()
    mock_adapter.get_services = AsyncMock(return_value=[
        {"uuid": "1800", "description": "Generic Access"},
        {"uuid": "1801", "description": "Generic Attribute"}
    ])
    
    with patch("backend.modules.ble.ble_routes.get_ble_service", return_value=mock_adapter):
        response = client.get("/api/ble/services")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["uuid"] == "1800"

@pytest.mark.asyncio
async def test_read_characteristic():
    """Test reading a characteristic."""
    mock_adapter = MagicMock()
    mock_adapter.read_characteristic = AsyncMock(return_value={
        "value": "48656c6c6f", 
        "text": "Hello"
    })
    
    with patch("backend.modules.ble.ble_routes.get_ble_service", return_value=mock_adapter):
        response = client.get("/api/ble/characteristic/2a00/read")
        assert response.status_code == 200
        data = response.json()
        assert data["value"] == "48656c6c6f"
        assert data["text"] == "Hello"