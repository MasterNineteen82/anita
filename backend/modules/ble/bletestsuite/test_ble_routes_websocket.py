import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.modules.ble.ble_routes import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)

@pytest.mark.asyncio
async def test_subscribe_to_characteristic():
    """Test subscribing to characteristic notifications."""
    mock_adapter = MagicMock()
    mock_adapter.start_notify = AsyncMock(return_value=True)
    
    with patch("backend.modules.ble.ble_routes.get_ble_adapter", return_value=mock_adapter):
        # Testing WebSocket subscribe message
        with client.websocket_connect("/ws/ble") as websocket:
            websocket.send_json({
                "action": "subscribe",
                "characteristic": "2a00",
                "client_id": "test_client"
            })
            response = websocket.receive_json()
            assert response["success"] is True