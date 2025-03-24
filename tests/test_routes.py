import json
from socket import IP_BIND_ADDRESS_NO_PORT
import pytest
import logging
from app import app
from unittest.mock import patch
from smartcard.Exceptions import CardConnectionException, NoCardException
from fastapi import HTTPException


# Configure logging for detailed output
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(module)s - %(funcname)s - %(message)s')

logger = logging.getLogger(__name__)

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        logger.info("Creating test client")
        yield client
        logger.info("Test client destroyed")

# Device Manager Tests
@patch('poc.device_manager.DeviceManager.list_smartcard_readers')
def test_api_smartcard_readers(mock_list_smartcard_readers, client):
    logger.info("Testing /api/smartcard/readers")
    mock_list_smartcard_readers.return_value = {'status': 'success', 'readers': [{'name': 'Reader 1', 'type': 'smartcard'}, {'name': 'NFC Reader', 'type': 'nfc'}]}
    response = client.get('/api/smartcard/readers')
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert len(response.json['data']['readers']) == 2
    logger.info("/api/smartcard/readers test passed")

# Smartcard Manager Tests
@patch('poc.smartcard_manager.SmartcardManager.get_atr')
def test_api_smartcard_atr_success(mock_get_atr, client):
    logger.info("Testing /api/smartcard/atr success case")
    mock_get_atr.return_value = {'status': 'success', 'atr': '3B6E00000073C84000000000', 'atr_ascii': '...', 'atr_analysis': {}, 'reader': 'Test Reader'}
    response = client.get('/api/smartcard/atr?reader=0')
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'atr' in response.json['data']
    logger.info("/api/smartcard/atr success test passed")

@patch('poc.smartcard_manager.SmartcardManager.get_atr')
def test_api_smartcard_atr_invalid_reader(mock_get_atr, client):
    logger.info("Testing /api/smartcard/atr with invalid reader")
    mock_get_atr.return_value = {'status': 'error', 'message': 'Invalid reader index'}
    response = client.get('/api/smartcard/atr?reader=invalid')
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'error'
    logger.info("/api/smartcard/atr invalid reader test passed")

@patch('poc.smartcard_manager.SmartcardManager.get_atr')
def test_api_smartcard_atr_no_card(mock_get_atr, client):
    logger.info("Testing /api/smartcard/atr with no card present")
    mock_get_atr.return_value = {'status': 'error', 'message': 'No card present'}
    response = client.get('/api/smartcard/atr?reader=0')
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'error'
    assert response.json['data']['message'] == 'No card present'
    logger.info("/api/smartcard/atr no card test passed")

@patch('poc.smartcard_manager.SmartcardManager.transmit_apdu')
def test_api_smartcard_transmit_success(mock_transmit_apdu, client):
    logger.info("Testing /api/smartcard/transmit success case")
    mock_transmit_apdu.return_value = {'status': 'success', 'response': '9000', 'sw': '9000', 'sw_meaning': 'Success', 'reader': 'Test Reader'}
    response = client.post('/api/smartcard/transmit', json={'reader': 0, 'apdu': '00 A4 04 00 0E'})
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'response' in response.json['data']
    logger.info("/api/smartcard/transmit success test passed")

@patch('poc.smartcard_manager.SmartcardManager.transmit_apdu')
def test_api_smartcard_transmit_invalid_apdu(mock_transmit_apdu, client):
    logger.info("Testing /api/smartcard/transmit with invalid APDU")
    mock_transmit_apdu.return_value = {'status': 'error', 'message': 'Invalid APDU format'}
    response = client.post('/api/smartcard/transmit', json={'reader': 0, 'apdu': 'invalid'})
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'error'
    assert 'message' in response.json['data']
    logger.info("/api/smartcard/transmit invalid APDU test passed")

@patch('poc.smartcard_manager.SmartcardManager.card_status')
def test_api_detect_smartcard_success(mock_card_status, client):
    logger.info("Testing /api/smartcard/detect success case")
    mock_card_status.return_value = {'status': 'success', 'present': True, 'reader': 'Test Reader'}
    response = client.get('/api/smartcard/detect')
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert response.json['data']['present']
    logger.info("/api/smartcard/detect success test passed")

# Card Manager Tests
@patch('poc.card_manager.CardManager.detect_card')
def test_api_detect_card_success(mock_detect_card, client):
    logger.info("Testing /api/detect_card success case")
    mock_detect_card.return_value = {'status': 'success', 'active_reader': 0}
    response = client.get('/api/detect_card')
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'data' in response.json
    logger.info("/api/detect_card success test passed")

