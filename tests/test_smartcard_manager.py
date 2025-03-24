import pytest
import logging
from app import app
from smartcard_manager import SmartcardManager
from smartcard.Exceptions import CardConnectionException, NoCardException
from unittest.mock import patch

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s')
logger = logging.getLogger(__name__)

# Mocking the readers() function for testing in environments without actual readers
@pytest.fixture
def mock_readers(monkeypatch):
    """Mocks the readers() function to return a list of mock readers."""
    class MockConnection:
        def connect(self):
            logger.debug("MockConnection: Connecting to card...")
            pass
        def disconnect(self):
            logger.debug("MockConnection: Disconnecting from card...")
            pass
        def getATR(self):
            logger.debug("MockConnection: Getting ATR...")
            return b'\x3B\x8F\x80\x01'
        def transmit(self, apdu):
            logger.debug(f"MockConnection: Transmitting APDU: {apdu}")
            return [0x61], 0x90, 0x00

    class MockReader:
        def __init__(self, name):
            self.name = name
        def createConnection(self):
            logger.debug(f"MockReader: Creating connection for reader: {self.name}")
            return MockConnection()
        def __str__(self):
            return self.name

    def mock_readers_func():
        mock_readers_list = [MockReader("Mock Reader 1"), MockReader("Mock Reader 2")]
        logger.debug(f"mock_readers_func: Returning mock readers: {mock_readers_list}")
        return mock_readers_list

    monkeypatch.setattr("poc.smartcard_manager.readers", mock_readers_func)
    logger.debug("mock_readers fixture setup complete.")


