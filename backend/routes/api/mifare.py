from fastapi import APIRouter, HTTPException, Body, Request
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging
from backend.modules.mifare_manager import MifareManager
from backend.logging.logging_config import get_api_logger
from ..utils import handle_errors

def validate_json(*args, **kwargs):
    def decorator(func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Add router definition before any routes
router = APIRouter(tags=["mifare"])
logger = get_api_logger()

@router.post("/mifare/auth")
async def api_mifare_auth(request: Request):
    """Authenticate with a MIFARE Classic card."""
    data = await request.json()
    reader = data.get('reader', 0)
    sector = data.get('sector', 0)
    key_type = data.get('key_type', 'A')
    key = data.get('key', 'FFFFFFFFFFFF')
    return await MifareManager.mifare_auth(reader, sector, key_type, key)

@router.get("/mifare/read_block")
async def api_mifare_read_block(block: int = 0, reader: int = 0):
    """Read a block from a MIFARE Classic card."""
    return await MifareManager.mifare_read_block(reader, block)

@router.post("/mifare/write_block")
async def api_mifare_write_block(request: Request):
    """Write a block to a MIFARE Classic card."""
    data = await request.json()
    reader = data.get('reader', 0)
    block = data.get('block', 0)
    data_to_write = data.get('data', '')
    return await MifareManager.mifare_write_block(reader, block, data_to_write)

@router.get("/mifare/desfire/list_apps")
async def api_desfire_list_apps(reader: int = 0):
    """List applications on a DESFire card."""
    return await MifareManager.desfire_list_apps(reader)

@router.get("/mifare/desfire/list_files")
async def api_desfire_list_files(app_id: str = '000000', reader: int = 0):
    """List files in a DESFire application."""
    return await MifareManager.desfire_list_files(reader, app_id)

@router.post("/mifare/desfire/auth")
async def api_desfire_auth(request: Request):
    """Authenticate with a DESFire application."""
    data = await request.json()
    reader = data.get('reader', 0)
    app_id = data.get('app_id', '000000')
    key_no = data.get('key_no', 0)
    key = data.get('key', '0000000000000000')
    return await MifareManager.desfire_auth(reader, app_id, key_no, key)

@router.get("/mifare/desfire/read_file")
async def api_desfire_read_file(app_id: str = '000000', file_id: int = 0, reader: int = 0):
    """Read a file from a DESFire application."""
    return await MifareManager.desfire_read_file(reader, app_id, file_id)

@router.post("/mifare/desfire/write_file")
async def api_desfire_write_file(request: Request):
    """Write a file to a DESFire application."""
    data = await request.json()
    reader = data.get('reader', 0)
    app_id = data.get('app_id', '000000')
    file_id = data.get('file_id', 0)
    data_to_write = data.get('data', '')
    return await MifareManager.desfire_write_file(reader, app_id, file_id, data_to_write)

@router.post("/mifare/increment")
@handle_errors
@validate_json('reader', 'block', 'value')
async def api_mifare_increment(request: Request):
    """Increment a value block on a MIFARE card."""
    data = await request.json()
    reader = data.get('reader', 0)
    block = data.get('block', 0)
    value = data.get('value', 1)
    
    try:
        result = await MifareManager.mifare_increment_value(reader, block, value)
        return {"status": "success", "message": f"Value incremented by {value}", "data": result}
    except Exception as e:
        logger.error(f"Error incrementing value block: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

@router.post("/mifare/decrement")
@handle_errors
@validate_json('reader', 'block', 'value')
async def api_mifare_decrement(request: Request):
    """Decrement a value block on a MIFARE card."""
    data = await request.json()
    reader = data.get('reader', 0)
    block = data.get('block', 0)
    value = data.get('value', 1)
    
    try:
        result = await MifareManager.mifare_decrement_value(reader, block, value)
        return {"status": "success", "message": f"Value decremented by {value}", "data": result}
    except Exception as e:
        logger.error(f"Error decrementing value block: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}