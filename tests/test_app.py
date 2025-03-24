import pytest
from fastapi.testclient import TestClient
from app import app  # Assuming app is the FastAPI instance
import logging
from unittest.mock import patch
import os

# Define the log file path
log_file_path = os.path.join(os.path.dirname(__file__), "test_app.log")

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s',
    filename=log_file_path,  # Output to a log file
    filemode='w'  # Overwrite the log file on each run
)
logger = logging.getLogger(__name__)

@pytest.fixture
def client():
    logger.info("Creating FastAPI test client")
    with TestClient(app) as client:
        yield client
        logger.info("Test client destroyed")

# Health Check Test
def test_api_health_check(client):
    logger.info("Testing /api/health")
    response = client.get("/api/health")
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "version" in response.json()
    logger.info("/api/health test passed")
    
@patch("routes.SmartcardManager.get_atr")
def test_api_smartcard_atr_success(mock_get_atr, client):
    logger.info("Testing /api/smartcard/atr success case")
    mock_get_atr.return_value = {"status": "success", "data": {"atr": "3B6E00000073C84000000000"}}
    response = client.get("/api/smartcard/atr?reader=0")
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "atr" in response.json()["data"]
    logger.info("/api/smartcard/atr success test passed")

@patch("routes.SmartcardManager.get_atr")
def test_api_smartcard_atr_no_card(mock_get_atr, client):
    logger.info("Testing /api/smartcard/atr with no card present")
    mock_get_atr.return_value = {"status": "error", "message": "No card present"}
    response = client.get("/api/smartcard/atr?reader=0")
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json()}")
    assert response.status_code == 500  # Handle_errors raises HTTP 500
    assert "No card present" in response.json()["detail"]
    logger.info("/api/smartcard/atr no card test passed")

@patch("routes.SmartcardManager.transmit_apdu")
def test_api_smartcard_transmit_success(mock_transmit_apdu, client):
    logger.info("Testing /api/smartcard/transmit success case")
    mock_transmit_apdu.return_value = {"status": "success", "data": {"response": "9000"}}
    response = client.post("/api/smartcard/transmit", json={"reader": 0, "apdu": "00 A4 04 00 0E"})
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "response" in response.json()["data"]
    logger.info("/api/smartcard/transmit success test passed")

@patch("routes.SmartcardManager.card_status")
def test_api_detect_smartcard_success(mock_card_status, client):
    logger.info("Testing /api/smartcard/detect success case")
    mock_card_status.return_value = {"status": "success", "data": {"present": True}}
    response = client.get("/api/smartcard/detect")
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["data"]["present"]
    logger.info("/api/smartcard/detect success test passed")
    
@patch("routes.NFCManager.read_tag")
def test_api_nfc_read_success(mock_nfc_read, client):
    logger.info("Testing /api/nfc/read success case")
    mock_nfc_read.return_value = {"status": "success", "data": {"tag_data": {"type": "Type A", "id": "1234"}}}
    response = client.get("/api/nfc/read")
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "data" in response.json()["data"]
    logger.info("/api/nfc/read success test passed")

@patch("routes.NFCManager.write_text")
def test_api_nfc_write_text_success(mock_nfc_write_text, client):
    logger.info("Testing /api/nfc/write_text success case")
    mock_nfc_write_text.return_value = {"status": "success", "data": {"message": "Text written"}}
    response = client.post("/api/nfc/write_text", json={"text": "test"})
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "message" in response.json()["data"]
    logger.info("/api/nfc/write_text success test passed")

@patch("routes.NFCManager.discover")
def test_api_nfc_discover(mock_discover, client):
    logger.info("Testing /api/nfc/discover")
    mock_discover.return_value = {"status": "success", "data": {"devices": ["Device1", "Device2"]}}
    response = client.get("/api/nfc/discover")
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "devices" in response.json()["data"]
    logger.info("/api/nfc/discover test passed")
    