# NFC Manager Tests
@patch('poc.nfc_manager.NFCManager.read_tag')
def test_api_nfc_read_success(mock_nfc_read, client):
    logger.info("Testing /api/nfc/read success case")
    mock_nfc_read.return_value = {'status': 'success', 'tag_data': {'type': 'Type A', 'id': '1234'}}
    response = client.get('/api/nfc/read')
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'data' in response.json
    logger.info("/api/nfc/read success test passed")

@patch('poc.nfc_manager.NFCManager.write_text')
def test_api_nfc_write_text_success(mock_nfc_write_text, client):
    logger.info("Testing /api/nfc/write_text success case")
    mock_nfc_write_text.return_value = {'status': 'success', 'message': 'Text written'}
    response = client.post('/api/nfc/write_text', json={'text': 'test'})
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'data' in response.json
    logger.info("/api/nfc/write_text success test passed")

# Utility Tests
@patch('poc.utils.DataConverter.convert')
def test_api_utils_convert_success(mock_convert, client):
    logger.info("Testing /api/utils/convert success case")
    mock_convert.return_value = {'status': 'success', 'result': 'test'}
    response = client.post('/api/utils/convert', json={'input': '74657374', 'type': 'hex-to-ascii'})
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'data' in response.json
    logger.info("/api/utils/convert success test passed")

@patch('poc.utils.Cryptography.perform_crypto')
def test_api_utils_crypto_success(mock_perform_crypto, client):
    logger.info("Testing /api/utils/crypto success case")
    mock_perform_crypto.return_value = {'status': 'success', 'result': 'encrypted'}
    response = client.post('/api/utils/crypto', json={'type': 'aes-encrypt', 'key': '00', 'iv': '00', 'data': '00'})
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'data' in response.json
    logger.info("/api/utils/crypto success test passed")

# Test for /api/health
def test_api_health_check(client):
    logger.info("Testing /api/health")
    response = client.get('/api/health')
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'ok'
    assert 'version' in response.json
    logger.info("/api/health test passed")

# Test for /api/card/config (GET)
@patch('poc.card_manager.CardManager.get_card_config')
def test_api_get_card_config(mock_get_card_config, client):
    logger.info("Testing /api/card/config (GET)")
    mock_get_card_config.return_value = {'config': {'param1': 'value1'}}
    response = client.get('/api/card/config?type=test_card')
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'config' in response.json['data']
    logger.info("/api/card/config (GET) test passed")

# Test for /api/card/config (POST)
@patch('poc.card_manager.CardManager.set_card_config')
def test_api_set_card_config(mock_set_card_config, client):
    logger.info("Testing /api/card/config (POST)")
    mock_set_card_config.return_value = {'message': 'Configuration updated'}
    response = client.post('/api/card/config', json={'card_type': 'test_card', 'config': {'param1': 'new_value'}})
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'message' in response.json['data']
    logger.info("/api/card/config (POST) test passed")

# Test for /api/card/factory_reset
@patch('poc.card_manager.CardManager.factory_reset')
def test_api_card_factory_reset(mock_factory_reset, client):
    logger.info("Testing /api/card/factory_reset")
    mock_factory_reset.return_value = {'message': 'Card reset'}
    response = client.post('/api/card/factory_reset', json={'card_type': 'test_card'})
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'message' in response.json['data']
    logger.info("/api/card/factory_reset test passed")

# Test for /api/batch
@patch('poc.card_manager.CardManager.detect_card')
def test_api_batch_operations(mock_detect_card, client):
    logger.info("Testing /api/batch")
    mock_detect_card.return_value = {'status': 'success', 'active_reader': 0}
    operations = [{'endpoint': '/api/detect_card', 'method': 'GET'}]
    response = client.post('/api/batch', json={'operations': operations})
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert isinstance(response.json['data'], list)
    logger.info("/api/batch test passed")

# Test for /api/scripts/run
@patch('poc.smartcard_manager.SmartcardManager.run_script')
def test_api_scripts_run(mock_run_script, client):
    logger.info("Testing /api/scripts/run")
    mock_run_script.return_value = {'status': 'success', 'results': ['result1', 'result2']}
    commands = ['command1', 'command2']
    response = client.post('/api/scripts/run', json={'reader': 0, 'commands': commands})
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert isinstance(response.json['data']['results'], list)
    logger.info("/api/scripts/run test passed")