class TestSmartcardManager:
    def test_is_valid_apdu_format_valid(self):
        logger.info("Testing is_valid_apdu_format with valid APDU")
        assert SmartcardManager.is_valid_apdu_format("00 A4 04 00 08 A0000000030000")
        logger.info("is_valid_apdu_format test passed for valid APDU")

    def test_is_valid_apdu_format_invalid_length(self):
        logger.info("Testing is_valid_apdu_format with invalid APDU length")
        assert not SmartcardManager.is_valid_apdu_format("00 A4 04 00")
        logger.info("is_valid_apdu_format test passed for invalid APDU length")

    def test_is_valid_apdu_format_invalid_characters(self):
        logger.info("Testing is_valid_apdu_format with invalid APDU characters")
        assert not SmartcardManager.is_valid_apdu_format("00 A4 04 0G 08 A0000000030000")
        logger.info("is_valid_apdu_format test passed for invalid APDU characters")

    def test_is_valid_apdu_format_empty_string(self):
        logger.info("Testing is_valid_apdu_format with empty string")
        assert not SmartcardManager.is_valid_apdu_format("")
        logger.info("is_valid_apdu_format test passed for empty string")

    def test_is_valid_apdu_format_none(self):
        logger.info("Testing is_valid_apdu_format with None")
        assert not SmartcardManager.is_valid_apdu_format(None)
        logger.info("is_valid_apdu_format test passed for None")

    def test_get_sw_meaning_success(self):
        logger.info("Testing get_sw_meaning with success status word")
        assert SmartcardManager.get_sw_meaning(0x90, 0x00) == "Success"
        logger.info("get_sw_meaning test passed for success status word")

    def test_get_sw_meaning_wrong_length(self):
        logger.info("Testing get_sw_meaning with wrong length status word")
        assert SmartcardManager.get_sw_meaning(0x67, 0x00) == "Wrong length"
        logger.info("get_sw_meaning test passed for wrong length status word")

    def test_get_sw_meaning_unknown(self):
        logger.info("Testing get_sw_meaning with unknown status word")
        assert SmartcardManager.get_sw_meaning(0x00, 0x00) == "Unknown status"
        logger.info("get_sw_meaning test passed for unknown status word")

    def test_get_sw_meaning_more_data(self):
        logger.info("Testing get_sw_meaning with more data status word")
        assert SmartcardManager.get_sw_meaning(0x61, 0x1A) == "More data available, use GET RESPONSE command"
        logger.info("get_sw_meaning test passed for more data status word")

    def test_get_sw_meaning_wrong_le(self):
        logger.info("Testing get_sw_meaning with wrong Le status word")
        assert SmartcardManager.get_sw_meaning(0x6C, 0x05) == "Wrong Le field; indicate the exact number of available data bytes"
        logger.info("get_sw_meaning test passed for wrong Le status word")

    @patch("poc.smartcard_manager.readers")
    def test_get_atr_success(self, mock_readers):
        logger.info("Testing get_atr with successful ATR retrieval")
        class MockConnection:
            def connect(self):
                logger.debug("MockConnection: Connecting to card...")
                pass
            def disconnect(self):
                logger.debug("MockConnection: Disconnecting from card...")
                pass
            def getATR(self):
                logger.debug("MockConnection: Getting ATR...")
                return b'\x3B\x8F\x80\x01'

        class MockReader:
            def createConnection(self):
                logger.debug("MockReader: Creating connection...")
                return MockConnection()
            def __str__(self):
                return "Mock Reader"

        mock_readers.return_value = [MockReader()]
        result = SmartcardManager.get_atr(0)
        assert result['status'] == 'success'
        assert result['atr'] == '3B 8F 80 01'
        logger.info("get_atr test passed for successful ATR retrieval")

    @patch("poc.smartcard_manager.readers")
    def test_get_atr_no_readers(self, mock_readers):
        logger.info("Testing get_atr with no readers available")
        mock_readers.return_value = []
        result = SmartcardManager.get_atr(0)
        assert result['status'] == 'error'
        assert result['message'] == 'No smartcard readers found'
        logger.info("get_atr test passed for no readers available")

    @patch("poc.smartcard_manager.readers")
    def test_get_atr_invalid_reader_index(self, mock_readers):
        logger.info("Testing get_atr with invalid reader index")
        class MockReader:
            def __str__(self):
                return "Mock Reader"
        mock_readers.return_value = [MockReader()]
        result = SmartcardManager.get_atr(1)
        assert result['status'] == 'error'
        assert result['message'] == 'Invalid reader index'
        logger.info("get_atr test passed for invalid reader index")

    @patch("poc.smartcard_manager.readers")
    def test_get_atr_card_connection_exception(self, mock_readers):
        logger.info("Testing get_atr with CardConnectionException")
        class MockConnection:
            def connect(self):
                logger.debug("MockConnection: Attempting to connect...")
                raise CardConnectionException("Connection failed")
            def disconnect(self):
                logger.debug("MockConnection: Disconnecting...")
                pass

            def getATR(self):
                logger.debug("MockConnection: Getting ATR...")
                return b'\x3B\x8F\x80\x01'

        class MockReader:
            def createConnection(self):
                logger.debug("MockReader: Creating connection...")
                return MockConnection()
            def __str__(self):
                return "Mock Reader"

        mock_readers.return_value = [MockReader()]
        result = SmartcardManager.get_atr(0)
        assert result['status'] == 'error'
        assert "Failed to connect to card" in result['message']
        logger.info("get_atr test passed for CardConnectionException")

    @patch("poc.smartcard_manager.readers")
    def test_get_atr_no_card_exception(self, mock_readers):
        logger.info("Testing get_atr with NoCardException")
        class MockConnection:
            def connect(self):
                logger.debug("MockConnection: Attempting to connect...")
                raise NoCardException("No card present")
            def disconnect(self):
                logger.debug("MockConnection: Disconnecting...")
                pass
            def getATR(self):
                logger.debug("MockConnection: Getting ATR...")
                return b'\x3B\x8F\x80\x01'

        class MockReader:
            def createConnection(self):
                logger.debug("MockReader: Creating connection...")
                return MockConnection()
            def __str__(self):
                return "Mock Reader"

        mock_readers.return_value = [MockReader()]
        result = SmartcardManager.get_atr(0)
        assert result['status'] == 'error'
        assert result['message'] == 'No card present'
        logger.info("get_atr test passed for NoCardException")

    @patch("poc.smartcard_manager.readers")
    def test_transmit_apdu_success(self, mock_readers):
        logger.info("Testing transmit_apdu with successful transmission")
        class MockConnection:
            def connect(self):
                logger.debug("MockConnection: Connecting to card...")
                pass
            def disconnect(self):
                logger.debug("MockConnection: Disconnecting from card...")
                pass
            def transmit(self, apdu):
                logger.debug(f"MockConnection: Transmitting APDU: {apdu}")
                return [0x61], 0x90, 0x00

        class MockReader:
            def createConnection(self):
                logger.debug("MockReader: Creating connection...")
                return MockConnection()
            def __str__(self):
                return "Mock Reader"

        mock_readers.return_value = [MockReader()]
        result = SmartcardManager.transmit_apdu(0, "00 A4 04 00 08")
        assert result['status'] == 'success'
        assert result['sw'] == '9000'
        assert result['response'] == '61'
        logger.info("transmit_apdu test passed for successful transmission")

    @patch("poc.smartcard_manager.readers")
    def test_transmit_apdu_no_apdu(self, mock_readers):
        logger.info("Testing transmit_apdu with no APDU command provided")
        result = SmartcardManager.transmit_apdu(0, None)
        assert result['status'] == 'error'
        assert result['message'] == 'No APDU command provided'
        logger.info("transmit_apdu test passed for no APDU command provided")

    @patch("poc.smartcard_manager.readers")
    def test_transmit_apdu_invalid_reader_index(self, mock_readers):
        logger.info("Testing transmit_apdu with invalid reader index")
        class MockReader:
            def __str__(self):
                return "Mock Reader"
        mock_readers.return_value = [MockReader()]
        result = SmartcardManager.transmit_apdu(1, "00 A4 04 00 08")
        assert result['status'] == 'error'
        assert result['message'] == 'Invalid reader index'
        logger.info("transmit_apdu test passed for invalid reader index")

    @patch("poc.smartcard_manager.readers")
    def test_transmit_apdu_card_connection_exception(self, mock_readers):
        logger.info("Testing transmit_apdu with CardConnectionException")
        class MockConnection:
            def connect(self):
                logger.debug("MockConnection: Connecting to card...")
                raise CardConnectionException("Connection failed")
            def disconnect(self):
                logger.debug("MockConnection: Disconnecting from card...")
                pass
            def transmit(self, apdu):
                logger.debug(f"MockConnection: Transmitting APDU: {apdu}")
                return [0x61], 0x90, 0x00

        class MockReader:
            def createConnection(self):
                logger.debug("MockReader: Creating connection...")
                return MockConnection()
            def __str__(self):
                return "Mock Reader"

        mock_readers.return_value = [MockReader()]
        result = SmartcardManager.transmit_apdu(0, "00 A4 04 00 08")
        assert result['status'] == 'error'
        assert "Failed to transmit APDU to card" in result['message']
        logger.info("transmit_apdu test passed for CardConnectionException")

    @patch("poc.smartcard_manager.readers")
    def test_transmit_apdu_no_card_exception(self, mock_readers):
        logger.info("Testing transmit_apdu with NoCardException")
        class MockConnection:
            def connect(self):
                logger.debug("MockConnection: Connecting to card...")
                raise NoCardException("No card present")
            def disconnect(self):
                logger.debug("MockConnection: Disconnecting from card...")
                pass
            def transmit(self, apdu):
                logger.debug(f"MockConnection: Transmitting APDU: {apdu}")
                return [0x61], 0x90, 0x00

        class MockReader:
            def createConnection(self):
                logger.debug("MockReader: Creating connection...")
                return MockConnection()
            def __str__(self):
                return "Mock Reader"

        mock_readers.return_value = [MockReader()]
        result = SmartcardManager.transmit_apdu(0, "00 A4 04 00 08")
        assert result['status'] == 'error'
        assert result['message'] == 'No card present'
        logger.info("transmit_apdu test passed for NoCardException")

    @patch("poc.smartcard_manager.readers")
    def test_transmit_apdu_invalid_apdu_format(self, mock_readers):
        logger.info("Testing transmit_apdu with invalid APDU format")
        class MockConnection:
            def connect(self):
                logger.debug("MockConnection: Connecting to card...")
                pass
            def disconnect(self):
                logger.debug("MockConnection: Disconnecting from card...")
                pass
            def transmit(self, apdu):
                logger.debug(f"MockConnection: Transmitting APDU: {apdu}")
                return [0x61], 0x90, 0x00

        class MockReader:
            def createConnection(self):
                logger.debug("MockReader: Creating connection...")
                return MockConnection()
            def __str__(self):
                return "Mock Reader"

        mock_readers.return_value = [MockReader()]
        result = SmartcardManager.transmit_apdu(0, "00 A4 04 0G 08")
        assert result['status'] == 'error'
        assert 'Invalid APDU format' in result['message']
        logger.info("transmit_apdu test passed for invalid APDU format")

    @patch("poc.smartcard_manager.readers")
    def test_card_status_present(self, mock_readers):
        logger.info("Testing card_status when card is present")
        class MockConnection:
            def connect(self):
                logger.debug("MockConnection: Connecting to card...")
                pass
            def disconnect(self):
                logger.debug("MockConnection: Disconnecting from card...")
                pass

        class MockReader:
            def createConnection(self):
                logger.debug("MockReader: Creating connection...")
                return MockConnection()
            def __str__(self):
                return "Mock Reader"

        mock_readers.return_value = [MockReader()]
        result = SmartcardManager.card_status(0)
        assert result['status'] == 'success'
        assert result['present']
        logger.info("card_status test passed when card is present")

    @patch("poc.smartcard_manager.readers")
    def test_card_status_no_card(self, mock_readers):
        logger.info("Testing card_status when no card is present")
        class MockConnection:
            def connect(self):
                logger.debug("MockConnection: Connecting to card...")
                raise NoCardException("No card present")
            def disconnect(self):
                logger.debug("MockConnection: Disconnecting from card...")
                pass

        class MockReader:
            def createConnection(self):
                logger.debug("MockReader: Creating connection...")
                return MockConnection()
            def __str__(self):
                return "Mock Reader"

        mock_readers.return_value = [MockReader()]
        result = SmartcardManager.card_status(0)
        assert result['status'] == 'success'
        assert not result['present']
        logger.info("card_status test passed when no card is present")

    @patch("poc.smartcard_manager.readers")
    def test_card_status_no_readers(self, mock_readers):
        logger.info("Testing card_status when no readers are found")
        mock_readers.return_value = []
        result = SmartcardManager.card_status(0)
        assert result['status'] == 'error'
        assert result['message'] == 'No smartcard readers found'
        logger.info("card_status test passed when no readers are found")

    @patch("poc.smartcard_manager.readers")
    def test_card_status_invalid_reader_index(self, mock_readers):
        logger.info("Testing card_status with an invalid reader index")
        class MockReader:
            def __str__(self):
                return "Mock Reader"

        mock_readers.return_value = [MockReader()]
        result = SmartcardManager.card_status(1)
        assert result['status'] == 'error'
        assert result['message'] == 'Invalid reader index'
        logger.info("card_status test passed with an invalid reader index")

    @patch("poc.smartcard_manager.readers")
    def test_test_reader_connection_success(self, mock_readers):
        logger.info("Testing test_reader_connection with a successful connection")
        class MockConnection:
            def connect(self):
                logger.debug("MockConnection: Connecting to card...")
                pass
            def disconnect(self):
                logger.debug("MockConnection: Disconnecting from card...")
                pass

        class MockReader:
            def createConnection(self):
                logger.debug("MockReader: Creating connection...")
                return MockConnection()
            def __str__(self):
                return "Mock Reader"

        mock_readers.return_value = [MockReader()]
        result = SmartcardManager.test_reader_connection(0)
        assert result['status'] == 'success'
        assert result['message'] == 'Reader functional'
        logger.info("test_reader_connection test passed with a successful connection")

    @patch("poc.smartcard_manager.readers")
    def test_test_reader_connection_no_readers(self, mock_readers):
        logger.info("Testing test_reader_connection when no readers are found")
        mock_readers.return_value = []
        result = SmartcardManager.test_reader_connection(0)
        assert result['status'] == 'error'
        assert result['message'] == 'No smartcard readers found'
        logger.info("test_reader_connection test passed when no readers are found")

    @patch("poc.smartcard_manager.readers")
    def test_test_reader_connection_invalid_reader_index(self, mock_readers):
        logger.info("Testing test_reader_connection with an invalid reader index")
        class MockReader:
            def __str__(self):
                return "Mock Reader"

        mock_readers.return_value = [MockReader()]
        result = SmartcardManager.test_reader_connection(1)
        assert result['status'] == 'error'
        assert result['message'] == 'Invalid reader index'
        logger.info("test_reader_connection test passed with an invalid reader index")

    @patch("poc.smartcard_manager.readers")
    def test_test_reader_connection_connection_exception(self, mock_readers):
        logger.info("Testing test_reader_connection with a connection exception")
        class MockConnection:
            def connect(self):
                logger.debug("MockConnection: Connecting to card...")
                raise CardConnectionException("Connection failed")
            def disconnect(self):
                logger.debug("MockConnection: Disconnecting from card...")
                pass

        class MockReader:
            def createConnection(self):
                logger.debug("MockReader: Creating connection...")
                return MockConnection()
            def __str__(self):
                return "Mock Reader"

        mock_readers.return_value = [MockReader()]
        result = SmartcardManager.test_reader_connection(0)
        assert result['status'] == 'error'
        assert "Connection failed" in result['message']
        logger.info("test_reader_connection test passed with a connection exception")

    def test_analyze_atr_empty(self):
        logger.info("Testing analyze_atr with an empty ATR")
        atr = b''
        result = SmartcardManager.analyze_atr(atr)
        assert result == {}
        logger.info("analyze_atr test passed with an empty ATR")

    def test_analyze_atr_direct_convention(self):
        logger.info("Testing analyze_atr with a direct convention ATR")
        atr = b'\x3B\x8F\x80\x01'
        result = SmartcardManager.analyze_atr(atr)
        assert result['TS'] == 'Direct Convention'
        assert result['T0'] == '8F'
        assert result['HistoricalBytes'] == '8F 80 01'
        logger.info("analyze_atr test passed with a direct convention ATR")

    def test_analyze_atr_index_error(self):
        logger.info("Testing analyze_atr with an incomplete ATR causing an IndexError")
        atr = b'\x3B'
        result = SmartcardManager.analyze_atr(atr)
        assert "Incomplete ATR for analysis" in result.get("Error", "")
        logger.info("analyze_atr test passed with an incomplete ATR")