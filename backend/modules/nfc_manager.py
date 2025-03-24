import logging
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Any, Union
import time

# Import centralized models
from backend.models import (
    NFCRecord, NFCMessage, NFCWifiCredentials, 
    NFCTextRecord, NFCURLRecord, SuccessResponse, ErrorResponse
)

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Try to import NFC library with fallback
try:
    import nfc
    import nfc.clf
    import nfc.tag
    try:
        import ndef
    except ImportError:
        # Use nfc.ndef if ndef is not available
        import nfc.ndef as ndef
    import usb1
    NFC_AVAILABLE = True
except ImportError:
    NFC_AVAILABLE = False
    logger.warning("NFC libraries not available. Using simulation mode.")

SIMULATION_MODE = os.environ.get('SIMULATION_MODE', 'False').lower() == 'true'

class NFCManager:
    """Manager for NFC operations"""
    
    # Class variables
    executor = ThreadPoolExecutor()
    _device = None
    
    @classmethod
    async def read_tag(cls) -> SuccessResponse:
        """
        Read an NFC tag and return its content
        
        Returns:
            SuccessResponse with tag data or ErrorResponse if operation failed
        """
        logger.info("Reading NFC tag")
        
        if SIMULATION_MODE:
            # Return simulated tag data
            return SuccessResponse(
                status="success",
                data={
                    'tag_id': 'SIM0123456789',
                    'tag_type': 'NTAG215',
                    'records': [
                        {
                            'type': 'text',
                            'payload': 'Simulated NFC tag content'
                        },
                        {
                            'type': 'uri',
                            'payload': 'https://example.com'
                        }
                    ]
                }
            )
        
        if not NFC_AVAILABLE:
            return ErrorResponse(
                status="error",
                message="NFC library not available"
            )
            
        try:
            # Use executor to run NFC read operation asynchronously
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(cls.executor, cls._read_tag_sync)
            return result
            
        except nfc.clf.CommunicationError as e:
            logger.error(f"Communication error during tag reading: {e}")
            return ErrorResponse(
                status="error",
                message=f"Communication error with NFC reader: {str(e)}"
            )
        except usb1.USBError as e:
            logger.error(f"USB error during tag reading: {e}")
            return ErrorResponse(
                status="error",
                message=f"USB error with NFC reader: {str(e)}"
            )
        except Exception as e:
            logger.exception("Error reading NFC tag: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f"Failed to read NFC tag: {str(e)}"
            )
    
    @classmethod
    def _read_tag_sync(cls) -> SuccessResponse:
        """Synchronous method to read an NFC tag"""
        clf = None
        try:
            # Initialize NFC reader
            clf = nfc.ContactlessFrontend('usb')
            
            # Read tag using on_connect callback for compatibility with both implementations
            cls._on_connect_read.tag = None
            tag = clf.connect(rdwr={'on-connect': cls._on_connect_read}, terminate=lambda: False)
            
            if hasattr(cls._on_connect_read, 'tag') and cls._on_connect_read.tag:
                tag = cls._on_connect_read.tag
                tag_id = tag.identifier.hex().upper()
                tag_type = str(type(tag))
                
                # Read NDEF records if available
                records = []
                if hasattr(tag, 'ndef') and tag.ndef:
                    for record in tag.ndef.records:
                        record_info = {
                            'type': cls._determine_record_type(record),
                            'payload': cls._extract_record_payload(record)
                        }
                        records.append(record_info)
                
                return SuccessResponse(
                    status="success",
                    data={
                        'tag_id': tag_id,
                        'tag_type': tag_type,
                        'records': records,
                        'technology': str(tag.dump()) if hasattr(tag, 'dump') else None
                    }
                )
            else:
                return ErrorResponse(
                    status="error",
                    message="Could not detect NFC tag"
                )
                    
        except Exception as e:
            logger.exception("Error in synchronous NFC tag read: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f"NFC tag read error: {str(e)}"
            )
        finally:
            if clf:
                clf.close()
            cls._reset_tag()
    
    @classmethod
    def _determine_record_type(cls, record) -> str:
        """Determine the type of an NDEF record"""
        if hasattr(ndef, 'TextRecord') and isinstance(record, ndef.TextRecord):
            return "text"
        elif hasattr(ndef, 'UriRecord') and isinstance(record, ndef.UriRecord):
            return "uri"
        elif hasattr(ndef, 'SmartPosterRecord') and isinstance(record, ndef.SmartPosterRecord):
            return "smartposter"
        elif hasattr(ndef, 'WifiSimpleConfig') and isinstance(record, ndef.WifiSimpleConfig):
            return "wifi"
        else:
            return "unknown"
    
    @classmethod
    def _extract_record_payload(cls, record) -> Any:
        """Extract the payload from an NDEF record"""
        if hasattr(ndef, 'TextRecord') and isinstance(record, ndef.TextRecord):
            return record.text
        elif hasattr(ndef, 'UriRecord') and isinstance(record, ndef.UriRecord):
            return record.uri
        elif hasattr(ndef, 'SmartPosterRecord') and isinstance(record, ndef.SmartPosterRecord):
            return record.uri
        elif hasattr(ndef, 'WifiSimpleConfig') and isinstance(record, ndef.WifiSimpleConfig):
            return {
                'ssid': record.ssid,
                'authentication': record.authentication_type,
                'encryption': record.encryption_type
            }
        else:
            # For unknown types, return as hex string
            return record.data.hex() if hasattr(record, 'data') else str(record)
    
    @classmethod
    async def write_text(cls, text: str, language_code: str = 'en') -> SuccessResponse:
        """
        Write a text record to an NFC tag
        
        Args:
            text: Text to write
            language_code: Language code to use
            
        Returns:
            SuccessResponse with operation result
        """
        logger.info(f"Writing text to NFC tag: {text}")
        
        if SIMULATION_MODE:
            return SuccessResponse(
                status="success",
                message=f"Text written to tag (simulated)",
                data={'written': True}
            )
        
        if not NFC_AVAILABLE:
            return ErrorResponse(
                status="error",
                message="NFC library not available"
            )
            
        try:
            # Use executor to run NFC write operation asynchronously
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                cls.executor,
                lambda: cls._write_text_sync(text, language_code)
            )
            
            if success:
                return SuccessResponse(
                    status="success",
                    message="Text written to tag",
                    data={'written': True}
                )
            else:
                return ErrorResponse(
                    status="error",
                    message="Failed to write text to tag"
                )
                
        except nfc.clf.CommunicationError as e:
            logger.error(f"Communication error with NFC reader: {e}")
            return ErrorResponse(
                status="error",
                message=f"Communication error with NFC reader: {str(e)}"
            )
        except usb1.USBError as e:
            logger.error(f"USB error with NFC reader: {e}")
            return ErrorResponse(
                status="error",
                message=f"USB error with NFC reader: {str(e)}"
            )
        except Exception as e:
            logger.exception("Error writing to NFC tag: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f"Failed to write to NFC tag: {str(e)}"
            )
    
    @classmethod
    def _write_text_sync(cls, text: str, language_code: str = 'en') -> bool:
        """Synchronous method to write text to an NFC tag"""
        clf = None
        try:
            # Initialize NFC reader
            clf = nfc.ContactlessFrontend('usb')
            
            # Create record and connect to tag
            success = clf.connect(
                rdwr={'on-connect': lambda tag: cls._on_connect_write_text(tag, text)},
                terminate=lambda: False
            )
            
            return success is not None
                
        except Exception as e:
            logger.exception("Error in synchronous NFC tag write: %s", str(e))
            return False
        finally:
            if clf:
                clf.close()
    
    @classmethod
    async def write_url(cls, url: str) -> SuccessResponse:
        """
        Write a URL to an NFC tag
        
        Args:
            url: URL to write
            
        Returns:
            SuccessResponse with operation result
        """
        logger.info(f"Writing URL to NFC tag: {url}")
        
        if SIMULATION_MODE:
            return SuccessResponse(
                status="success",
                message=f"URL written to tag (simulated)",
                data={'written': True, 'url': url}
            )
        
        if not NFC_AVAILABLE:
            return ErrorResponse(
                status="error",
                message="NFC library not available"
            )
            
        try:
            # Use executor to run NFC write operation asynchronously
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                cls.executor,
                lambda: cls._write_url_sync(url)
            )
            
            if success:
                return SuccessResponse(
                    status="success",
                    message="URL written to tag",
                    data={'written': True, 'url': url}
                )
            else:
                return ErrorResponse(
                    status="error",
                    message="Failed to write URL to tag"
                )
                
        except Exception as e:
            logger.exception("Error writing URL to NFC tag: %s", str(e))
            return ErrorResponse(
                status="error",
                message=f"Failed to write URL to NFC tag: {str(e)}"
            )
    
    @classmethod
    def _write_url_sync(cls, url: str) -> bool:
        """Synchronous method to write URL to an NFC tag"""
        clf = None
        try:
            # Initialize NFC reader
            clf = nfc.ContactlessFrontend('usb')
            
            # Define on-connect callback
            def on_connect_write_url(tag):
                if tag.ndef is not None:
                    try:
                        record = nfc.ndef.UriRecord(url)
                        message = nfc.ndef.Message(record)
                        tag.ndef.records = message.records
                        tag.ndef.write()
                        logger.info(f"URL successfully written to tag: {url}")
                        return True
                    except Exception as e:
                        logger.error(f"Error writing URL to tag: {e}")
                        return False
                else:
                    logger.warning("Tag does not support NDEF.")
                    return False
            
            # Connect to tag
            success = clf.connect(
                rdwr={'on-connect': on_connect_write_url},
                terminate=lambda: False
            )
            
            return success is not None
                
        except Exception as e:
            logger.exception("Error in synchronous NFC URL write: %s", str(e))
            return False
        finally:
            if clf:
                clf.close()
    
    @classmethod
    async def get_status(cls) -> SuccessResponse:
        """
        Get the status of the NFC reader
        
        Returns:
            SuccessResponse with reader status
        """
        logger.info("Checking NFC reader status")
        
        if SIMULATION_MODE:
            return SuccessResponse(
                status="success",
                data={'reader_status': 'Simulated Reader Active'}
            )
        
        if not NFC_AVAILABLE:
            return ErrorResponse(
                status="error",
                message="NFC library not available"
            )
            
        try:
            clf = nfc.ContactlessFrontend('usb')
            active = clf.device is not None
            clf.close()
            
            if active:
                return SuccessResponse(
                    status="success",
                    data={'reader_status': 'Reader Active'}
                )
            else:
                return SuccessResponse(
                    status="warning",
                    message="NFC reader not active",
                    data={'reader_status': 'Reader Inactive'}
                )
                
        except nfc.clf.CommunicationError as e:
            logger.error(f"Communication error with NFC reader: {e}")
            return ErrorResponse(
                status="error",
                message=f"Communication error with NFC reader: {str(e)}",
                data={'reader_status': 'Error'}
            )
        except usb1.USBError as e:
            logger.error(f"USB error with NFC reader: {e}")
            return ErrorResponse(
                status="error",
                message=f"USB error with NFC reader: {str(e)}",
                data={'reader_status': 'Error'}
            )
        except Exception as e:
            logger.error(f"An unexpected error occurred while checking reader status: {e}", exc_info=True)
            return ErrorResponse(
                status="error",
                message=f"Failed to check reader status: {str(e)}",
                data={'reader_status': 'Error'}
            )
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if an NFC reader is available"""
        logger.debug("Checking if NFC reader is available")
        try:
            if SIMULATION_MODE:
                logger.debug("Simulation mode enabled, reporting NFC as available")
                return True
            
            if not NFC_AVAILABLE:
                return False
                
            # Try to open a connection to NFC reader
            clf = nfc.ContactlessFrontend('usb')
            is_available = clf.device is not None
            clf.close()
            logger.debug(f"NFC reader availability check: {is_available}")
            return is_available
        except Exception as e:
            logger.debug(f"NFC reader not available: {e}")
            return False
    
    # Callback functions and helper methods
    
    @staticmethod
    def _on_connect_read(tag) -> bool:
        """Callback function for reading NFC tag."""
        logger.debug(f"Tag connected for reading: {tag}")
        if isinstance(tag, nfc.tag.Tag):
            NFCManager._on_connect_read.tag = tag
            return True
        return False
    
    @staticmethod
    def _on_connect_write_text(tag, text: str) -> bool:
        """Callback function for writing text to NFC tag."""
        logger.debug(f"Tag connected for writing: {tag}, Text: {text}")
        if tag.ndef is not None:
            try:
                record = nfc.ndef.TextRecord(text, encoding="utf-8")
                message = nfc.ndef.Message(record)
                tag.ndef.records = message.records
                tag.ndef.write()
                logger.info(f"Text successfully written to tag: {text}")
                return True
            except nfc.ndef.WriteError as e:
                logger.error(f"Failed to write to tag (WriteError): {e}")
                return False
            except Exception as e:
                logger.error(f"Error writing to tag: {e}")
                return False
        else:
            logger.warning("Tag does not support NDEF.")
            return False
    
    @staticmethod
    def _reset_tag():
        """Resets the tag attribute after reading."""
        if hasattr(NFCManager._on_connect_read, 'tag'):
            del NFCManager._on_connect_read.tag
    
    @classmethod
    def close(cls):
        """Close the NFC device"""
        if cls._device:
            cls._device.close()
            cls._device = None
            logger.info("NFC device closed")