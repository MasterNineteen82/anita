from fastapi import APIRouter, HTTPException, Depends, Request, Body, Form
from fastapi.security import OAuth2PasswordRequestForm
from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging

from backend.auth.auth_manager import AuthManager
from backend.auth.anti_spoofing_manager import AntiSpoofingManager
from backend.auth.blockchain_auth import BlockchainAuth
from backend.models import SuccessResponse, ErrorResponse
from backend.models import LogRequest, Settings
from backend.security.jwt_handler import signJWT  # Changed import
from ..utils import handle_errors, validate_json

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

class BlockchainAuthRequest(BaseModel):
    wallet_address: str
    signature: str
    message: str

@router.post("/auth/login", summary="Authenticate user")
@handle_errors
async def login(request: LoginRequest):
    """Log in a user with username and password."""
    result = await AuthManager.authenticate(request.username, request.password)
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=401, detail=result.message)
    access_token = signJWT(request.username)  # Changed function call
    return access_token

@router.post("/auth/blockchain", summary="Authenticate with blockchain")
@handle_errors
async def blockchain_auth(request: BlockchainAuthRequest):
    """Authenticate using blockchain signature."""
    result = await BlockchainAuth.verify_signature(
        request.wallet_address,
        request.signature,
        request.message
    )
    return result

@router.get("/auth/spoof-check", summary="Run anti-spoofing check")
@handle_errors
async def spoof_check():
    """Run anti-spoofing verification."""
    result = await AntiSpoofingManager.verify()
    return {"status": "success", "data": result}