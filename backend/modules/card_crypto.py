from typing import List, Dict, Union, Tuple, Optional
import logging
import os

# Use Cryptodome instead of Crypto
from Cryptodome.Cipher import AES, DES, DES3
from Cryptodome.Util.Padding import pad, unpad
from Cryptodome.Random import get_random_bytes

logger = logging.getLogger(__name__)

class CardCrypto:
    """Cryptographic operations for smart cards"""
    
    @staticmethod
    def diversify_key(master_key: bytes, card_uid: bytes, aid: Optional[bytes] = None) -> bytes:
        """
        Diversify a master key for a specific card
        
        Args:
            master_key: The master key bytes
            card_uid: The unique ID of the card
            aid: Optional application ID
            
        Returns:
            Diversified key bytes
        """
        try:
            # Simple implementation of key diversification using AES
            if len(master_key) != 16:
                raise ValueError("Master key must be 16 bytes for AES diversification")
                
            # Create diversification input using UID and optional AID
            div_input = card_uid
            if aid:
                div_input += aid
                
            # Ensure we have at least 16 bytes by padding if needed
            if len(div_input) < 16:
                div_input = pad(div_input, 16)
            elif len(div_input) > 16:
                div_input = div_input[:16]
                
            # Use AES to create the diversified key
            cipher = AES.new(master_key, AES.MODE_ECB)
            return cipher.encrypt(div_input)
            
        except Exception as e:
            logger.error(f"Key diversification error: {str(e)}")
            raise
    
    @staticmethod
    def authenticate_mifare_classic(sector: int, key: bytes, key_type: str = 'A') -> bytes:
        """
        Prepare authentication command for MIFARE Classic card
        
        Args:
            sector: The sector number to authenticate
            key: The authentication key (6 bytes)
            key_type: Key type ('A' or 'B')
            
        Returns:
            APDU command bytes for authentication
        """
        if len(key) != 6:
            raise ValueError("MIFARE Classic key must be 6 bytes")
            
        key_type_byte = 0x60 if key_type.upper() == 'A' else 0x61
        block = sector * 4  # First block of the sector
        
        # Format: CLA INS P1 P2 Lc Data
        return bytes([0xFF, 0x86, 0x00, 0x00, 0x05, 0x01, key_type_byte, block]) + key
    
    @staticmethod
    def authenticate_desfire(key_no: int, key: bytes) -> bytes:
        """
        Prepare authentication command for MIFARE DESFire card
        
        Args:
            key_no: The key number to use
            key: The authentication key
            
        Returns:
            APDU command bytes for authentication initiation
        """
        # DESFire authentication is a multi-step process, this is just step 1
        # Format: CLA INS P1 P2 Lc
        return bytes([0x90, 0x0A, 0x00, key_no, 0x00])
    
    @staticmethod
    def encrypt_apdu(command: bytes, session_key: bytes, iv: bytes) -> bytes:
        """
        Encrypt an APDU command for secure messaging
        
        Args:
            command: The command APDU to encrypt
            session_key: The session key to use
            iv: The initialization vector
            
        Returns:
            Encrypted APDU bytes
        """
        try:
            # Pad the command to a multiple of 16 bytes (AES block size)
            padded_command = pad(command, 16)
            
            # Use AES CBC mode for encryption
            cipher = AES.new(session_key, AES.MODE_CBC, iv)
            encrypted_data = cipher.encrypt(padded_command)
            
            return encrypted_data
            
        except Exception as e:
            logger.error(f"APDU encryption error: {str(e)}")
            raise
    
    @staticmethod
    def decrypt_response(response: bytes, session_key: bytes, iv: bytes) -> bytes:
        """
        Decrypt a card response from secure messaging
        
        Args:
            response: The encrypted response data
            session_key: The session key to use
            iv: The initialization vector
            
        Returns:
            Decrypted response bytes
        """
        try:
            # Ensure response is a multiple of 16 bytes (AES block size)
            if len(response) % 16 != 0:
                raise ValueError(f"Encrypted response length ({len(response)}) is not a multiple of 16")
                
            # Use AES CBC mode for decryption
            cipher = AES.new(session_key, AES.MODE_CBC, iv)
            decrypted_data = cipher.decrypt(response)
            
            # Remove padding
            return unpad(decrypted_data, 16)
            
        except Exception as e:
            logger.error(f"Response decryption error: {str(e)}")
            raise