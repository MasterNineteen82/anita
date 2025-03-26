import binascii
import base64
import logging
import json
from typing import Dict, Any, Optional, Callable, Tuple
from functools import wraps
from Cryptodome.Cipher import AES, DES, DES3
from Cryptodome.Util.Padding import pad, unpad
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from jsonschema import validate, ValidationError, SchemaError  # Import JSON Schema validator

# Configure logging (if not already configured)
logger = logging.getLogger(__name__)

class DataConverter:
    """
    A class for converting data between different formats such as hex, ASCII, and base64.
    """

    @staticmethod
    def convert(input_data: str, conversion_type: str) -> Dict[str, Any]:
        """
        Converts the input data to the specified conversion type.

        Args:
            input_data (str): The data to convert.
            conversion_type (str): The type of conversion to perform.
                Supported types: 'hex-to-ascii', 'ascii-to-hex', 'hex-to-base64', 'base64-to-hex'.

        Returns:
            dict: A dictionary containing the status and result of the conversion.
                Returns {'status': 'success', 'result': converted_data} on success,
                or {'status': 'error', 'message': error_message} on failure.
        """
        try:
            if not isinstance(input_data, str):
                raise TypeError("Input data must be a string.")

            if not input_data:
                return {'status': 'warning', 'message': 'Input data is empty.'}

            if conversion_type == 'hex-to-ascii':
                # Convert hex string to ASCII
                try:
                    ascii_string = binascii.unhexlify(input_data).decode('ascii', errors='ignore')
                    return {'status': 'success', 'result': ascii_string}
                except binascii.Error as e:
                    return {'status': 'error', 'message': f"Invalid hex input: {e}"}
                except UnicodeDecodeError as e:
                    return {'status': 'error', 'message': f"Unicode decode error: {e}"}

            elif conversion_type == 'ascii-to-hex':
                # Convert ASCII string to hex
                try:
                    hex_string = binascii.hexlify(input_data.encode('ascii')).decode('utf-8').upper()
                    return {'status': 'success', 'result': hex_string}
                except UnicodeEncodeError as e:
                    return {'status': 'error', 'message': f"ASCII encode error: {e}"}

            elif conversion_type == 'hex-to-base64':
                # Convert hex string to base64
                try:
                    base64_string = base64.b64encode(binascii.unhexlify(input_data)).decode('utf-8')
                    return {'status': 'success', 'result': base64_string}
                except binascii.Error as e:
                    return {'status': 'error', 'message': f"Invalid hex input: {e}"}

            elif conversion_type == 'base64-to-hex':
                # Convert base64 string to hex
                try:
                    hex_string = binascii.hexlify(base64.b64decode(input_data)).decode('utf-8').upper()
                    return {'status': 'success', 'result': hex_string}
                except base64.binascii.Error as e:  # Correct exception type
                    return {'status': 'error', 'message': f"Invalid base64 input: {e}"}

            else:
                return {'status': 'error', 'message': 'Unsupported conversion type'}

        except TypeError as e:
            return {'status': 'error', 'message': str(e)}
        except Exception as e:
            logger.exception("An unexpected error occurred during data conversion.")
            return {'status': 'error', 'message': f"An unexpected error occurred: {e}"}