# Test for /api/toggle_simulation
def test_api_toggle_simulation(client):
    logger.info("Testing /api/toggle_simulation")
    response = client.post('/api/toggle_simulation', json={'enabled': True})
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert response.json['data']['simulation_mode'] is True
    logger.info("/api/toggle_simulation test passed")

# Test for /api/smartcard/test_reader
@patch('poc.smartcard_manager.SmartcardManager.test_reader_connection')
def test_api_test_reader(mock_test_reader_connection, client):
    logger.info("Testing /api/smartcard/test_reader")
    mock_test_reader_connection.return_value = {'status': 'success', 'message': 'Reader functional'}
    response = client.get('/api/smartcard/test_reader?reader=0')
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'message' in response.json['data']
    logger.info("/api/smartcard/test_reader test passed")

# Test for /api/log
def test_api_log_from_frontend(client):
    logger.info("Testing /api/log from frontend")
    log_data = {'level': 'info', 'message': 'Frontend log message'}
    response = client.post('/api/log', json=log_data)
    logger.debug(f"Response status code: {response.status_code}")
    assert response.status_code == 200  # Assuming the route returns a 200 OK
    logger.info("/api/log from frontend test passed")

# Mocking specific functions to simulate card/reader behavior
@patch('poc.smartcard_manager.SmartcardManager.card_status')
def test_api_card_status_old(mock_card_status, client):
    logger.info("Testing /api/smartcard/card_status (old)")
    mock_card_status.return_value = {'status': 'success', 'present': True, 'reader': 'Test Reader'}
    response = client.get('/api/smartcard/card_status')
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert response.json['data']['present']
    logger.info("/api/smartcard/card_status (old) test passed")

@patch('poc.device_manager.DeviceManager.list_smartcard_readers')
@patch('poc.device_manager.DeviceManager.discover_nfc_device')
def test_api_list_readers(mock_list_smartcard_readers, mock_discover_nfc_device, client):
    logger.info("Testing /api/readers")
    mock_list_smartcard_readers.return_value = {'status': 'success', 'readers': [{'name': 'Reader 1', 'type': 'smartcard'}]}
    mock_discover_nfc_device.return_value = {'status': 'success', 'device': 'NFC Device', 'type': 'nfc'}
    response = client.get('/api/readers')
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert len(response.json['data']['readers']) == 2
    assert response.json['data']['readers'][0]['name'] == 'Reader 1'
    assert response.json['data']['readers'][1]['name'] == 'NFC Device'
    logger.info("/api/readers test passed")

@patch('poc.device_manager.DeviceManager.select_reader')
def test_api_select_reader(mock_select_reader, client):
    logger.info("Testing /api/select_reader")
    mock_select_reader.return_value = {'status': 'success', 'message': 'Reader selected'}
    response = client.post('/api/select_reader', json={'reader_name': 'Reader 1'})
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'message' in response.json['data']
    logger.info("/api/select_reader test passed")

@patch('poc.card_manager.CardManager.detect_card')
def test_api_card_event(mock_detect_card, client):
    logger.info("Testing /api/card_event")
    mock_detect_card.return_value = {'status': 'success', 'active_reader': 0}
    response = client.post('/api/card_event')
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'data' in response.json
    logger.info("/api/card_event test passed")

# Mocking MIFARE Classic operations
@patch('poc.smartcard_manager.SmartcardManager.mifare_auth')
def test_api_mifare_auth(mock_mifare_auth, client):
    logger.info("Testing /api/mifare/auth")
    mock_mifare_auth.return_value = {'status': 'success', 'message': 'Authentication successful'}
    response = client.post('/api/mifare/auth', json={'sector': 1, 'key_type': 'A', 'key': 'FFFFFFFFFFFF'})
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'message' in response.json['data']
    logger.info("/api/mifare/auth test passed")

@patch('poc.smartcard_manager.SmartcardManager.mifare_read_block')
def test_api_mifare_read_block(mock_mifare_read_block, client):
    logger.info("Testing /api/mifare/read_block")
    mock_mifare_read_block.return_value = {'status': 'success', 'data': 'Block data'}
    response = client.get('/api/mifare/read_block?block=1')
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'data' in response.json['data']
    logger.info("/api/mifare/read_block test passed")

@patch('poc.smartcard_manager.SmartcardManager.mifare_write_block')
def test_api_mifare_write_block(mock_mifare_write_block, client):
    logger.info("Testing /api/mifare/write_block")
    mock_mifare_write_block.return_value = {'status': 'success', 'message': 'Block written'}
    response = client.post('/api/mifare/write_block', json={'block': 1, 'data': 'New block data'})
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'message' in response.json['data']
    logger.info("/api/mifare/write_block test passed")

