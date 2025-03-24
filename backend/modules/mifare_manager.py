import logging
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Optional, Union
import binascii

# Import centralized models
from backend.models import (
    MifareKey, MifareClassicSector, MifareDESFireApplication,
    SuccessResponse, ErrorResponse
)

# Configure logging
logger = logging.getLogger(__name__)

# Try to import the smartcard library with fallback
try:
    from smartcard.System import readers
    from smartcard.util import toHexString, toBytes
    from smartcard.Exceptions import CardConnectionException, NoCardException
    SMARTCARD_AVAILABLE = True
except ImportError:
    SMARTCARD_AVAILABLE = False
    logger.warning("Smartcard library not available. Using simulation mode.")

SIMULATION_MODE = os.environ.get('SIMULATION_MODE', 'False').lower() == 'true'

class MifareManager:
    """Manager for MIFARE card operations"""
    
    # Class variables
    executor = ThreadPoolExecutor()
    _connection = None
    
    @classmethod
    async def identify_card(cls) -> SuccessResponse:
        """
        Identify the current MIFARE card type
        
        Returns:
            SuccessResponse with card type information
        """
        logger.info("Identifying MIFARE card")
        
        if SIMULATION_MODE:
            return SuccessResponse(
                status="success",
                data={
                    'card_type': 'MIFARE Classic 1K',
                    'uid': 'A1B2C3D4',
                    'supports_crypto': True,
                    'sectors': 16
                }
            )
        
        if not SMARTCARD_AVAILABLE:
            return ErrorResponse(
                status="error",
                message="Smartcard library not available"
            )
            
        # Execute card identification in thread pool
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(cls.executor, cls._identify_card_sync)
            return result
            
        except Exception as e:
            logger.exception("Error identifying MIFARE card: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f"Failed to identify MIFARE card: {str(e)}"
            )
    
    @classmethod
    def _identify_card_sync(cls) -> SuccessResponse:
        """Synchronous method to identify MIFARE card"""
        try:
            # Get the first reader
            available_readers = readers()
            if not available_readers:
                return ErrorResponse(
                    status="error",
                    message="No smartcard readers found"
                )
                
            reader = available_readers[0]
            
            # Connect to the card
            from smartcard.CardConnection import CardConnection
            connection = reader.createConnection()
            connection.connect(CardConnection.T0_protocol | CardConnection.T1_protocol)
            
            # Store connection for future use
            cls._connection = connection
            
            # Get ATR
            atr = connection.getATR()
            atr_hex = toHexString(atr, separator='')
            
            # Get card UID with GET DATA command
            uid_cmd = [0xFF, 0xCA, 0x00, 0x00, 0x00]  # GET DATA for UID
            response, sw1, sw2 = connection.transmit(uid_cmd)
            
            if sw1 == 0x90 and sw2 == 0x00:
                uid = toHexString(response, separator='')
            else:
                uid = "Unknown"
            
            # Try to identify card type from ATR and other characteristics
            card_info = cls._determine_mifare_type(atr_hex, uid)
            
            return SuccessResponse(
                status="success",
                data=card_info
            )
                
        except NoCardException:
            return ErrorResponse(
                status="error",
                message="No card present in the reader"
            )
        except Exception as e:
            logger.exception("Error in synchronous MIFARE card identification: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f"MIFARE identification error: {str(e)}"
            )
    
    @classmethod
    def _determine_mifare_type(cls, atr: str, uid: str) -> Dict[str, Any]:
        """Determine MIFARE card type from ATR and UID"""
        if '3B8F8001804F0CA000000306030000000000006A' in atr:
            return {
                'card_type': 'MIFARE Classic 1K',
                'uid': uid,
                'supports_crypto': True,
                'sectors': 16
            }
        elif '3B8F8001804F0CA000000306030001000000006B' in atr:
            return {
                'card_type': 'MIFARE Classic 4K',
                'uid': uid,
                'supports_crypto': True,
                'sectors': 40
            }
        elif '3B8180018080' in atr:
            return {
                'card_type': 'MIFARE DESFire',
                'uid': uid,
                'supports_crypto': True,
                'applications': []
            }
        elif '3B8F8001804F0CA000000306' in atr:
            # Generic detection based on partial ATR
            return {
                'card_type': 'MIFARE (Unknown Type)',
                'uid': uid,
                'supports_crypto': True,
                'atr': atr
            }
        else:
            return {
                'card_type': 'Unknown Card',
                'uid': uid,
                'atr': atr
            }
    
    @classmethod
    async def authenticate_sector(cls, sector: int, key: Union[str, MifareKey], key_type: str = 'A') -> SuccessResponse:
        """
        Authenticate to a MIFARE Classic sector
        
        Args:
            sector: Sector number
            key: Key as hex string or MifareKey object
            key_type: 'A' or 'B'
            
        Returns:
            SuccessResponse with authentication result
        """
        logger.info(f"Authenticating to sector {sector} with key type {key_type}")
        
        if SIMULATION_MODE:
            return SuccessResponse(
                status="success",
                message=f"Authentication successful (simulated)",
                data={'authenticated': True, 'sector': sector}
            )
        
        if not SMARTCARD_AVAILABLE:
            return ErrorResponse(
                status="error",
                message="Smartcard library not available"
            )
            
        try:
            # Convert key to correct format
            if isinstance(key, MifareKey):
                key_bytes = bytes.fromhex(key.key_value)
            else:
                key_bytes = bytes.fromhex(key)
            
            # Create authentication parameters
            params = {
                'sector': sector,
                'key': key_bytes,
                'key_type': key_type
            }
            
            # Execute authentication in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                cls.executor, 
                lambda: cls._authenticate_sector_sync(**params)
            )
            
            return result
                
        except Exception as e:
            logger.exception("Error authenticating to MIFARE sector: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f"Authentication failed: {str(e)}"
            )
    
    @classmethod
    def _authenticate_sector_sync(cls, sector: int, key: bytes, key_type: str) -> SuccessResponse:
        """Synchronous method to authenticate to a MIFARE Classic sector"""
        try:
            if cls._connection is None:
                # Try to establish a connection
                available_readers = readers()
                if not available_readers:
                    return ErrorResponse(
                        status="error",
                        message="No smartcard readers found"
                    )
                    
                reader = available_readers[0]
                
                # Connect to the card
                from smartcard.CardConnection import CardConnection
                connection = reader.createConnection()
                connection.connect(CardConnection.T0_protocol | CardConnection.T1_protocol)
                
                # Store connection for future use
                cls._connection = connection
            
            # Calculate block address (first block of the sector)
            block = sector * 4
            
            # Perform authentication
            if key_type.upper() == 'A':
                auth_cmd = [0xFF, 0x86, 0x00, 0x00, 0x05, 0x01, 0x00, block, 0x60, key[0]]
            else:  # key_type B
                auth_cmd = [0xFF, 0x86, 0x00, 0x00, 0x05, 0x01, 0x00, block, 0x61, key[0]]
                
            # Add the rest of the key bytes
            for i in range(1, 6):
                auth_cmd.append(key[i])
                
            # Send authentication command
            response, sw1, sw2 = cls._connection.transmit(auth_cmd)
            
            if sw1 == 0x90 and sw2 == 0x00:
                return SuccessResponse(
                    status="success",
                    message="Authentication successful",
                    data={'authenticated': True, 'sector': sector}
                )
            else:
                return ErrorResponse(
                    status="error",
                    message=f"Authentication failed: SW={sw1:02X}{sw2:02X}",
                    data={'authenticated': False, 'sector': sector}
                )
                
        except Exception as e:
            logger.exception("Error in synchronous MIFARE authentication: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f"MIFARE authentication error: {str(e)}",
                data={'authenticated': False, 'sector': sector}
            )
    
    @classmethod
    async def read_block(cls, block: int) -> SuccessResponse:
        """
        Read a MIFARE Classic block
        
        Args:
            block: Block number to read
            
        Returns:
            SuccessResponse with block data
        """
        logger.info(f"Reading block {block}")
        
        if SIMULATION_MODE:
            # Simulated data based on block number
            block_data = ''.join([f"{((block * 7 + i) % 256):02X}" for i in range(16)])
            return SuccessResponse(
                status="success",
                data={'block': block, 'data': block_data}
            )
        
        if not SMARTCARD_AVAILABLE:
            return ErrorResponse(
                status="error",
                message="Smartcard library not available"
            )
            
        try:
            # Execute read operation in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                cls.executor, 
                lambda: cls._read_block_sync(block)
            )
            
            return result
                
        except Exception as e:
            logger.exception("Error reading MIFARE block: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f"Failed to read block: {str(e)}"
            )
    
    @classmethod
    def _read_block_sync(cls, block: int) -> SuccessResponse:
        """Synchronous method to read a MIFARE Classic block"""
        try:
            if cls._connection is None:
                return ErrorResponse(
                    status="error",
                    message="No connection to card"
                )
                
            # Read block command
            read_cmd = [0xFF, 0xB0, 0x00, block, 0x10]  # Read 16 bytes
            response, sw1, sw2 = cls._connection.transmit(read_cmd)
            
            if sw1 == 0x90 and sw2 == 0x00:
                data = toHexString(response, separator='')
                return SuccessResponse(
                    status="success",
                    data={'block': block, 'data': data}
                )
            else:
                return ErrorResponse(
                    status="error",
                    message=f"Failed to read block: SW={sw1:02X}{sw2:02X}",
                    data={'block': block}
                )
                
        except Exception as e:
            logger.exception("Error in synchronous MIFARE block read: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f"MIFARE block read error: {str(e)}",
                data={'block': block}
            )
    
    @classmethod
    async def write_block(cls, block: int, data: str) -> SuccessResponse:
        """
        Write data to a MIFARE Classic block
        
        Args:
            block: Block number to write
            data: Hex string data (16 bytes / 32 hex chars)
            
        Returns:
            SuccessResponse with write result
        """
        logger.info(f"Writing to block {block}: {data}")
        
        # Validate input data
        if len(data.replace(' ', '')) != 32:
            return ErrorResponse(
                status="error",
                message="Data must be exactly 16 bytes (32 hex characters)"
            )
            
        if SIMULATION_MODE:
            return SuccessResponse(
                status="success",
                message="Block written successfully (simulated)",
                data={'block': block, 'written': True}
            )
        
        if not SMARTCARD_AVAILABLE:
            return ErrorResponse(
                status="error",
                message="Smartcard library not available"
            )
            
        try:
            # Convert hex string to bytes
            data_bytes = bytes.fromhex(data.replace(' ', ''))
            
            # Execute write operation in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                cls.executor, 
                lambda: cls._write_block_sync(block, data_bytes)
            )
            
            return result
                
        except Exception as e:
            logger.exception("Error writing to MIFARE block: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f"Failed to write block: {str(e)}"
            )
    
    @classmethod
    def _write_block_sync(cls, block: int, data: bytes) -> SuccessResponse:
        """Synchronous method to write to a MIFARE Classic block"""
        try:
            if cls._connection is None:
                return ErrorResponse(
                    status="error",
                    message="No connection to card"
                )
                
            # Write block command
            write_cmd = [0xFF, 0xD6, 0x00, block, 0x10]  # Write 16 bytes
            
            # Add data bytes to command
            for byte in data:
                write_cmd.append(byte)
                
            # Send command
            response, sw1, sw2 = cls._connection.transmit(write_cmd)
            
            if sw1 == 0x90 and sw2 == 0x00:
                return SuccessResponse(
                    status="success",
                    message="Block written successfully",
                    data={'block': block, 'written': True}
                )
            else:
                return ErrorResponse(
                    status="error",
                    message=f"Failed to write block: SW={sw1:02X}{sw2:02X}",
                    data={'block': block, 'written': False}
                )
                
        except Exception as e:
            logger.exception("Error in synchronous MIFARE block write: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f"MIFARE block write error: {str(e)}",
                data={'block': block, 'written': False}
            )
    
    @classmethod
    async def read_sector(cls, sector: int, key: Union[str, MifareKey] = None, key_type: str = 'A') -> SuccessResponse:
        """
        Read an entire MIFARE Classic sector
        
        Args:
            sector: Sector number
            key: Authentication key (optional if already authenticated)
            key_type: Key type ('A' or 'B')
            
        Returns:
            SuccessResponse with sector data
        """
        logger.info(f"Reading sector {sector}")
        
        if SIMULATION_MODE:
            # Simulated sector data
            sector_data = {}
            for block in range(sector * 4, (sector + 1) * 4):
                # Last block is the sector trailer
                if block % 4 == 3:
                    sector_data[f"block_{block}"] = "FFFFFFFFFFFF08778F6699FFFFFFFFFFFF"
                else:
                    sector_data[f"block_{block}"] = ''.join([f"{((block * 7 + i) % 256):02X}" for i in range(16)])
                    
            return SuccessResponse(
                status="success",
                data={
                    'sector': sector,
                    'blocks': sector_data
                }
            )
        
        if not SMARTCARD_AVAILABLE:
            return ErrorResponse(
                status="error",
                message="Smartcard library not available"
            )
            
        try:
            # Authenticate first if key provided
            if key is not None:
                auth_result = await cls.authenticate_sector(sector, key, key_type)
                if auth_result.status != "success":
                    return auth_result
            
            # Execute sector read operation in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                cls.executor, 
                lambda: cls._read_sector_sync(sector)
            )
            
            return result
                
        except Exception as e:
            logger.exception("Error reading MIFARE sector: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f"Failed to read sector: {str(e)}"
            )
    
    @classmethod
    def _read_sector_sync(cls, sector: int) -> SuccessResponse:
        """Synchronous method to read an entire MIFARE Classic sector"""
        try:
            if cls._connection is None:
                return ErrorResponse(
                    status="error",
                    message="No connection to card"
                )
                
            # Calculate block range for the sector
            start_block = sector * 4
            end_block = (sector + 1) * 4
            
            # Read all blocks in the sector
            sector_data = {}
            for block in range(start_block, end_block):
                # Read block command
                read_cmd = [0xFF, 0xB0, 0x00, block, 0x10]  # Read 16 bytes
                response, sw1, sw2 = cls._connection.transmit(read_cmd)
                
                if sw1 == 0x90 and sw2 == 0x00:
                    data = toHexString(response, separator='')
                    sector_data[f"block_{block}"] = data
                else:
                    sector_data[f"block_{block}"] = f"ERROR: SW={sw1:02X}{sw2:02X}"
            
            return SuccessResponse(
                status="success",
                data={
                    'sector': sector,
                    'blocks': sector_data
                }
            )
                
        except Exception as e:
            logger.exception("Error in synchronous MIFARE sector read: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f"MIFARE sector read error: {str(e)}"
            )
    
    @classmethod
    def close(cls):
        """Close connection to the card"""
        if cls._connection:
            try:
                cls._connection.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting from card: {e}")
            finally:
                cls._connection = None