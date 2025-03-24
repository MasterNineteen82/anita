from fastapi import FastAPI, WebSocket
import logging
import asyncio
import json
import random
from datetime import datetime

from backend.modules.smartcard_manager import SmartcardManager
from backend.logging.logging_config import get_api_logger

# Create logger
logger = get_api_logger()

def register_websocket_routes(app: FastAPI):
    """Register WebSocket routes for smartcard operations."""
    
    @app.websocket("/ws/smartcard")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        logger.info("WebSocket connection established")
        
        try:
            # Send initial status
            await websocket.send_json({
                "status": "connected",
                "message": "WebSocket connection established"
            })
            
            # Simulation loop
            while True:
                # Simulate reader status
                reader_status = {
                    "timestamp": datetime.now().isoformat(),
                    "reader_count": 1,
                    "readers": [
                        {
                            "index": 0,
                            "name": "Simulated Reader",
                            "has_card": random.choice([True, False])
                        }
                    ]
                }
                
                # Send status update
                await websocket.send_json({
                    "type": "reader_status",
                    "data": reader_status
                })
                
                # Wait 2 seconds before next update
                await asyncio.sleep(2)
                
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
        finally:
            logger.info("WebSocket connection closed")
            try:
                await websocket.close()
            except:
                pass