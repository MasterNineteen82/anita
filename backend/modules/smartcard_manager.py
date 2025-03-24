import logging
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Optional, Union
import time
import binascii

# Import centralized models
from backend.models import (
    SmartcardReaderResponse, SmartcardCommand, SmartcardResponse,
    SuccessResponse, ErrorResponse
)

logger = logging.getLogger(__name__)

# Try to import the smartcard library with fallback
try:
    from smartcard.System import readers
    from smartcard.util import toHexString, toBytes
    from smartcard.Exceptions import CardConnectionException, NoCardException
    from smartcard.CardType import AnyCardType
    from smartcard.CardRequest import CardRequest
    from smartcard.CardConnection import CardConnection
    SMARTCARD_AVAILABLE = True
except ImportError:
    SMARTCARD_AVAILABLE = False
    logger.warning("Smartcard library not available. Using simulation mode.")

SIMULATION_MODE = os.environ.get('SIMULATION_MODE', 'False').lower() == 'true'

class SmartcardManager:
    """Manager for Smartcard operations"""
    
    # Class variables
    executor = ThreadPoolExecutor()
    _readers = {}
    _selected_reader = None
    _selected_card = None
    
    @classmethod
    async def list_readers(cls) -> SuccessResponse:
        """
        List all available smartcard readers
        
        Returns:
            SuccessResponse with readers data
        """
        logger.info("Listing smartcard readers")
        
        if SIMULATION_MODE:
            # Return simulated readers
            return SuccessResponse(
                status="success",
                data={
                    'readers': [
                        {
                            'name': 'Simulated Contact Reader',
                            'type': 'contact',
                            'status': 'online'
                        },
                        {
                            'name': 'Simulated Contactless Reader',
                            'type': 'contactless',
                            'status': 'online'
                        }
                    ]
                }
            )
        
        if not SMARTCARD_AVAILABLE:
            return ErrorResponse(
                status="error",
                message="Smartcard library not available"
            )
            
        try:
            # Get readers from the system
            available_readers = readers()
            
            # Format reader information
            reader_list = []
            for i, reader in enumerate(available_readers):
                reader_info = {
                    'name': str(reader),
                    'type': 'contactless' if 'contactless' in str(reader).lower() else 'contact',
                    'status': 'online',
                    'index': i
                }
                reader_list.append(reader_info)
                
            # Store readers for later use
            cls._readers = {i: reader for i, reader in enumerate(available_readers)}
                
            return SuccessResponse(
                status="success",
                data={'readers': reader_list}
            )
                
        except Exception as e:
            logger.exception("Error listing smartcard readers: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f"Failed to list smartcard readers: {str(e)}"
            )
    
    @classmethod
    async def select_reader(cls, reader_index: int) -> SuccessResponse:
        """
        Select a smartcard reader for operations
        
        Args:
            reader_index: Index of the reader to select
            
        Returns:
            SuccessResponse with selected reader info
        """
        logger.info(f"Selecting smartcard reader: {reader_index}")
        
        # Ensure we have readers
        if not cls._readers and not SIMULATION_MODE:
            result = await cls.list_readers()
            if result.status != "success":
                return result
        
        if SIMULATION_MODE:
            cls._selected_reader = reader_index
            reader_name = "Simulated Reader" if reader_index == 0 else f"Simulated Reader {reader_index}"
            return SuccessResponse(
                status="success",
                message=f"Reader selected: {reader_name}",
                data={
                    'reader': {
                        'name': reader_name,
                        'type': 'contact' if reader_index == 0 else 'contactless',
                        'status': 'online',
                        'index': reader_index
                    }
                }
            )
        
        try:
            # Check if the reader index is valid
            if reader_index not in cls._readers:
                return ErrorResponse(
                    status="error",
                    message=f"Invalid reader index: {reader_index}"
                )
                
            # Select the reader
            cls._selected_reader = reader_index
            selected_reader = cls._readers[reader_index]
            
            return SuccessResponse(
                status="success",
                message=f"Reader selected: {str(selected_reader)}",
                data={
                    'reader': {
                        'name': str(selected_reader),
                        'type': 'contactless' if 'contactless' in str(selected_reader).lower() else 'contact',
                        'status': 'online',
                        'index': reader_index
                    }
                }
            )
                
        except Exception as e:
            logger.exception("Error selecting smartcard reader: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f"Failed to select smartcard reader: {str(e)}"
            )
    
    @classmethod
    async def detect_card(cls) -> SuccessResponse:
        """
        Detect a card in the selected reader
        
        Returns:
            SuccessResponse with card info
        """
        logger.info("Detecting card in selected reader")
        
        if SIMULATION_MODE:
            return SuccessResponse(
                status="success",
                data={
                    'card_present': True,
                    'atr': '3B8F8001804F0CA0000003060300030000000068',
                    'type': 'Simulated Card'
                }
            )
        
        if not SMARTCARD_AVAILABLE:
            return ErrorResponse(
                status="error",
                message="Smartcard library not available"
            )
            
        # Check if a reader is selected
        if cls._selected_reader is None:
            return ErrorResponse(
                status="error",
                message="No reader selected"
            )
            
        try:
            # Get the selected reader
            selected_reader = cls._readers[cls._selected_reader]
            
            # Try to connect to a card
            connection = selected_reader.createConnection()
            connection.connect()
            
            # Get the ATR
            atr = connection.getATR()
            atr_hex = toHexString(atr, separator='')
            
            # Store the connection for later use
            cls._selected_card = connection
            
            return SuccessResponse(
                status="success",
                data={
                    'card_present': True,
                    'atr': atr_hex,
                    'type': cls._identify_card_type(atr)
                }
            )
                
        except NoCardException:
            return SuccessResponse(
                status="success",
                data={
                    'card_present': False
                }
            )
        except Exception as e:
            logger.exception("Error detecting card: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f"Failed to detect card: {str(e)}"
            )
    
    @classmethod
    async def transmit_apdu(cls, apdu: Union[str, List[int]]) -> SmartcardResponse:
        """
        Transmit an APDU command to the card
        
        Args:
            apdu: APDU command as hex string or list of bytes
            
        Returns:
            SmartcardResponse with the card's response
        """
        logger.info(f"Transmitting APDU: {apdu}")
        
        if SIMULATION_MODE:
            # Simulate different responses based on the command
            apdu_bytes = apdu if isinstance(apdu, list) else toBytes(apdu)
            
            # Default simulated response
            response_data = '9000'  # SW1=90, SW2=00 (Success)
            
            # Check for specific commands
            cla = apdu_bytes[0] if len(apdu_bytes) > 0 else 0
            ins = apdu_bytes[1] if len(apdu_bytes) > 1 else 0
            
            if cla == 0x00 and ins == 0xA4:  # SELECT command
                response_data = '6F00' + '9000'  # File control parameters + Success
            elif cla == 0x00 and ins == 0xB0:  # READ BINARY
                # Simulated data block
                response_data = '00112233445566778899AABBCCDDEEFF' + '9000'
            elif cla == 0x00 and ins == 0xB2:  # READ RECORD
                response_data = 'RECORD_DATA' + '9000'
                
            # Parse the simulated response
            if len(response_data) >= 4:
                sw = response_data[-4:]
                data = response_data[:-4] if len(response_data) > 4 else ''
                
                return SmartcardResponse(
                    data=data,
                    sw1=sw[:2],
                    sw2=sw[2:],
                    success=sw == '9000'
                )
        
        if not SMARTCARD_AVAILABLE:
            return ErrorResponse(
                status="error",
                message="Smartcard library not available"
            )
            
        # Check if a card is selected
        if cls._selected_card is None:
            return ErrorResponse(
                status="error",
                message="No card selected"
            )
            
        try:
            # Convert string APDU to bytes if needed
            apdu_bytes = apdu if isinstance(apdu, list) else toBytes(apdu)
            
            # Transmit the command
            data, sw1, sw2 = cls._selected_card.transmit(apdu_bytes)
            
            # Format the response
            sw1_hex = f'{sw1:02X}'
            sw2_hex = f'{sw2:02X}'
            data_hex = toHexString(data, separator='')
            
            return SmartcardResponse(
                data=data_hex,
                sw1=sw1_hex,
                sw2=sw2_hex,
                success=(sw1 == 0x90 and sw2 == 0x00)
            )
                
        except Exception as e:
            logger.exception("Error transmitting APDU: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f"Failed to transmit APDU: {str(e)}"
            )
    
    @classmethod
    def _identify_card_type(cls, atr: List[int]) -> str:
        """Identify card type from ATR"""
        atr_hex = toHexString(atr, separator='')
        
        # This is a basic identification - production code would need a more comprehensive database
        if atr_hex.startswith('3B8F80'):
            return 'MIFARE DESFire'
        elif atr_hex.startswith('3B8F'):
            return 'MIFARE Classic'
        elif atr_hex.startswith('3B9F'):
            return 'Java Card'
        else:
            return f'Unknown card type'
    
    @classmethod
    def close(cls):
        """Close connections and release resources"""
        try:
            if cls._selected_card:
                cls._selected_card.disconnect()
                cls._selected_card = None
                
            cls._selected_reader = None
            cls._readers = {}
            
        except Exception as e:
            logger.error(f"Error closing smartcard connections: {e}")