# Mocking DESFire operations
@patch('poc.smartcard_manager.SmartcardManager.desfire_list_apps')
def test_api_desfire_list_apps(mock_desfire_list_apps, client):
    logger.info("Testing /api/mifare/desfire/list_apps")
    mock_desfire_list_apps.return_value = {'status': 'success', 'apps': ['App1', 'App2']}
    response = client.get('/api/mifare/desfire/list_apps')
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'apps' in response.json['data']
    logger.info("/api/mifare/desfire/list_apps test passed")

@patch('poc.smartcard_manager.SmartcardManager.desfire_list_files')
def test_api_desfire_list_files(mock_desfire_list_files, client):
    logger.info("Testing /api/mifare/desfire/list_files")
    mock_desfire_list_files.return_value = {'status': 'success', 'files': ['File1', 'File2']}
    response = client.get('/api/mifare/desfire/list_files?app_id=000000')
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'files' in response.json['data']
    logger.info("/api/mifare/desfire/list_files test passed")

@patch('poc.smartcard_manager.SmartcardManager.desfire_auth')
def test_api_desfire_auth(mock_desfire_auth, client):
    logger.info("Testing /api/mifare/desfire/auth")
    mock_desfire_auth.return_value = {'status': 'success', 'message': 'Authentication successful'}
    response = client.post('/api/mifare/desfire/auth', json={'app_id': '000000', 'key_no': 0, 'key': '0000000000000000'})
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'message' in response.json['data']
    logger.info("/api/mifare/desfire/auth test passed")

@patch('poc.smartcard_manager.SmartcardManager.desfire_read_file')
def test_api_desfire_read_file(mock_desfire_read_file, client):
    logger.info("Testing /api/mifare/desfire/read_file")
    mock_desfire_read_file.return_value = {'status': 'success', 'data': 'File data'}
    response = client.get('/api/mifare/desfire/read_file?app_id=000000&file_id=0')
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'data' in response.json['data']
    logger.info("/api/mifare/desfire/read_file test passed")

@patch('poc.smartcard_manager.SmartcardManager.desfire_write_file')
def test_api_desfire_write_file(mock_desfire_write_file, client):
    logger.info("Testing /api/mifare/desfire/write_file")
    mock_desfire_write_file.return_value = {'status': 'success', 'message': 'File written'}
    response = client.post('/api/mifare/desfire/write_file', json={'app_id': '000000', 'file_id': 0, 'data': 'New file data'})
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'message' in response.json['data']
    logger.info("/api/mifare/desfire/write_file test passed")

# Mocking JavaCard operations
@patch('poc.smartcard_manager.SmartcardManager.select_aid')
def test_api_javacard_select(mock_javacard_select, client):
    logger.info("Testing /api/javacard/select")
    mock_javacard_select.return_value = {'status': 'success', 'message': 'Applet selected'}
    response = client.post('/api/javacard/select', json={'aid': 'A000000003'})
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'message' in response.json['data']
    logger.info("/api/javacard/select test passed")

@patch('poc.smartcard_manager.SmartcardManager.list_applets')
def test_api_javacard_list(mock_javacard_list, client):
    logger.info("Testing /api/javacard/list")
    mock_javacard_list.return_value = {'status': 'success', 'applets': ['Applet1', 'Applet2']}
    response = client.get('/api/javacard/list')
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response JSON: {response.json}")
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'applets' in response.json['data']
    logger.info("/api/javacard/list test passed")

# Mocking EMV operations
@patch('poc.smartcard_manager.SmartcardManager.select_aid')

# Smartcard Manager Tests
@patch('poc.smartcard_manager.SmartcardManager.get_atr')
def test_api_smartcard_atr_success(mock_get_atr, client):
    mock_get_atr.return_value = {'status': 'success', 'atr': '3B6E00000073C84000000000', 'atr_ascii': '...', 'atr_analysis': {}, 'reader': 'Test Reader'}
    response = client.get('/api/smartcard/atr?reader=0')
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'atr' in response.json['data']

@patch('poc.smartcard_manager.SmartcardManager.get_atr')
def test_api_smartcard_atr_invalid_reader(mock_get_atr, client):
    mock_get_atr.return_value = {'status': 'error', 'message': 'Invalid reader index'}
    response = client.get('/api/smartcard/atr?reader=invalid')
    assert response.status_code == 200
    assert response.json['status'] == 'error'

