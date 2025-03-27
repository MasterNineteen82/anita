"""Test BLE API routes functionality."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.modules.ble.ble_routes import router
from backend.modules.ble.ble_manager import BLEManager

# Create a test client
app = FastAPI()
app.include_router(router)
client = TestClient(app)

@pytest.fixture
def ble_manager():
    """Create a mock BLEManager for testing routes."""
    manager = MagicMock(spec=BLEManager)
    manager.scan_devices = AsyncMock(return_value=[
        {"address": "00:11:22:33:44:55", "name": "Device 1", "rssi": -65},
        {"address": "AA:BB:CC:DD:EE:FF", "name": "Device 2", "rssi": -72}
    ])
    manager.connect_device = AsyncMock(return_value=True)
    manager.disconnect_device = AsyncMock(return_value=True)
    manager.get_services = AsyncMock(return_value=[
        {"uuid": "1800", "name": "Generic Access"},
        {"uuid": "1801", "name": "Generic Attribute"}
    ])
    return manager

@pytest.fixture
def client(ble_manager):
    """Create a test client for API routes."""
    from fastapi.testclient import TestClient
    
    # Override the BLEManager dependency in your router
    app = MagicMock()
    app.dependency_overrides = {
        BLEManager: lambda: ble_manager
    }
    
    return TestClient(app)

def test_get_adapter_status(client, ble_manager):
    """Test GET /ble/status endpoint."""
    # Mock adapter availability
    ble_manager.is_adapter_available = AsyncMock(return_value=True)
    
    # Call the route
    response = client.get("/ble/status")
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True

def test_scan_devices(client, ble_manager):
    """Test GET /ble/scan endpoint."""
    # Call the route
    response = client.get("/ble/scan")
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert len(data["devices"]) == 2
    assert data["devices"][0]["name"] == "Device 1"
    assert data["devices"][1]["address"] == "AA:BB:CC:DD:EE:FF"

def test_connect_device(client, ble_manager):
    """Test POST /ble/connect endpoint."""
    # Call the route
    response = client.post(
        "/ble/connect",
        json={"address": "00:11:22:33:44:55"}
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    
    # Verify manager method was called
    ble_manager.connect_device.assert_called_once_with("00:11:22:33:44:55")

def test_disconnect_device(client, ble_manager):
    """Test POST /ble/disconnect endpoint."""
    # Call the route
    response = client.post("/ble/disconnect")
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["disconnected"] is True
    
    # Verify manager method was called
    ble_manager.disconnect_device.assert_called_once()

def test_get_services(client, ble_manager):
    """Test GET /ble/services endpoint."""
    # Call the route
    response = client.get("/ble/services")
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert len(data["services"]) == 2
    assert data["services"][0]["uuid"] == "1800"
    assert data["services"][1]["name"] == "Generic Attribute"

def test_error_handling(client, ble_manager):
    """Test error handling in routes."""
    # Mock error in scan_devices
    ble_manager.scan_devices = AsyncMock(side_effect=Exception("Test error"))
    
    # Call the route
    response = client.get("/ble/scan")
    
    # Verify error response
    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert "Test error" in data["error"]

# Test getting adapter info
def test_get_adapter_info():
    """Test getting BLE adapter information."""
    with patch("backend.modules.ble.ble_routes.get_ble_adapter") as mock_adapter:
        mock_adapter.return_value = {
            "name": "Test Adapter",
            "address": "00:11:22:33:44:55",
            "available": True
        }
        
        response = client.get("/api/ble/adapter")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Adapter"
        assert data["address"] == "00:11:22:33:44:55"
        assert data["available"] is True

# Test scanning for devices
@pytest.mark.asyncio
async def test_scan_devices():
    """Test scanning for BLE devices."""
    with patch("backend.modules.ble.ble_routes.scan_for_devices") as mock_scan:
        mock_scan.return_value = [
            {"address": "00:11:22:33:44:55", "name": "Test Device 1", "rssi": -65},
            {"address": "AA:BB:CC:DD:EE:FF", "name": "Test Device 2", "rssi": -72}
        ]
        
        response = client.get("/api/ble/scan?timeout=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Test Device 1"
        assert data[1]["name"] == "Test Device 2"