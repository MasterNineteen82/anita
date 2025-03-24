from fastapi import APIRouter, HTTPException, Request, Form, Body
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging

from backend.logging.logging_config import get_api_logger
from ..utils import handle_errors
from backend.models import MifareKey, MifareClassicSector, MifareDESFireApplication
from backend.models import ErrorResponse, SuccessResponse, StatusResponse

# Define router with proper prefix and tags
router = APIRouter(tags=["mifare"])

# Get logger
logger = get_api_logger("mifare")

# Models for Mifare operations
class MifareKey(BaseModel):
    key_a: str
    key_b: Optional[str] = None

class MifareBlockData(BaseModel):
    data: str  # Hex string of data to write
    authenticate: bool = True
    key_type: str = "A"  # "A" or "B"
    key: Optional[str] = None

class MifareSectorData(BaseModel):
    sector: int
    blocks: Dict[int, str]  # Block number -> hex data
    authenticate: bool = True
    key_type: str = "A"  # "A" or "B"
    key: Optional[str] = None

# Routes for Mifare operations
@router.get("/mifare/info", summary="Get Mifare card info")
@handle_errors
async def get_mifare_info():
    """
    Get information about the Mifare card currently on the reader.
    
    Returns:
        Dictionary with status and card information.
    """
    # Mock implementation - would be replaced with actual hardware calls
    card_info = {
        "uid": "AA BB CC DD",
        "type": "MIFARE Classic 1K",
        "sectors": 16,
        "blocks_per_sector": 4,
        "block_size": 16
    }
    
    return {
        "status": "success",
        "data": card_info
    }

@router.get("/mifare/read/block/{block}", summary="Read Mifare block")
@handle_errors
async def read_mifare_block(
    block: int,
    authenticate: bool = True,
    key_type: str = "A",
    key: Optional[str] = None
):
    """
    Read data from a specific Mifare block.
    
    Args:
        block: The block number to read.
        authenticate: Whether to authenticate before reading.
        key_type: Key type to use for authentication (A or B).
        key: Authentication key (hex string).
        
    Returns:
        Dictionary with status and block data.
    """
    # Check block number validity
    if not 0 <= block <= 63:  # Assuming Mifare 1K with 64 blocks
        raise HTTPException(status_code=400, detail="Invalid block number")
    
    # Check key type validity
    if key_type not in ["A", "B"]:
        raise HTTPException(status_code=400, detail="Key type must be 'A' or 'B'")
    
    # Mock implementation - would be replaced with actual hardware calls
    # Generate some dummy data based on the block number
    import hashlib
    hash_obj = hashlib.md5(f"block{block}".encode())
    mock_data = hash_obj.hexdigest()[:32]  # 16 bytes = 32 hex chars
    
    return {
        "status": "success",
        "data": {
            "block": block,
            "data": mock_data,
            "data_ascii": bytes.fromhex(mock_data).decode('ascii', errors='replace')
        }
    }

@router.post("/mifare/write/block/{block}", summary="Write to Mifare block")
@handle_errors
async def write_mifare_block(
    block: int,
    data: MifareBlockData
):
    """
    Write data to a specific Mifare block.
    
    Args:
        block: The block number to write to.
        data: Block data and authentication parameters.
        
    Returns:
        Dictionary with status and write confirmation.
    """
    # Check block number validity
    if not 0 <= block <= 63:  # Assuming Mifare 1K with 64 blocks
        raise HTTPException(status_code=400, detail="Invalid block number")
    
    # Check if block is a sector trailer (every 4th block)
    if block % 4 == 3:
        logger.warning(f"Writing to sector trailer (block {block}). This can brick your card if not careful!")
    
    # Check key type validity
    if data.key_type not in ["A", "B"]:
        raise HTTPException(status_code=400, detail="Key type must be 'A' or 'B'")
    
    # Validate data length
    if len(data.data) != 32:  # 16 bytes = 32 hex chars
        raise HTTPException(status_code=400, detail="Data must be exactly 16 bytes (32 hex characters)")
    
    # Mock implementation - would be replaced with actual hardware calls
    return {
        "status": "success",
        "message": f"Data written to block {block} successfully",
        "data": {
            "block": block,
            "data": data.data
        }
    }

@router.get("/mifare/read/sector/{sector}", summary="Read Mifare sector")
@handle_errors
async def read_mifare_sector(
    sector: int,
    authenticate: bool = True,
    key_type: str = "A",
    key: Optional[str] = None
):
    """
    Read all blocks from a specific Mifare sector.
    
    Args:
        sector: The sector number to read.
        authenticate: Whether to authenticate before reading.
        key_type: Key type to use for authentication (A or B).
        key: Authentication key (hex string).
        
    Returns:
        Dictionary with status and sector data.
    """
    # Check sector number validity
    if not 0 <= sector <= 15:  # Assuming Mifare 1K with 16 sectors
        raise HTTPException(status_code=400, detail="Invalid sector number")
    
    # Check key type validity
    if key_type not in ["A", "B"]:
        raise HTTPException(status_code=400, detail="Key type must be 'A' or 'B'")
    
    # Mock implementation - would be replaced with actual hardware calls
    # Generate some dummy data for each block in the sector
    import hashlib
    
    # Calculate blocks in this sector
    first_block = sector * 4
    blocks_data = {}
    
    for block_offset in range(4):  # 4 blocks per sector
        block = first_block + block_offset
        hash_obj = hashlib.md5(f"block{block}".encode())
        mock_data = hash_obj.hexdigest()[:32]  # 16 bytes = 32 hex chars
        blocks_data[block] = {
            "data": mock_data,
            "data_ascii": bytes.fromhex(mock_data).decode('ascii', errors='replace')
        }
    
    return {
        "status": "success",
        "data": {
            "sector": sector,
            "blocks": blocks_data
        }
    }