class Cryptography:
    """
    A class for performing cryptographic operations such as encryption and decryption using AES, DES, and 3DES algorithms.
    """

    @staticmethod
    def perform_crypto(crypto_type: str, key: str, iv: str, data: str) -> Dict[str, Any]:
        """
        Performs the specified cryptographic operation.

        Args:
            crypto_type (str): The type of cryptographic operation to perform.
                Supported types: 'des-encrypt', 'des-decrypt', 'des3-encrypt', 'des3-decrypt', 'aes-encrypt', 'aes-decrypt'.
            key (str): The encryption/decryption key in hexadecimal format.
            iv (str): The initialization vector in hexadecimal format.
            data (str): The data to encrypt/decrypt in hexadecimal format.

        Returns:
            dict: A dictionary containing the status and result of the cryptographic operation.
                Returns {'status': 'success', 'result': encrypted/decrypted_data} on success,
                or {'status': 'error', 'message': error_message} on failure.
        """
        # Validate inputs
        if not all([crypto_type, key, data]):  # iv can be optional
            return {'status': 'error', 'message': "Missing required parameters: type, key, or data"}

        if not isinstance(key, str) or not isinstance(data, str):
            return {'status': 'error', 'message': "Key and data must be strings."}

        if iv and not isinstance(iv, str):
            return {'status': 'error', 'message': "IV must be a string."}

        try:
            key_bytes = binascii.unhexlify(key.replace(' ', ''))
            data_bytes = binascii.unhexlify(data.replace(' ', ''))
            iv_bytes = binascii.unhexlify(iv.replace(' ', '')) if iv else b'\0' * 8  # Default IV for DES/3DES

        except binascii.Error as e:
            return {'status': 'error', 'message': f"Invalid hex input: {e}"}

        # Add length checks and algorithm selection
        try:
            if crypto_type in ['des-encrypt', 'des-decrypt']:
                if len(key_bytes) != 8:
                    return {'status': 'error', 'message': "DES requires an 8-byte key"}
                if len(iv_bytes) != 8:
                    return {'status': 'error', 'message': "DES requires an 8-byte IV"}
                cipher = DES.new(key_bytes, DES.MODE_CBC, iv_bytes)
                block_size = DES.block_size
            elif crypto_type in ['des3-encrypt', 'des3-decrypt']:
                if len(key_bytes) != 24:
                    return {'status': 'error', 'message': "3DES requires a 24-byte key"}
                if len(iv_bytes) != 8:
                    return {'status': 'error', 'message': "3DES requires an 8-byte IV"}
                cipher = DES3.new(key_bytes, DES3.MODE_CBC, iv_bytes)
                block_size = DES3.block_size
            elif crypto_type in ['aes-encrypt', 'aes-decrypt']:
                if len(key_bytes) not in [16, 24, 32]:
                    return {'status': 'error', 'message': "AES requires a 16, 24, or 32-byte key"}
                if len(iv_bytes) != 16:
                    return {'status': 'error', 'message': "AES requires a 16-byte IV"}
                cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
                block_size = AES.block_size
            else:
                return {'status': 'error', 'message': "Unsupported crypto operation"}

            # Encryption/Decryption
            if 'encrypt' in crypto_type:
                padded_data = pad(data_bytes, block_size)
                try:
                    result = cipher.encrypt(padded_data)
                except ValueError as e:
                    return {'status': 'error', 'message': f"Encryption error: {e}"}
            else:  # decrypt
                try:
                    result = cipher.decrypt(data_bytes)
                    result = unpad(result, block_size)
                except ValueError as e:
                    return {'status': 'error', 'message': "Incorrect padding or invalid data"}
                except Exception as e:
                    return {'status': 'error', 'message': f"Decryption error: {e}"}

            return {'status': 'success', 'result': binascii.hexlify(result).decode().upper()}

        except Exception as e:
            logger.exception("An unexpected error occurred during cryptographic operation.")
            return {'status': 'error', 'message': f"An unexpected error occurred: {e}"}

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

def handle_errors(func: Callable) -> Callable:
    """
    Decorator that wraps API endpoints to handle exceptions uniformly.
    """
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise  # Re-raise HTTPExceptions for FastAPI to handle
        except Exception as e:
            logger.exception(f"Error in {func.__name__}")  # Log the full exception
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": f"Internal server error: {e}"}
            )
    return wrapper

def validate_json(schema: dict) -> Callable:
    """
    Validates the JSON data in a request body against a specified schema using jsonschema.

    Args:
        schema (dict): A dictionary defining the JSON schema.

    Returns:
        A decorator that can be applied to a FastAPI route.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request: Request = kwargs.get('request')  # Type hint for request
            if not request:
                raise ValueError("Request object not found in arguments")

            try:
                data: Any = await request.json()  # Type hint for data
            except (TypeError, ValueError) as e:
                return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid JSON format"})

            try:
                validate(instance=data, schema=schema)
            except ValidationError as e:
                return JSONResponse(status_code=400, content={"status": "error", "message": f"Validation error: {e.message}"})
            except SchemaError as e:
                logger.error(f"Invalid JSON schema: {e}")
                return JSONResponse(status_code=500, content={"status": "error", "message": "Invalid JSON schema"})
                
            # Pass the data along to the function
            return await func(*args, **kwargs)
        return wrapper  # Changed from 'return decorator' to 'return wrapper'
    return decorator