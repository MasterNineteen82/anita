from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel
import logging
from backend.modules.rfid_manager import RFIDManager
from backend.logging.logging_config import get_api_logger
from ..utils import handle_errors
from backend.models import RFIDTagDataRequest, RFIDConfigRequest

# Add router definition before any routes
router = APIRouter(tags=["RFID"])
logger = get_api_logger()

@router.get("/rfid/status", summary="Get RFID reader status")
@handle_errors
async def get_rfid_status():
    """Get the status of RFID readers"""
    result = await RFIDManager.get_status()
    return {"status": "success", "data": result}

@router.get("/rfid/tag", summary="Check if tag is present and read it")
@handle_errors
async def read_rfid_tag():
    """Check if an RFID tag is present and read its data."""
    with RFIDManager() as rfid:
        if not rfid.is_connected:
            raise HTTPException(status_code=503, detail="RFID reader not connected")
            
        is_present = rfid.is_tag_present()
        tag_data = rfid.read_tag() if is_present else None
        
        return {
            "status": "success",
            "data": {
                "tag_present": is_present,
                "tag_data": tag_data
            }
        }

@router.post("/rfid/write", summary="Write data to RFID tag")
@handle_errors
async def write_rfid_tag(request: RFIDTagDataRequest):
    """Write data to an RFID tag."""
    with RFIDManager() as rfid:
        if not rfid.is_connected:
            raise HTTPException(status_code=503, detail="RFID reader not connected")
            
        if not rfid.is_tag_present():
            raise HTTPException(status_code=404, detail="No RFID tag detected")
            
        success = rfid.write_tag(request.data)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to write data to tag")
            
        return {"status": "success", "message": "Data written to tag successfully"}
        
@router.post("/rfid/config", summary="Update RFID reader configuration")
@handle_errors
async def update_rfid_config(request: RFIDConfigRequest):
    with RFIDManager() as rfid:
        if not rfid.is_connected:
            raise HTTPException(status_code=503, detail="RFID reader not connected")
            
        rfid.set_config(request.config)
        return {"status": "success", "message": "RFID configuration updated"}