@patch("routes.CardManager.get_card_config")
def test_api_get_card_config(mock_get_card_config, client):
    logger.info("Testing /api/card/config (GET)")
    mock_get_card_config.return_value = {"status": "success", "data": {"config": {"param1": "value1"}}}
    response = client.get("/api/card/config?type=test_card")
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "config" in response.json()["data"]
    logger.info("/api/card/config (GET) test passed")

@patch("routes.CardManager.set_card_config")
def test_api_set_card_config(mock_set_card_config, client):
    logger.info("Testing /api/card/config (POST)")
    mock_set_card_config.return_value = {"status": "success", "data": {"message": "Configuration updated"}}
    response = client.post("/api/card/config", json={"card_type": "test_card", "config": {"param1": "new_value"}})
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "message" in response.json()["data"]
    logger.info("/api/card/config (POST) test passed")

@patch("routes.CardManager.factory_reset")
def test_api_card_factory_reset(mock_factory_reset, client):
    logger.info("Testing /api/card/factory_reset")
    mock_factory_reset.return_value = {"status": "success", "data": {"message": "Card reset"}}
    response = client.post("/api/card/factory_reset", json={"card_type": "test_card"})
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "message" in response.json()["data"]
    logger.info("/api/card/factory_reset test passed")
    
@patch("routes.DataConverter.convert")
def test_api_utils_convert_success(mock_convert, client):
    logger.info("Testing /api/utils/convert success case")
    mock_convert.return_value = {"status": "success", "data": {"result": "test"}}
    response = client.post("/api/utils/convert", json={"input": "74657374", "type": "hex-to-ascii"})
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "result" in response.json()["data"]
    logger.info("/api/utils/convert success test passed")

@patch("routes.Cryptography.perform_crypto")
def test_api_utils_crypto_success(mock_perform_crypto, client):
    logger.info("Testing /api/utils/crypto success case")
    mock_perform_crypto.return_value = {"status": "success", "data": {"result": "encrypted"}}
    response = client.post("/api/utils/crypto", json={"type": "aes-encrypt", "key": "00", "iv": "00", "data": "00"})
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "result" in response.json()["data"]
    logger.info("/api/utils/crypto success test passed")

def test_api_toggle_simulation(client):
    logger.info("Testing /api/toggle_simulation")
    response = client.post("/api/toggle_simulation", json={"enabled": True})
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["simulation_mode"] is True  # Fixed assertion
    logger.info("/api/toggle_simulation test passed")
    
@patch("routes.SmartcardManager.mifare_auth")
def test_api_mifare_auth(mock_mifare_auth, client):
    logger.info("Testing /api/mifare/auth")
    mock_mifare_auth.return_value = {"status": "success", "data": {"message": "Authentication successful"}}
    response = client.post("/api/mifare/auth", json={"sector": 1, "key_type": "A", "key": "FFFFFFFFFFFF"})
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "message" in response.json()["data"]
    logger.info("/api/mifare/auth test passed")

@patch("routes.SmartcardManager.desfire_list_apps")
def test_api_desfire_list_apps(mock_desfire_list_apps, client):
    logger.info("Testing /api/mifare/desfire/list_apps")
    mock_desfire_list_apps.return_value = {"status": "success", "data": {"apps": ["App1", "App2"]}}
    response = client.get("/api/mifare/desfire/list_apps")
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "apps" in response.json()["data"]
    logger.info("/api/mifare/desfire/list_apps test passed")
    
@patch("routes.SmartcardManager.transmit_apdu")
def test_api_smartcard_transmit_invalid_json(client):
    logger.info("Testing /api/smartcard/transmit with invalid JSON")
    response = client.post("/api/smartcard/transmit", json={"reader": 0})  # Missing 'apdu'
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json()}")
    assert response.status_code == 400  # @validate_json raises 400 for missing fields
    assert "Missing fields" in response.json()["detail"]
    logger.info("/api/smartcard/transmit invalid JSON test passed")