@router.post("/mifare/write/sector", summary="Write to Mifare sector")
@handle_errors
async def write_mifare_sector(
    data: MifareSectorData
):
    """
    Write data to multiple blocks in a Mifare sector.
    
    Args:
        data: Sector data and authentication parameters.
        
    Returns:
        Dictionary with status and write confirmation.
    """
    # Check sector number validity
    if not 0 <= data.sector <= 15:  # Assuming Mifare 1K with 16 sectors
        raise HTTPException(status_code=400, detail="Invalid sector number")
    
    # Check key type validity
    if data.key_type not in ["A", "B"]:
        raise HTTPException(status_code=400, detail="Key type must be 'A' or 'B'")
    
    # Calculate blocks in this sector
    first_block = data.sector * 4
    last_block = first_block + 3
    
    # Validate block numbers
    for block_num in data.blocks.keys():
        if not first_block <= block_num <= last_block:
            raise HTTPException(
                status_code=400, 
                detail=f"Block {block_num} does not belong to sector {data.sector}"
            )
    
    # Check if writing to sector trailer
    if last_block in data.blocks:
        logger.warning(f"Writing to sector trailer (block {last_block}). This can brick your card if not careful!")
    
    # Validate data lengths
    for block_num, block_data in data.blocks.items():
        if len(block_data) != 32:  # 16 bytes = 32 hex chars
            raise HTTPException(
                status_code=400,
                detail=f"Data for block {block_num} must be exactly 16 bytes (32 hex characters)"
            )
    
    # Mock implementation - would be replaced with actual hardware calls
    return {
        "status": "success",
        "message": f"Data written to sector {data.sector} successfully",
        "data": {
            "sector": data.sector,
            "written_blocks": list(data.blocks.keys())
        }
    }

@router.post("/mifare/auth/keys", summary="Set authentication keys")
@handle_errors
async def set_mifare_keys(
    sector: int,
    keys: MifareKey
):
    """
    Set authentication keys for a Mifare sector.
    
    Args:
        sector: The sector number to set keys for.
        keys: Key A and optionally Key B.
        
    Returns:
        Dictionary with status and confirmation.
    """
    # Check sector number validity
    if not 0 <= sector <= 15:  # Assuming Mifare 1K with 16 sectors
        raise HTTPException(status_code=400, detail="Invalid sector number")
    
    # Validate key lengths
    if len(keys.key_a) != 12:  # 6 bytes = 12 hex chars
        raise HTTPException(status_code=400, detail="Key A must be exactly 6 bytes (12 hex characters)")
    
    if keys.key_b is not None and len(keys.key_b) != 12:
        raise HTTPException(status_code=400, detail="Key B must be exactly 6 bytes (12 hex characters)")
    
    # Mock implementation - would be replaced with actual hardware calls
    return {
        "status": "success",
        "message": f"Authentication keys set for sector {sector}",
        "data": {
            "sector": sector,
            "key_a_set": True,
            "key_b_set": keys.key_b is not None
        }
    }

@router.get("/mifare/value/{block}", summary="Read Mifare value block")
@handle_errors
async def read_mifare_value(
    block: int,
    authenticate: bool = True,
    key_type: str = "A",
    key: Optional[str] = None
):
    """
    Read value from a Mifare value block.
    
    Args:
        block: The block number to read from.
        authenticate: Whether to authenticate before reading.
        key_type: Key type to use for authentication (A or B).
        key: Authentication key (hex string).
        
    Returns:
        Dictionary with status and value.
    """
    # Check block number validity
    if not 0 <= block <= 63:  # Assuming Mifare 1K with 64 blocks
        raise HTTPException(status_code=400, detail="Invalid block number")
    
    # Check if block is a sector trailer (every 4th block)
    if block % 4 == 3:
        raise HTTPException(status_code=400, detail="Cannot use sector trailer as a value block")
    
    # Check key type validity
    if key_type not in ["A", "B"]:
        raise HTTPException(status_code=400, detail="Key type must be 'A' or 'B'")
    
    # Mock implementation - would be replaced with actual hardware calls
    import random
    
    # Generate a random value based on the block number
    random.seed(block)
    value = random.randint(-1000, 1000)
    
    return {
        "status": "success",
        "data": {
            "block": block,
            "value": value,
            "is_valid_value_block": True
        }
    }

@router.post("/mifare/value/{block}", summary="Write Mifare value block")
@handle_errors
async def write_mifare_value(
    block: int,
    value: int,
    authenticate: bool = True,
    key_type: str = "A",
    key: Optional[str] = None
):
    """
    Write value to a Mifare value block.
    
    Args:
        block: The block number to write to.
        value: The integer value to write.
        authenticate: Whether to authenticate before writing.
        key_type: Key type to use for authentication (A or B).
        key: Authentication key (hex string).
        
    Returns:
        Dictionary with status and write confirmation.
    """
    # Check block number validity
    if not 0 <= block <= 63:  # Assuming Mifare 1K with 64 blocks
        raise HTTPException(status_code=400, detail="Invalid block number")
    
    # Check if block is a sector trailer (every 4th block)
    if block % 4 == 3:
        raise HTTPException(status_code=400, detail="Cannot use sector trailer as a value block")
    
    # Check key type validity
    if key_type not in ["A", "B"]:
        raise HTTPException(status_code=400, detail="Key type must be 'A' or 'B'")
    
    # Mock implementation - would be replaced with actual hardware calls
    return {
        "status": "success",
        "message": f"Value {value} written to block {block} successfully",
        "data": {
            "block": block,
            "value": value
        }
    }