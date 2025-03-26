from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import logging
from functools import wraps

from backend.modules.smartcard_manager import SmartcardManager
from backend.logging.logging_config import get_api_logger
from backend.models import StatusResponse, ErrorResponse, LogRequest, Settings
from ..utils import handle_errors
from backend.utils.utils import validate_json

# Create logger and router
logger = get_api_logger()
router = APIRouter(tags=["smartcard"])

@router.get("/smartcard/atr", response_model=Dict[str, Any])
@handle_errors
async def api_smartcard_atr(reader: int = 0):
    """Get the ATR of a smartcard."""
    logger.info(f"Getting ATR from reader {reader}")
    result = await SmartcardManager.get_atr(reader)
    return result

@router.post("/smartcard/transmit")
@handle_errors
@validate_json(schema={"required": ["apdu"]})
async def api_smartcard_transmit(request: Request):
    """Transmit an APDU command to a smartcard."""
    data = await request.json()
    reader = data.get('reader', 0)
    apdu = data.get('apdu')
    logger.info(f"Transmitting APDU to reader {reader}: {apdu}")
    result = await SmartcardManager.transmit_apdu(reader, apdu)
    return {"status": "success", "data": result}

@router.get("/smartcard/detect")
@handle_errors
async def api_detect_smartcard():
    """Detect smartcard presence."""
    logger.debug("Detecting smartcard presence")
    result = SmartcardManager.card_status()
    return {"status": "success", "data": result}

@router.get("/smartcard/card_status")
@handle_errors
async def api_card_status(reader: int = 0):
    """Check card status."""
    result = await SmartcardManager.card_status(reader)
    return result

@router.get("/smartcard/test_reader")
async def api_smartcard_test_reader(reader: int = 0):
    """Test the connection to a smartcard reader."""
    return SmartcardManager.test_reader_connection(reader)

@router.get("/readers")
@handle_errors
async def api_get_readers():
    """Get all available readers."""
    try:
        smartcard_manager = SmartcardManager()
        readers = smartcard_manager.get_readers()
        
        return {
            "status": "success", 
            "readers": readers,
            "selected_reader": readers[0] if readers else None
        }
    except Exception as e:
        logger.error(f"Error getting readers: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

@router.post("/apdu")
@validate_json(schema={"required": ["apdu"]})  # Provide a schema
@handle_errors
async def send_apdu(request: Request):
    """Send an APDU command to the smart card."""
    data = await request.json()
    apdu = data.get('apdu')
    if not apdu:
        raise HTTPException(status_code=400, detail="APDU command is required")
    response = await SmartcardManager.send_apdu(apdu)
    return {"response": response}