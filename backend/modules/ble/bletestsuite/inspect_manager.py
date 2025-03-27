"""Script to inspect BLE Manager implementation."""
import asyncio
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.modules.ble.ble_manager import BLEManager
from unittest.mock import AsyncMock, MagicMock

async def inspect_get_services():
    """Inspect the get_services method."""
    ble_manager = BLEManager()
    
    # Mock the client
    mock_client = AsyncMock()
    mock_client.is_connected = True
    
    # Create mock service objects that match what's expected
    mock_service1 = MagicMock()
    mock_service1.uuid = "0000180d-0000-1000-8000-00805f9b34fb"
    mock_service1.description = "Heart Rate Service"
    
    mock_service2 = MagicMock()
    mock_service2.uuid = "0000180f-0000-1000-8000-00805f9b34fb"
    mock_service2.description = "Battery Service"
    
    # Create a BleakGATTServiceCollection mock
    mock_services = MagicMock()
    mock_services.services = {
        "0000180d-0000-1000-8000-00805f9b34fb": mock_service1,
        "0000180f-0000-1000-8000-00805f9b34fb": mock_service2
    }
    mock_services.get_service = lambda uuid: mock_services.services.get(uuid)
    
    # Assign to client
    mock_client.services = mock_services
    ble_manager.client = mock_client
    
    # Call the method we're testing
    services = await ble_manager.get_services()
    print(f"get_services returned: {type(services)}")
    print(f"Content: {services}")

asyncio.run(inspect_get_services())