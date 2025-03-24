import jwt
import time
from typing import Dict, Optional, Any

from decouple import config


# Provide default values for development
JWT_SECRET = config("secret", default="your_secret_key_here")
JWT_ALGORITHM = config("algorithm", default="HS256")


def token_response(token: str) -> Dict[str, str]:
    return {
        "access_token": token
    }


def signJWT(userID: str) -> Dict[str, str]:
    payload = {
        "userID": userID,
        "expiry": time.time() + 600
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token_response(token)


def decodeJWT(token: str) -> Optional[Dict[str, Any]]:
    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return decoded_token if decoded_token["expiry"] >= time.time() else None
    except Exception as e:
        print(f"Error decoding JWT: {e}")  # Log the error
        return None