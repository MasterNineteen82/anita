import logging
from typing import Dict, Any, Optional
import json
import time

logger = logging.getLogger(__name__)

class AuthManager:
    """
    Manager class for authentication operations.
    """
    
    @staticmethod
    async def authenticate(username: str, password: str) -> Dict[str, Any]:
        """
        Authenticate a user with username and password.
        
        Args:
            username: The username to authenticate
            password: The password to authenticate
            
        Returns:
            Dict containing authentication results
        """
        # Simple demo authentication
        if username == "demo" and password == "password":
            return {
                "status": "success",
                "data": {
                    "token": f"demo_token_{int(time.time())}",
                    "user": {
                        "id": "user_001",
                        "username": username,
                        "role": "admin"
                    }
                }
            }
        else:
            logger.warning(f"Failed authentication attempt for user: {username}")
            return {
                "status": "error",
                "message": "Invalid username or password"
            }
    
    @staticmethod
    async def validate_token(token: str) -> Dict[str, Any]:
        """
        Validate an authentication token.
        
        Args:
            token: The token to validate
            
        Returns:
            Dict containing token validation results
        """
        # Demo token validation
        if token and token.startswith("demo_token_"):
            return {
                "status": "success",
                "data": {
                    "valid": True,
                    "user": {
                        "id": "user_001",
                        "username": "demo",
                        "role": "admin"
                    }
                }
            }
        else:
            return {
                "status": "error",
                "message": "Invalid token"
            }
    
    @staticmethod
    async def register_user(username: str, password: str, email: str = None) -> Dict[str, Any]:
        """
        Register a new user.
        
        Args:
            username: The username for the new user
            password: The password for the new user
            email: Optional email for the user
            
        Returns:
            Dict containing registration results
        """
        return {
            "status": "success",
            "data": {
                "user_id": f"user_{int(time.time())}",
                "username": username,
                "email": email,
                "message": "User registered successfully"
            }
        }