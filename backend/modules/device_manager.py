import logging
import os
import asyncio
from typing import Dict, List, Optional, Any
import time
from concurrent.futures import ThreadPoolExecutor
from fastapi import HTTPException, status

# Add these imports
from backend.models import ReaderResponse, ReadersResponse, SuccessResponse, ErrorResponse

# Try to import the card libraries with fallbacks
try:
    from smartcard.System import readers as get_readers
    from smartcard.Exceptions import SmartcardException
    SMARTCARD_AVAILABLE = True
except ImportError:
    SMARTCARD_AVAILABLE = False
    
try:
    import nfc
    NFC_AVAILABLE = True
except ImportError:
    NFC_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
SIMULATION_MODE = os.environ.get('SIMULATION_MODE', 'False').lower() in ('true', '1', 'yes')
DEVICE_OPERATION_TIMEOUT = int(os.environ.get('DEVICE_OPERATION_TIMEOUT', '10'))  # seconds

class DeviceManager:
    executor = ThreadPoolExecutor()
    _reader_cache = {"timestamp": 0, "readers": None, "cache_duration": 5}  # 5 second cache
    _selected_reader = None
    
    @staticmethod
    async def list_smartcard_readers(force_refresh: bool = False) -> ReadersResponse:
        """
        List all available smartcard and NFC readers.
        
        Args:
            force_refresh: If True, bypass the cache and force a new device discovery
            
        Returns:
            Dictionary with readers information
        """
        logger.info("Listing smartcard and NFC readers (force_refresh=%s)", force_refresh)
        
        # Check cache if not forcing refresh
        current_time = time.time()
        if not force_refresh and DeviceManager._reader_cache["readers"] is not None:
            if current_time - DeviceManager._reader_cache["timestamp"] < DeviceManager._reader_cache["cache_duration"]:
                logger.debug("Using cached reader list")
                return ReadersResponse(
                    status="success",
                    data={"readers": DeviceManager._reader_cache["readers"]}
                )
        
        loop = asyncio.get_event_loop()
        try:
            # Use a timeout to prevent hanging
            reader_future = loop.run_in_executor(DeviceManager.executor, DeviceManager._get_smartcard_readers)
            smartcard_readers = await asyncio.wait_for(reader_future, timeout=DEVICE_OPERATION_TIMEOUT)
            
            # Get NFC readers
            nfc_result = await DeviceManager.discover_nfc_device()
            
            reader_list = [
                {
                    'name': str(r), 
                    'type': 'smartcard',
                    'isContact': True,
                    'isContactless': 'contactless' in str(r).lower(),
                    'simulation': SIMULATION_MODE
                } 
                for r in smartcard_readers
            ]
            
            # Add NFC devices if found
            if nfc_result.get('status') == 'success' and nfc_result.get('data', {}).get('device'):
                nfc_device = nfc_result['data']['device']
                reader_list.append({
                    'name': nfc_device,
                    'type': 'nfc',
                    'isContact': False,
                    'isContactless': True,
                    'simulation': SIMULATION_MODE
                })
            
            # Update cache
            DeviceManager._reader_cache["readers"] = reader_list
            DeviceManager._reader_cache["timestamp"] = current_time
            
            return ReadersResponse(
                status="success",
                data={"readers": reader_list}
            )
            
        except asyncio.TimeoutError:
            logger.error("Timeout while discovering card readers")
            return ErrorResponse(
                status="error",
                message="Device discovery timed out"
            )
            
        except Exception as e:
            logger.exception("Error discovering card readers: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f"Failed to discover card readers: {str(e)}"
            )
    
    @staticmethod
    def _get_smartcard_readers():
        """Get list of physical smartcard readers or simulated ones"""
        try:
            if SIMULATION_MODE:
                # Return simulated readers
                return [
                    "Simulated Contact Reader",
                    "Simulated Contactless Reader"
                ]
            
            if not SMARTCARD_AVAILABLE:
                logger.warning("Smartcard library not available")
                return []
                
            # Get physical readers
            return get_readers()
            
        except Exception as e:
            logger.exception("Error getting smartcard readers: %s", str(e))
            return []
    
    @staticmethod
    async def discover_nfc_device() -> SuccessResponse:
        """
        Discover NFC devices connected to the system.
        
        Returns:
            SuccessResponse with NFC device information
        """
        try:
            if SIMULATION_MODE:
                # Return simulated NFC device
                return SuccessResponse(
                    status="success",
                    data={'device': 'Simulated NFC Reader'}
                )
                
            if not NFC_AVAILABLE:
                logger.warning("NFC library not available")
                return SuccessResponse(
                    status="warning",
                    message='NFC library not available',
                    data={'device': None}
                )
            
            # Use a separate thread for NFC discovery to avoid blocking
            loop = asyncio.get_event_loop()
            nfc_future = loop.run_in_executor(DeviceManager.executor, DeviceManager._discover_nfc_device_sync)
            result = await asyncio.wait_for(nfc_future, timeout=DEVICE_OPERATION_TIMEOUT)
            
            return result
            
        except asyncio.TimeoutError:
            logger.error("Timeout while discovering NFC devices")
            return ErrorResponse(
                status="error",
                message='NFC device discovery timed out',
                data={'device': None}
            )
            
        except Exception as e:
            logger.exception("Error discovering NFC devices: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f'Failed to discover NFC devices: {str(e)}',
                data={'device': None}
            )
    
    @staticmethod
    def _discover_nfc_device_sync() -> SuccessResponse:
        """Synchronous method to discover NFC devices"""
        try:
            # This implementation depends on the specific NFC library being used
            # For nfcpy:
            clf = nfc.ContactlessFrontend('usb')
            if clf:
                device_path = clf.path
                clf.close()
                return SuccessResponse(
                    status="success",
                    data={'device': device_path}
                )
            else:
                return SuccessResponse(
                    status="warning",
                    message='No NFC devices found',
                    data={'device': None}
                )
                
        except Exception as e:
            logger.exception("Error in NFC device discovery: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f'NFC discovery error: {str(e)}',
                data={'device': None}
            )
    
    @staticmethod
    async def select_reader(reader_name: str) -> ReaderResponse:
        """
        Select a reader for operations.
        
        Args:
            reader_name: Name of the reader to select
            
        Returns:
            Status dictionary
        """
        logger.info("Selecting reader: %s", reader_name)
        
        try:
            # Verify the reader exists
            reader_info = None
            reader_list = DeviceManager._reader_cache.get("readers", [])
            
            if not reader_list:
                # Get fresh reader list if cache is empty
                result = await DeviceManager.list_smartcard_readers(force_refresh=True)
                if result.status == 'success':
                    reader_list = result.data.get('readers', [])
            
            for reader in reader_list:
                if reader.get('name') == reader_name:
                    reader_info = reader
                    break
            
            if not reader_info:
                return ErrorResponse(
                    status="error",
                    message=f'Reader "{reader_name}" not found'
                )
            
            # Store the selected reader
            DeviceManager._selected_reader = reader_info
            
            return ReaderResponse(
                status="success",
                message=f'Reader "{reader_name}" selected successfully',
                data={'reader': reader_info}
            )
            
        except Exception as e:
            logger.exception("Error selecting reader: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f'Failed to select reader: {str(e)}'
            )
    
    @staticmethod
    async def check_reader_health(reader_name: str) -> SuccessResponse:
        """
        Check the health status of a reader.
        
        Args:
            reader_name: Name of the reader to check
            
        Returns:
            Health status dictionary
        """
        logger.info("Checking health of reader: %s", reader_name)
        
        try:
            # In simulation mode, always return healthy
            if SIMULATION_MODE:
                return SuccessResponse(
                    status="success",
                    data={
                        'healthy': True,
                        'message': 'Simulated reader is healthy'
                    }
                )
            
            # For real readers, perform basic health check
            loop = asyncio.get_event_loop()
            health_future = loop.run_in_executor(
                DeviceManager.executor, 
                DeviceManager._check_reader_health_sync,
                reader_name
            )
            
            result = await asyncio.wait_for(health_future, timeout=DEVICE_OPERATION_TIMEOUT)
            return result
            
        except asyncio.TimeoutError:
            logger.error("Timeout while checking reader health")
            return ErrorResponse(
                status="error",
                message="Health check timed out",
                data={'healthy': False}
            )
            
        except Exception as e:
            logger.exception("Error checking reader health: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f'Health check failed: {str(e)}',
                data={'healthy': False}
            )
    
    @staticmethod
    def _check_reader_health_sync(reader_name: str) -> SuccessResponse:
        """Synchronous method to check reader health"""
        try:
            if not SMARTCARD_AVAILABLE:
                return ErrorResponse(
                    status="error",
                    message="Smartcard library not available",
                    data={'healthy': False}
                )
            
            # Find the reader in the system
            available_readers = get_readers()
            reader = None
            
            for r in available_readers:
                if str(r) == reader_name:
                    reader = r
                    break
            
            if not reader:
                return ErrorResponse(
                    status="error",
                    message=f'Reader "{reader_name}" not found',
                    data={'healthy': False}
                )
            
            # Basic health check - try to create a connection
            from smartcard.CardConnection import CardConnection
            connection = reader.createConnection()
            
            # Try to connect - this will raise an exception if the reader is not healthy
            connection.connect(CardConnection.T0_protocol | CardConnection.T1_protocol)
            
            # If we got here, the reader is responsive
            return SuccessResponse(
                status="success",
                data={
                    'healthy': True,
                    'message': 'Reader is responding correctly'
                }
            )
                
        except SmartcardException as e:
            # Not finding a card doesn't mean the reader is unhealthy
            # It might just mean there's no card inserted
            return SuccessResponse(
                status="success",
                data={
                    'healthy': True,
                    'message': 'Reader is present but no card detected'
                }
            )
            
        except Exception as e:
            logger.exception("Reader health check failed: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f'Reader health check failed: {str(e)}',
                data={'healthy': False}
            )
    
    @staticmethod
    async def set_simulation_mode(enabled: bool) -> SuccessResponse:
        """
        Toggle simulation mode.
        
        Args:
            enabled: Whether to enable simulation mode
            
        Returns:
            Status dictionary
        """
        global SIMULATION_MODE
        logger.info("Setting simulation mode to: %s", enabled)
        
        try:
            # Update the simulation mode
            old_mode = SIMULATION_MODE
            SIMULATION_MODE = enabled
            
            # Clear the cache to force refresh with new simulation setting
            DeviceManager._reader_cache["readers"] = None
            
            return SuccessResponse(
                status="success",
                message=f'Simulation mode {"enabled" if enabled else "disabled"}',
                data={'simulation_mode': enabled, 'previous_mode': old_mode}
            )
            
        except Exception as e:
            logger.exception("Error setting simulation mode: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f'Failed to set simulation mode: {str(e)}'
            )
    
    @staticmethod
    def shutdown_executor():
        """Shutdown the thread pool executor"""
        logger.info("Shutting down device manager executor")
        DeviceManager.executor.shutdown(wait=False)

    @staticmethod
    async def read_card(reader_name: str, options: Dict = None) -> SuccessResponse:
        """
        Read data from a card
        
        Args:
            reader_name: Name of the reader to use
            options: Optional parameters (sector, block, authentication keys, etc.)
            
        Returns:
            Dictionary with card data
        """
        logger.info(f"Reading card with reader: {reader_name}")
        
        if SIMULATION_MODE:
            # Return simulated data
            return SuccessResponse(
                status="success",
                data={
                    'uid': '04A23B99C2E380',
                    'type': 'MIFARE Classic 1K',
                    'sectors': {
                        '0': {'data': '00000000000000000000000000000000'},
                        '1': {'data': 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'}
                    }
                }
            )
        
        try:
            # Import crypto only when needed
            from .card_crypto import CardCrypto
            
            # Get default options if none provided
            if options is None:
                options = {
                    'sectors': [0, 1],  # Default sectors to read
                    'key_a': bytes.fromhex('FFFFFFFFFFFF'),  # Default key A
                    'key_b': bytes.fromhex('FFFFFFFFFFFF'),  # Default key B
                    'use_key': 'A'  # Default key type
                }
            
            # Execute the card read operation in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                DeviceManager.executor,
                DeviceManager._read_card_sync,
                reader_name,
                options
            )
            
            return result
            
        except Exception as e:
            logger.exception(f"Error reading card: {str(e)}")
            return ErrorResponse(
                status="error",
                message=f'Card read operation failed: {str(e)}'
            )

    @staticmethod
    def _read_card_sync(reader_name: str, options: Dict) -> SuccessResponse:
        """Synchronous method to read a card"""
        try:
            if not SMARTCARD_AVAILABLE:
                return ErrorResponse(
                    status="error",
                    message="Smartcard library not available"
                )
            
            # Import card crypto
            from .card_crypto import CardCrypto
            
            # Find the reader
            available_readers = get_readers()
            reader = None
            
            for r in available_readers:
                if str(r) == reader_name:
                    reader = r
                    break
            
            if not reader:
                return ErrorResponse(
                    status="error",
                    message=f'Reader "{reader_name}" not found'
                )
            
            # Connect to the card
            from smartcard.CardConnection import CardConnection
            connection = reader.createConnection()
            connection.connect(CardConnection.T0_protocol | CardConnection.T1_protocol)
            
            # Get card UID (ATR might contain it, or use specific command)
            atr = connection.getATR()
            logger.debug(f"Card ATR: {bytes(atr).hex().upper()}")
            
            # For MIFARE, we need to send a specific command to get UID
            get_uid_cmd = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            response, sw1, sw2 = connection.transmit(get_uid_cmd)
            
            if sw1 != 0x90 or sw2 != 0x00:
                return ErrorResponse(
                    status="error",
                    message=f'Failed to get card UID: SW={sw1:02X}{sw2:02X}'
                )
            
            uid = bytes(response).hex().upper()
            logger.info(f"Card UID: {uid}")
            
            # Read the requested sectors
            sectors_data = {}
            key_a = options.get('key_a', bytes.fromhex('FFFFFFFFFFFF'))
            key_b = options.get('key_b', bytes.fromhex('FFFFFFFFFFFF'))
            use_key = options.get('use_key', 'A')
            
            for sector in options.get('sectors', [0, 1]):
                # Authenticate to the sector
                auth_cmd = list(CardCrypto.authenticate_mifare_classic(
                    sector, 
                    key_a if use_key == 'A' else key_b, 
                    use_key
                ))
                
                response, sw1, sw2 = connection.transmit(auth_cmd)
                
                if sw1 != 0x90 or sw2 != 0x00:
                    sectors_data[str(sector)] = {
                        'error': f'Authentication failed: SW={sw1:02X}{sw2:02X}'
                    }
                    continue
                
                # Read blocks in the sector
                sector_data = {}
                for block in range(sector * 4, (sector + 1) * 4):
                    read_cmd = [0xFF, 0xB0, 0x00, block, 0x10]  # Read 16 bytes
                    response, sw1, sw2 = connection.transmit(read_cmd)
                    
                    if sw1 == 0x90 and sw2 == 0x00:
                        sector_data[f'block_{block}'] = bytes(response).hex().upper()
                    else:
                        sector_data[f'block_{block}'] = f'Read failed: SW={sw1:02X}{sw2:02X}'
                
                sectors_data[str(sector)] = sector_data
            
            return SuccessResponse(
                status="success",
                data={
                    'uid': uid,
                    'type': DeviceManager._identify_card_type(atr),
                    'sectors': sectors_data
                }
            )
            
        except Exception as e:
            logger.exception(f"Card read operation error: {str(e)}")
            return ErrorResponse(
                status="error",
                message=f'Card read operation failed: {str(e)}'
            )

    @staticmethod
    def _identify_card_type(atr: List[int]) -> str:
        """Identify card type from ATR"""
        atr_hex = bytes(atr).hex().upper()
        
        # This is a basic identification - production code would need a more comprehensive database
        if atr_hex.startswith('3B8F80'):
            return 'MIFARE DESFire'
        elif atr_hex.startswith('3B8F'):
            return 'MIFARE Classic'
        else:
            return f'Unknown card (ATR: {atr_hex})'