@patch('poc.smartcard_manager.SmartcardManager.get_atr')
def test_api_smartcard_atr_no_card(mock_get_atr, client):
    mock_get_atr.return_value = {'status': 'error', 'message': 'No card present'}
    response = client.get('/api/smartcard/atr?reader=0')
    assert response.status_code == 200
    assert response.json['status'] == 'error'
    assert response.json['data']['message'] == 'No card present'

@patch('poc.smartcard_manager.SmartcardManager.transmit_apdu')
def test_api_smartcard_transmit_success(mock_transmit_apdu, client):
    mock_transmit_apdu.return_value = {'status': 'success', 'response': '9000', 'sw': '9000', 'sw_meaning': 'Success', 'reader': 'Test Reader'}
    response = client.post('/api/smartcard/transmit', json={'reader': 0, 'apdu': '00 A4 04 00 0E'})
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'response' in response.json['data']

@patch('poc.smartcard_manager.SmartcardManager.transmit_apdu')
def test_api_smartcard_transmit_invalid_apdu(mock_transmit_apdu, client):
    mock_transmit_apdu.return_value = {'status': 'error', 'message': 'Invalid APDU format'}
    response = client.post('/api/smartcard/transmit', json={'reader': 0, 'apdu': 'invalid'})
    assert response.status_code == 200
    assert response.json['status'] == 'error'
    assert 'message' in response.json['data']

@patch('poc.smartcard_manager.SmartcardManager.card_status')
def test_api_detect_smartcard_success(mock_card_status, client):
    mock_card_status.return_value = {'status': 'success', 'present': True, 'reader': 'Test Reader'}
    response = client.get('/api/smartcard/detect')
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert response.json['data']['present']

# Card Manager Tests
@patch('poc.card_manager.CardManager.detect_card')
def test_api_detect_card_success(mock_detect_card, client):
    mock_detect_card.return_value = {'status': 'success', 'active_reader': 0}
    response = client.get('/api/detect_card')
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'data' in response.json

# NFC Manager Tests
@patch('poc.nfc_manager.NFCManager.read_tag')
def test_api_nfc_read_success(mock_nfc_read, client):
    mock_nfc_read.return_value = {'status': 'success', 'tag_data': {'type': 'Type A', 'id': '1234'}}
    response = client.get('/api/nfc/read')
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'data' in response.json

@patch('poc.nfc_manager.NFCManager.write_text')
def test_api_nfc_write_text_success(mock_nfc_write_text, client):
    mock_nfc_write_text.return_value = {'status': 'success', 'message': 'Text written'}
    response = client.post('/api/nfc/write_text', json={'text': 'test'})
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'data' in response.json

# Utility Tests
@patch('poc.utils.DataConverter.convert')
def test_api_utils_convert_success(mock_convert, client):
    mock_convert.return_value = {'status': 'success', 'result': 'test'}
    response = client.post('/api/utils/convert', json={'input': '74657374', 'type': 'hex-to-ascii'})
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'data' in response.json

@patch('poc.utils.Cryptography.perform_crypto')
def test_api_utils_crypto_success(mock_perform_crypto, client):
    mock_perform_crypto.return_value = {'status': 'success', 'result': 'encrypted'}
    response = client.post('/api/utils/crypto', json={'type': 'aes-encrypt', 'key': '00', 'iv': '00', 'data': '00'})
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'data' in response.json

