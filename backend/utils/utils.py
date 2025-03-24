import binascii
import base64
import logging
import json
from typing import Dict, Any, Optional, Callable
from Cryptodome.Cipher import AES, DES, DES3
from Cryptodome.Util.Padding import pad, unpad

class DataConverter:
    """
    A class for converting data between different formats such as hex, ASCII, and base64.
    """

    @staticmethod
    def convert(input_data: str, conversion_type: str) -> Dict[str, str]:
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
                raise ValueError("Input data must be a string.")

            if conversion_type == 'hex-to-ascii':
                # Convert hex string to ASCII
                ascii_string = binascii.unhexlify(input_data).decode('ascii', errors='ignore')
                return {'status': 'success', 'result': ascii_string}
            elif conversion_type == 'ascii-to-hex':
                # Convert ASCII string to hex
                hex_string = binascii.hexlify(input_data.encode('ascii')).decode('utf-8').upper()
                return {'status': 'success', 'result': hex_string}
            elif conversion_type == 'hex-to-base64':
                # Convert hex string to base64
                base64_string = base64.b64encode(binascii.unhexlify(input_data)).decode('utf-8')
                return {'status': 'success', 'result': base64_string}
            elif conversion_type == 'base64-to-hex':
                # Convert base64 string to hex
                hex_string = binascii.hexlify(base64.b64decode(input_data)).decode('utf-8').upper()
                return {'status': 'success', 'result': hex_string}
            else:
                return {'status': 'error', 'message': 'Unsupported conversion type'}

        except binascii.Error as e:
            return {'status': 'error', 'message': f"Invalid hex input: {e}"}
        except UnicodeDecodeError as e:
            return {'status': 'error', 'message': f"Unicode decode error: {e}"}
        except ValueError as e:
            return {'status': 'error', 'message': str(e)}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}


class Cryptography:
    """
    A class for performing cryptographic operations such as encryption and decryption using AES, DES, and 3DES algorithms.
    """

    @staticmethod
    def perform_crypto(crypto_type: str, key: str, iv: str, data: str) -> Dict[str, str]:
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

        try:
            key_bytes = binascii.unhexlify(key.replace(' ', ''))
            data_bytes = binascii.unhexlify(data.replace(' ', ''))
            if iv:
                iv_bytes = binascii.unhexlify(iv.replace(' ', ''))
            else:
                iv_bytes = b'\0' * 8  # Default IV for DES/3DES

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
                result = cipher.encrypt(padded_data)
            else:  # decrypt
                result = cipher.decrypt(data_bytes)
                try:
                    result = unpad(result, block_size)
                except ValueError:
                    return {'status': 'error', 'message': "Incorrect padding"}

            return {'status': 'success', 'result': binascii.hexlify(result).decode().upper()}

        except Exception as e:
            return {'status': 'error', 'message': str(e)}

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

def handle_errors(func: Callable) -> Callable:
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Log the error
            logging.error(f"Error in {func.__name__}: {e}")
            # Re-raise the exception
            raise
    return wrapper

def validate_json(json_data: str) -> bool:
    """
    Validates if the provided string is a valid JSON.

    Args:
        json_data (str): The string to validate.

    Returns:
        bool: True if the string is a valid JSON, False otherwise.
    """
    try:
        json.loads(json_data)
        return True
    except (TypeError, ValueError):
        return False