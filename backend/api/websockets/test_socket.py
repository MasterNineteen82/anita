from fastapi import WebSocket, APIRouter
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws/test")
async def test_websocket(websocket: WebSocket):
    """Test WebSocket endpoint with no authentication."""
    await websocket.accept()
    logger.info("Test WebSocket connection accepted")
    
    await websocket.send_text(json.dumps({
        "type": "welcome",
        "message": "Test WebSocket connection established"
    }))
    
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(json.dumps({
                "type": "echo",
                "data": data
            }))
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")

@router.websocket("/ws/test-noauth")
async def test_websocket_noauth(websocket: WebSocket):
    """Test WebSocket endpoint with no authentication for testing."""
    await websocket.accept()
    
    await websocket.send_text(json.dumps({
        "type": "welcome",
        "message": "Test WebSocket connection established"
    }))
    
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(data)  # Echo back
    except Exception:
        pass