# Test for /api/health
def test_api_health_check(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json['status'] == 'ok'
    assert 'version' in response.json

# Test for /api/card/config (GET)
@patch('poc.card_manager.CardManager.get_card_config')
def test_api_get_card_config(mock_get_card_config, client):
    mock_get_card_config.return_value = {'config': {'param1': 'value1'}}
    response = client.get('/api/card/config?type=test_card')
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'config' in response.json['data']

# Test for /api/card/config (POST)
@patch('poc.card_manager.CardManager.set_card_config')
def test_api_set_card_config(mock_set_card_config, client):
    mock_set_card_config.return_value = {'message': 'Configuration updated'}
    response = client.post('/api/card/config', json={'card_type': 'test_card', 'config': {'param1': 'new_value'}})
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'message' in response.json['data']

# Test for /api/card/factory_reset
@patch('poc.card_manager.CardManager.factory_reset')
def test_api_card_factory_reset(mock_factory_reset, client):
    mock_factory_reset.return_value = {'message': 'Card reset'}
    response = client.post('/api/card/factory_reset', json={'card_type': 'test_card'})
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'message' in response.json['data']

# Test for /api/batch
@patch('poc.card_manager.CardManager.detect_card')
def test_api_batch_operations(mock_detect_card, client):
    mock_detect_card.return_value = {'status': 'success', 'active_reader': 0}
    operations = [{'endpoint': '/api/detect_card', 'method': 'GET'}]
    response = client.post('/api/batch', json={'operations': operations})
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert isinstance(response.json['data'], list)

# Test for /api/scripts/run
@patch('poc.smartcard_manager.SmartcardManager.run_script')
def test_api_scripts_run(mock_run_script, client):
    mock_run_script.return_value = {'status': 'success', 'results': ['result1', 'result2']}
    commands = ['command1', 'command2']
    response = client.post('/api/scripts/run', json={'reader': 0, 'commands': commands})
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert isinstance(response.json['data']['results'], list)

# Test for /api/toggle_simulation
def test_api_toggle_simulation(client):
    response = client.post('/api/toggle_simulation', json={'enabled': True})
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert response.json['data']['simulation_mode'] is True

# Test for /api/smartcard/test_reader
@patch('poc.smartcard_manager.SmartcardManager.test_reader_connection')
def test_api_test_reader(mock_test_reader_connection, client):
    mock_test_reader_connection.return_value = {'status': 'success', 'message': 'Reader functional'}
    response = client.get('/api/smartcard/test_reader?reader=0')
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'message' in response.json['data']

# Test for /api/log
def test_api_log_from_frontend(client):
    log_data = {'level': 'info', 'message': 'Frontend log message'}
    response = client.post('/api/log', json=log_data)
    assert response.status_code == 200  # Assuming the route returns a 200 OK

# Mocking specific functions to simulate card/reader behavior
@patch('poc.smartcard_manager.SmartcardManager.card_status')
def test_api_card_status_old(mock_card_status, client):
    mock_card_status.return_value = {'status': 'success', 'present': True, 'reader': 'Test Reader'}
    response = client.get('/api/smartcard/card_status')
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert response.json['data']['present']

@patch('poc.device_manager.DeviceManager.list_smartcard_readers')
@patch('poc.device_manager.DeviceManager.discover_nfc_device')
def test_api_list_readers(mock_list_smartcard_readers, mock_discover_nfc_device, client):
    mock_list_smartcard_readers.return_value = {'status': 'success', 'readers': [{'name': 'Reader 1', 'type': 'smartcard'}]}
    mock_discover_nfc_device.return_value = {'status': 'success', 'device': 'NFC Device', 'type': 'nfc'}
    response = client.get('/api/readers')
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert len(response.json['data']['readers']) == 2
    assert response.json['data']['readers'][0]['name'] == 'Reader 1'
    assert response.json['data']['readers'][1]['name'] == 'NFC Device'

@patch('poc.device_manager.DeviceManager.select_reader')
def test_api_select_reader(mock_select_reader, client):
    mock_select_reader.return_value = {'status': 'success', 'message': 'Reader selected'}
    response = client.post('/api/select_reader', json={'reader_name': 'Reader 1'})
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'message' in response.json['data']

@patch('poc.card_manager.CardManager.detect_card')
def test_api_card_event(mock_detect_card, client):
    mock_detect_card.return_value = {'status': 'success', 'active_reader': 0}
    response = client.post('/api/card_event')
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'data' in response.json

# Mocking MIFARE Classic operations
@patch('poc.smartcard_manager.SmartcardManager.mifare_auth')
def test_api_mifare_auth(mock_mifare_auth, client):
    mock_mifare_auth.return_value = {'status': 'success', 'message': 'Authentication successful'}
    response = client.post('/api/mifare/auth', json={'sector': 1, 'key_type': 'A', 'key': 'FFFFFFFFFFFF'})
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'message' in response.json['data']

@patch('poc.smartcard_manager.SmartcardManager.mifare_read_block')
def test_api_mifare_read_block(mock_mifare_read_block, client):
    mock_mifare_read_block.return_value = {'status': 'success', 'data': 'Block data'}
    response = client.get('/api/mifare/read_block?block=1')
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'data' in response.json['data']

@patch('poc.smartcard_manager.SmartcardManager.mifare_write_block')
def test_api_mifare_write_block(mock_mifare_write_block, client):
    mock_mifare_write_block.return_value = {'status': 'success', 'message': 'Block written'}
    response = client.post('/api/mifare/write_block', json={'block': 1, 'data': 'New block data'})
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'message' in response.json['data']

# Mocking DESFire operations
@patch('poc.smartcard_manager.SmartcardManager.desfire_list_apps')
def test_api_desfire_list_apps(mock_desfire_list_apps, client):
    mock_desfire_list_apps.return_value = {'status': 'success', 'apps': ['App1', 'App2']}
    response = client.get('/api/mifare/desfire/list_apps')
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'apps' in response.json['data']

@patch('poc.smartcard_manager.SmartcardManager.desfire_list_files')
def test_api_desfire_list_files(mock_desfire_list_files, client):
    mock_desfire_list_files.return_value = {'status': 'success', 'files': ['File1', 'File2']}
    response = client.get('/api/mifare/desfire/list_files?app_id=000000')
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'files' in response.json['data']

@patch('poc.smartcard_manager.SmartcardManager.desfire_auth')
def test_api_desfire_auth(mock_desfire_auth, client):
    mock_desfire_auth.return_value = {'status': 'success', 'message': 'Authentication successful'}
    response = client.post('/api/mifare/desfire/auth', json={'app_id': '000000', 'key_no': 0, 'key': '0000000000000000'})
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'message' in response.json['data']

@patch('poc.smartcard_manager.SmartcardManager.desfire_read_file')
def test_api_desfire_read_file(mock_desfire_read_file, client):
    mock_desfire_read_file.return_value = {'status': 'success', 'data': 'File data'}
    response = client.get('/api/mifare/desfire/read_file?app_id=000000&file_id=0')
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'data' in response.json['data']

@patch('poc.smartcard_manager.SmartcardManager.desfire_write_file')
def test_api_desfire_write_file(mock_desfire_write_file, client):
    mock_desfire_write_file.return_value = {'status': 'success', 'message': 'File written'}
    response = client.post('/api/mifare/desfire/write_file', json={'app_id': '000000', 'file_id': 0, 'data': 'New file data'})
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'message' in response.json['data']

# Mocking JavaCard operations
@patch('poc.smartcard_manager.SmartcardManager.select_aid')
def test_api_javacard_select(mock_javacard_select, client):
    mock_javacard_select.return_value = {'status': 'success', 'message': 'Applet selected'}
    response = client.post('/api/javacard/select', json={'aid': 'A000000003'})
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'message' in response.json['data']

@patch('poc.smartcard_manager.SmartcardManager.list_applets')
def test_api_javacard_list(mock_javacard_list, client):
    mock_javacard_list.return_value = {'status': 'success', 'applets': ['Applet1', 'Applet2']}
    response = client.get('/api/javacard/list')
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'applets' in response.json['data']

# Mocking EMV operations
@patch('poc.smartcard_manager.SmartcardManager.select_aid')
def test_api_emv_select(mock_emv_select, client):
    mock_emv_select.return_value = {'status': 'success', 'message': 'EMV application selected'}
    response = client.post('/api/emv/select', json={'aid': 'A000000004'})
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'message' in response.json['data']

@patch('poc.smartcard_manager.SmartcardManager.process_emv')
def test_api_emv_process(mock_emv_process, client):
    mock_emv_process.return_value = {'status': 'success', 'data': 'EMV processing result'}
    response = client.post('/api/emv/process', json={'anonymize': True})
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'data' in response.json['data']

# Mocking additional NFC operations
@patch('poc.nfc_manager.NFCManager.write_vcard')
def test_api_nfc_write_vcard(mock_write_vcard, client):
    mock_write_vcard.return_value = {'status': 'success', 'message': 'vCard written'}
    response = client.post('/api/nfc/write_vcard', json={'name': 'Test', 'org': 'Test Org', 'email': 'test@example.com', 'phone': '123-456-7890'})
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'message' in response.json['data']

@patch('poc.nfc_manager.NFCManager.write_raw')
def test_api_nfc_write_raw(mock_write_raw, client):
    mock_write_raw.return_value = {'status': 'success', 'message': 'Raw record written'}
    response = client.post('/api/nfc/write_raw', json={'record_type': 'Text', 'payload': '74657374'})
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'message' in response.json['data']

@patch('poc.nfc_manager.NFCManager.emulate_tag')
def test_api_nfc_emulate(mock_emulate_tag, client):
    mock_emulate_tag.return_value = {'status': 'success', 'message': 'Tag emulation started'}
    response = client.post('/api/nfc/emulate')
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'message' in response.json['data']

@patch('poc.nfc_manager.NFCManager.enter_p2p_mode')
def test_api_nfc_p2p(mock_enter_p2p_mode, client):
    mock_enter_p2p_mode.return_value = {'status': 'success', 'message': 'P2P mode started'}
    response = client.post('/api/nfc/p2p')
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'message' in response.json['data']

@patch('poc.nfc_manager.NFCManager.discover')
def test_api_nfc_discover(mock_discover, client):
    mock_discover.return_value = {'status': 'success', 'devices': ['Device1', 'Device2']}
    response = client.get('/api/nfc/discover')
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'devices' in response.json['data']

@patch('poc.nfc_manager.NFCManager.write_text')
def test_api_nfc_write_text(mock_write_text, client):
    mock_write_text.return_value = {'status': 'success', 'message': 'Text written'}
    response = client.post('/api/nfc/write_text', json={'text': 'Test text'})
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'message' in response.json['data']

@patch('poc.nfc_manager.NFCManager.write_uri')
def test_api_nfc_write_uri(mock_write_uri, client):
    mock_write_uri.return_value = {'status': 'success', 'message': 'URI written'}
    response = client.post('/api/nfc/write_uri', json={'uri': 'http://example.com'})
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'message' in response.json['data']

# Error handling tests
@patch('poc.smartcard_manager.SmartcardManager.get_atr')
def test_api_smartcard_atr_exception(mock_get_atr, client):
    mock_get_atr.side_effect = Exception('Test exception')
    response = client.get('/api/smartcard/atr?reader=0')
    assert response.status_code == 500  # Or appropriate error code
    assert response.json['status'] == 'error'
    assert 'message' in response.json['data']

@patch('poc.card_manager.CardManager.detect_card')
def test_api_detect_card_exception(mock_detect_card, client):
    mock_detect_card.side_effect = Exception('Test exception')
    response = client.get('/api/detect_card')
    assert response.status_code == 500  # Or appropriate error code
    assert response.json['status'] == 'error'
    assert 'message' in response.json['data']

@patch('poc.nfc_manager.NFCManager.read_tag')
def test_api_nfc_read_exception(mock_nfc_read, client):
    mock_nfc_read.side_effect = Exception('Test exception')
    response = client.get('/api/nfc/read')
    assert response.status_code == 500  # Or appropriate error code
    assert response.json['status'] == 'error'
    assert 'message' in response.json['data']

@patch('poc.utils.DataConverter.convert')
def test_api_utils_convert_exception(mock_convert, client):
    mock_convert.side_effect = Exception('Test exception')
    response = client.post('/api/utils/convert', json={'input': '74657374', 'type': 'hex-to-ascii'})
    assert response.status_code == 500  # Or appropriate error code
    assert response.json['status'] == 'error'
    assert 'message' in response.json['data']

@patch('poc.utils.Cryptography.perform_crypto')
def test_api_utils_crypto_exception(mock_perform_crypto, client):
    mock_perform_crypto.side_effect = Exception('Test exception')
    response = client.post('/api/utils/crypto', json={'type': 'aes-encrypt', 'key': '00', 'iv': '00', 'data': '00'})
    assert response.status_code == 500  # Or appropriate error code
    assert response.json['status'] == 'error'
    assert 'message' in response.json['data']

# Test for handling CardConnectionException in SmartcardManager
@patch('poc.smartcard_manager.SmartcardManager.get_atr')
def test_api_smartcard_atr_card_connection_exception(mock_get_atr, client):
    mock_get_atr.side_effect = CardConnectionException('Failed to connect')
    response = client.get('/api/smartcard/atr?reader=0')
    assert response.status_code == 200  # Or appropriate error code
    assert response.json['status'] == 'error'
    assert 'message' in response.json['data']
    assert 'Failed to connect' in response.json['data']['message']

# Test for handling NoCardException in SmartcardManager
@patch('poc.smartcard_manager.SmartcardManager.get_atr')
def test_api_smartcard_atr_no_card_exception(mock_get_atr, client):
    mock_get_atr.side_effect = NoCardException('No card present')
    response = client.get('/api/smartcard/atr?reader=0')
    assert response.status_code == 200  # Or appropriate error code
    assert response.json['status'] == 'error'
    assert 'message' in response.json['data']
    assert 'No card present' in response.json['data']['message']

@patch('poc.device_manager.DeviceManager.reader_types', {'Reader 1': 'smartcard'})
def test_api_card_event_with_reader(client):
    response = client.post('/api/card_event', json={'reader': 'Reader 1'})
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'message' in response.json['data']
    assert response.json['data']['message'] == 'Card detected on Reader 1'
    
@patch('poc.smartcard_manager.SmartcardManager.card_status')
def test_api_card_status(mock_card_status, client):
    mock_card_status.return_value = {'status': 'success', 'present': True, 'reader': 'Test Reader'}
    response = client.get('/api/smartcard/card_status?reader=0')
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert response.json['data']['present']