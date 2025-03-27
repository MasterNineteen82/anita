import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.modules.ble.ble_routes import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)

@pytest.mark.asyncio
async def test_get_ble_metrics():
    """Test retrieving BLE metrics."""
    mock_metrics = MagicMock()
    mock_metrics.get_metrics = AsyncMock(return_value={
        "scan_count": 10,
        "connect_count": 5,
        "error_count": 2
    })
    
    with patch("backend.modules.ble.ble_routes.get_ble_metrics", return_value=mock_metrics):
        response = client.get("/api/ble/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["scan_count"] == 10
        assert data["connect_count"] == 5