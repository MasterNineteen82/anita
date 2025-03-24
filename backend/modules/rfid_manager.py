import logging
import serial
from backend.models import (
    RFIDTagResponse, RFIDReaderInfo, RFIDTagInfo, 
    SuccessResponse, ErrorResponse
)
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class RFIDManager:
    """
    Manages RFID reader interactions, including connecting, reading, and writing data.

    Enhancements:
    - Abstract hardware interaction to support different RFID reader models.
    - Implement error handling and retry mechanisms for robust operation.
    - Add support for different RFID tag types and protocols.
    - Implement a caching mechanism to reduce redundant reads.
    - Integrate with a configuration system for reader settings.
    """

    def __init__(self, config=None):
        """
        Initializes the RFIDManager with optional configuration.

        Args:
            config (dict, optional): Configuration settings for the RFID reader.
        """
        self.config = config or self._default_config()
        self.reader = None  # Placeholder for the RFID reader instance
        self.is_connected = False
        self.cache = {}  # Simple cache for tag data
        self.reader_info = RFIDReaderInfo(  # Initialize RFIDReaderInfo
            reader_id="default_reader",
            reader_type=self.config.get('reader_type', 'Generic'),
            location="unknown"
        )

        # Setup logger
        self.logger = logging.getLogger(__name__)

    def _default_config(self):
        """
        Returns a default configuration for the RFID reader.

        This should be overridden in subclasses to provide reader-specific defaults.
        """
        return {
            'reader_type': 'Generic',
            'port': '/dev/ttyUSB0',
            'baudrate': 9600,
            'timeout': 1
        }

    def connect(self):
        """
        Connects to the RFID reader.

        Returns:
            bool: True if the connection was successful, False otherwise.
        """
        try:
            # Abstracted reader initialization
            reader_type = self.config.get('reader_type', 'Generic')
            if reader_type == 'Generic':
                # Example using pyserial (replace with actual RFID library)
                self.reader = serial.Serial(
                    port=self.config['port'],
                    baudrate=self.config['baudrate'],
                    timeout=self.config['timeout']
                )
                self.is_connected = True
                self.reader_info.status = "connected"  # Update reader status
                self.logger.info(f"Connected to RFID reader on {self.config['port']}")
                return True
            else:
                self.logger.error(f"Unsupported reader type: {reader_type}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to connect to RFID reader: {e}")
            self.is_connected = False
            self.reader_info.status = "disconnected"  # Update reader status
            return False

    def disconnect(self):
        """
        Disconnects from the RFID reader.
        """
        if self.reader and self.is_connected:
            try:
                self.reader.close()
                self.is_connected = False
                self.reader = None
                self.reader_info.status = "disconnected"  # Update reader status
                self.logger.info("Disconnected from RFID reader.")
            except Exception as e:
                self.logger.error(f"Error disconnecting from RFID reader: {e}")

    def read_tag(self):
        """
        Reads data from an RFID tag.
        
        Returns:
            RFIDTagResponse: The data read from the tag, with status info
        """
        if not self.is_connected:
            self.logger.warning("RFID reader is not connected.")
            return RFIDTagResponse(
                tag_id="unknown",
                success=False,
                message="RFID reader is not connected"
            )

        try:
            # Implement RFID read command based on the reader type
            self.reader.write(b'READ\n')  # Example command
            tag_data = self.reader.readline().decode('utf-8').strip()

            if tag_data:
                # Parse the tag data - in a real implementation you'd extract tag_id
                # Here we're using a placeholder approach
                parts = tag_data.split(':')
                tag_id = parts[0] if len(parts) > 1 else "unknown"
                data = parts[1] if len(parts) > 1 else tag_data
                
                # Update cache
                self.cache['last_read'] = tag_data
                
                self.logger.info(f"Tag data read: {tag_data}")
                
                # Create RFIDTagInfo instance
                tag_info = RFIDTagInfo(
                    tag_id=tag_id,
                    data=data,
                    timestamp=datetime.now()
                )
                
                return RFIDTagResponse(
                    tag_id=tag_id,
                    data=data,
                    timestamp=datetime.now(),
                    success=True,
                    tag_info=tag_info  # Include RFIDTagInfo in the response
                )
            else:
                self.logger.warning("No data received from tag.")
                return RFIDTagResponse(
                    tag_id="unknown",
                    success=False,
                    message="No data received from tag"
                )
        except Exception as e:
            self.logger.error(f"Error reading from RFID tag: {e}")
            return RFIDTagResponse(
                tag_id="unknown",
                success=False,
                message=f"Error reading from RFID tag: {str(e)}"
            )

    def write_tag(self, data):
        """
        Writes data to an RFID tag.

        Args:
            data (str): The data to write to the tag.

        Returns:
            bool: True if the write was successful, False otherwise.
        """
        if not self.is_connected:
            self.logger.warning("RFID reader is not connected.")
            return False

        try:
            # Implement RFID write command based on the reader type
            # This is a placeholder and needs to be replaced with actual RFID commands
            command = f'WRITE {data}\n'
            self.reader.write(command.encode('utf-8'))
            response = self.reader.readline().decode('utf-8').strip()

            if 'OK' in response:  # Example success response
                self.logger.info(f"Data written to tag: {data}")
                return True
            else:
                self.logger.warning(f"Write failed: {response}")
                return False
        except Exception as e:
            self.logger.error(f"Error writing to RFID tag: {e}")
            return False

    def get_last_read(self):
        """
        Returns the last successfully read tag data from the cache.

        Returns:
            str: The last read tag data, or None if no data has been read.
        """
        return self.cache.get('last_read')

    def is_tag_present(self):
        """
        Checks if a tag is currently present within the reader's range.

        This method provides a basic way to check for tag presence without reading the tag data.
        It can be useful for triggering actions when a tag enters or leaves the reader's field.

        Returns:
            bool: True if a tag is present, False otherwise.
        """
        if not self.is_connected:
            self.logger.warning("RFID reader is not connected.")
            return False

        try:
            # Send an inventory command to check for tag presence
            self.reader.write(b'INVENTORY\n')  # Example command
            response = self.reader.readline().decode('utf-8').strip()

            # Check if the response indicates a tag is present
            if 'TAG_FOUND' in response:  # Example response
                self.logger.info("Tag is present.")
                return True
            else:
                self.logger.info("No tag found.")
                return False
        except Exception as e:
            self.logger.error(f"Error checking for tag presence: {e}")
            return False

    def set_config(self, config):
        """
        Updates the RFIDManager's configuration.

        Args:
            config (dict): New configuration settings.
        """
        if not isinstance(config, dict):
            self.logger.error("Configuration must be a dictionary.")
            return

        self.config.update(config)
        self.logger.info("RFIDManager configuration updated.")

    def get_config(self):
        """
        Returns the current configuration of the RFIDManager.

        Returns:
            dict: The current configuration settings.
        """
        return self.config

    def get_reader_info(self):
        """
        Returns the RFIDReaderInfo object containing information about the reader.

        Returns:
            RFIDReaderInfo: The reader information.
        """
        return self.reader_info

    def clear_cache(self):
        """
        Clears the tag data cache.
        """
        self.cache.clear()
        self.logger.info("RFIDManager cache cleared.")

    def __enter__(self):
        """
        Allows the RFIDManager to be used as a context manager.
        """
        if not self.is_connected:
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Handles cleanup when exiting the context.
        """
        self.disconnect()
        if exc_type:
            self.logger.error(f"Exception occurred: {exc_type} - {exc_val}")
        return False  # Allows exceptions to propagate

if __name__ == '__main__':
    # Example Usage
    try:
        rfid_manager = RFIDManager(config={'port': 'COM3', 'baudrate': 115200})

        if rfid_manager.connect():
            print("Connected to RFID reader.")

            # Get reader info
            reader_info = rfid_manager.get_reader_info()
            print(f"Reader Info: {reader_info}")

            # Check if a tag is present
            if rfid_manager.is_tag_present():
                print("Tag is present.")

                # Read tag data
                tag_data = rfid_manager.read_tag()
                if tag_data:
                    print(f"Tag data: {tag_data}")

                    # Write new data to the tag
                    new_data = "New RFID Data"
                    if rfid_manager.write_tag(new_data):
                        print(f"Successfully wrote '{new_data}' to the tag.")
                    else:
                        print("Failed to write data to the tag.")
                else:
                    print("Failed to read tag data.")
            else:
                print("No tag found.")

            # Get last read data from cache
            last_read = rfid_manager.get_last_read()
            if last_read:
                print(f"Last read data from cache: {last_read}")
            else:
                print("No data in cache.")

            # Clear the cache
            rfid_manager.clear_cache()
            print("Cache cleared.")

            # Disconnect from the RFID reader
            rfid_manager.disconnect()
            print("Disconnected from RFID reader.")
        else:
            print("Failed to connect to RFID reader.")
    except Exception as e:
        print(f"An error occurred: {e}")