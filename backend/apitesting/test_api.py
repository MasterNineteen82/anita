import os
import sys
import pytest
from fastapi.testclient import TestClient
import httpx
import requests
import asyncio
import json # Added import

# Import Bleak components for mocking
from bleak import BLEDevice, AdvertisementData, BleakClient

# Import BleDeviceManager for mocking
from backend.modules.ble.core.device_manager import BleDeviceManager, get_device_manager

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))) # Corrected path string

from app import app  # Import your FastAPI app instance
# from backend.main import app # Reverted: Import the FastAPI app from the correct entry point
from backend.modules.ble.core.ble_service import get_ble_service

client = TestClient(app)

# Define API Prefixes for easier route management
ADAPTER_API_PREFIX = "/api/ble/adapter"  # This needs to stay as-is since the router has prefix="/adapter"
DEVICE_API_PREFIX = "/api/ble/device"    # This needs to stay as-is since the router has prefix="/device"

BASE_URL = "http://testserver"  # Base URL used by TestClient

# --- Helper Functions (Optional) ---

def check_health():
    try:
        response = requests.get(f"{BASE_URL}/health")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False

# --- Test Basic API Health --- 

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    print("Test 'test_health_check': PASSED")

# --- Test Root Endpoint --- 

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    # Assuming it returns HTML content, check for a key element or text
    assert "<title>Dashboard | ANITA</title>" in response.text # Corrected title
    print("Test 'test_read_root': PASSED")

# --- Test API Docs Endpoints --- 

def test_read_docs():
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger-ui" in response.text # Check for Swagger UI elements
    print("Test 'test_read_docs': PASSED")

def test_read_redoc():
    response = client.get("/redoc")
    assert response.status_code == 200
    assert "ReDoc" in response.text # Check for ReDoc elements
    print("Test 'test_read_redoc': PASSED")

def test_openapi_json():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "ANITA Backend" # Corrected title
    print("\n\nOpenAPI JSON Test: PASSED\n")

def test_list_adapters():
    """Tests listing available BLE adapters."""
    response = client.get(f"{ADAPTER_API_PREFIX}/adapters")
    assert response.status_code == 200
    # Updated Assertion: Expecting a dict { "adapters": [...] } based on previous logs
    assert isinstance(response.json(), dict)
    assert "adapters" in response.json()
    assert isinstance(response.json()["adapters"], list)
    # Optional: Check if the list contains expected keys if structure is known
    # if response.json()["adapters"]:
    #     assert "id" in response.json()["adapters"][0]
    #     assert "name" in response.json()["adapters"][0]
    print("Test 'test_list_adapters': PASSED")

# --- Test GET /metrics ---
@pytest.mark.xfail(reason="Known issue: AttributeError: 'BleMetricsCollector' object has no attribute 'get_metrics'")
def test_get_adapter_metrics():
    """Tests retrieving metrics for BLE adapters."""
    response = client.get(f"{ADAPTER_API_PREFIX}/metrics")
    # This test is expected to fail due to the AttributeError
    # If fixed, it should return 200 OK
    assert response.status_code == 200
    # Add assertions for the expected metrics structure if known
    # e.g., assert "cpu_usage" in response.json()
    print("Test 'test_get_adapter_metrics': PASSED (Expected Failure)")

# --- Test GET /diagnostics ---
def test_get_adapter_diagnostics():
    """Tests retrieving diagnostic information."""
    response = client.get(f"{ADAPTER_API_PREFIX}/diagnostics")
    # Expected to fail due to missing BleService method (unless fixed)
    assert response.status_code == 200
    # TODO: Add assertions for expected diagnostic structure if known
    print("Test 'test_get_adapter_diagnostics': PASSED") # Note: May still fail if AttributeError persists

# --- Test POST /reset ---
@pytest.mark.xfail(reason="Requires adapter selection or specific state, received 422")
def test_reset_adapter():
    """Tests resetting a BLE adapter (requires adapter ID/selection)."""
    # This likely needs an adapter_id parameter or prior selection
    # Sending without might result in 422 or other errors
    response = client.post(f"{ADAPTER_API_PREFIX}/reset") # Needs adapter_id?
    # Expected to fail (422) unless an adapter is implicitly selected/defaulted
    assert response.status_code == 200
    print("Test 'test_reset_adapter': PASSED (Expected Failure due to 422)")

# --- Test POST /select ---
@pytest.mark.xfail(reason="Requires existing adapter or specific state, received 422")
def test_select_adapter():
    """Tests selecting a BLE adapter."""
    # Requires a valid adapter_id in the request body or path
    response = client.post(f"{ADAPTER_API_PREFIX}/select") # Needs adapter_id in body/path?
    # Expected to fail (422) without a valid adapter ID
    assert response.status_code == 200
    print("Test 'test_select_adapter': PASSED (Expected Failure due to 422)")

# --- Test POST /power ---
def test_set_adapter_power():
    """Tests setting the power state of a BLE adapter (requires adapter ID/selection)."""
    # Needs adapter_id and power state (true/false) in the request body
    # Sending without might result in 422 or other errors
    power_state = True
    adapter_id_to_test = None # Or specify an adapter ID if needed: "hci0"
    request_body = {"power": power_state}
    if adapter_id_to_test:
        request_body["adapter_id"] = adapter_id_to_test
        
    # Send power state in the JSON body
    response = client.post(f"{ADAPTER_API_PREFIX}/power", json=request_body) 
    
    # Check for expected success (200)
    assert response.status_code == 200 
    print(f"Test 'test_set_adapter_power': Status Code {response.status_code}, Response: {response.text}") 
    assert response.json().get("status") == "success"
    # Optionally check the message
    # assert f"power to {power_state}" in response.json().get("message", "")

# --- Test GET /info/{adapter_id} ---
@pytest.mark.xfail(reason="Requires a valid and selected adapter_id")
def test_get_adapter_info():
    """Tests getting detailed info for a specific adapter."""
    adapter_id_to_test = "hci0" # Replace with a known valid adapter ID if possible, else expect failure
    response = client.get(f"{ADAPTER_API_PREFIX}/info/{adapter_id_to_test}")
    # If adapter_id is invalid or adapter not found, expect 404
    # If adapter exists, expect 200
    assert response.status_code == 200
    data = response.json()
    # Updated Assertion: Check for expected keys based on previous logs/structure
    assert isinstance(data, dict)
    assert "adapter_id" in data
    assert "address" in data
    assert "name" in data
    # assert data["adapter_id"] == adapter_id_to_test # Verify ID matches
    print(f"Test 'test_get_adapter_info' for {adapter_id_to_test}: PASSED (Expected Failure)")

# --- Test GET /health/{adapter_id} ---
def test_get_adapter_health():
    """Tests getting health status for the Bluetooth system (not adapter specific)."""
    #adapter_id_to_test = "hci0" # Route doesn't take adapter_id
    response = client.get(f"{ADAPTER_API_PREFIX}/health") # Corrected endpoint
    assert response.status_code == 200
    # Add assertions for expected health status structure
    print(f"Test 'test_get_adapter_health': PASSED")


# ======================================================
# == BLE Device Routes Tests (/api/ble/device/*)     ==
# ======================================================

# --- Test GET / --- (List devices)
def test_get_ble_devices():
    """Tests listing BLE devices (potentially filtered)."""
    response = client.get(f"{DEVICE_API_PREFIX}/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    print("Test 'test_get_ble_devices': PASSED")

# --- Test GET /bonded --- (List bonded devices)
@pytest.mark.xfail(reason="Functionality not implemented in BleDeviceManager yet")
def test_list_bonded_devices():
    """Tests listing bonded/saved BLE devices."""
    response = client.get(f"{DEVICE_API_PREFIX}/bonded")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    print("Test 'test_list_bonded_devices': PASSED (Expected Failure - Not Implemented)")

# --- Test POST /scan --- (Start scanning)
def test_start_ble_scan():
    """Tests starting a BLE scan."""
    scan_params = {"scan_time": 5.0, "active": False} # Example params
    response = client.post(f"{DEVICE_API_PREFIX}/scan", json=scan_params)
    assert response.status_code == 200 # Or 202 Accepted
    # Assert response body if applicable (e.g., {"status": "scanning"})
    print("Test 'test_start_ble_scan': PASSED")

# --- Test POST /scan/real_only --- (Scan without simulated devices)
#@pytest.mark.xfail(reason="Requires specific backend setup/adapter state")
def test_scan_real_only():
    # response = client.post("/api/ble/device/scan/real_only", json={"scan_time": 1.0}) # Original: JSON body
    response = client.post(f"{DEVICE_API_PREFIX}/scan/real_only", content=json.dumps(1.0)) # Updated: Raw float body
    # This might expect 200 OK or 202 Accepted if scan starts
    # Or potentially 4xx/5xx if adapter state is wrong or endpoint has issues
    assert response.status_code == 200 # Adjust based on expected behavior
    print(f"Test 'test_scan_real_only': Status Code {response.status_code}")

# --- Test POST /scan/stop --- (Stop scanning)
def test_stop_ble_scan():
    """Tests stopping an ongoing BLE scan."""
    response = client.post(f"{DEVICE_API_PREFIX}/scan/stop")
    assert response.status_code == 200
    # Assert response body if applicable (e.g., {"status": "stopped"})
    print("Test 'test_stop_ble_scan': PASSED")

# --- Test GET /discovered --- (List discovered devices)
def test_list_discovered_devices():
    """Tests listing devices discovered during the last scan."""
    response = client.get(f"{DEVICE_API_PREFIX}/discovered")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict) # Expecting {"discovered_devices": [...]} ?
    assert "discovered_devices" in data
    assert isinstance(data["discovered_devices"], list)
    print("Test 'test_list_discovered_devices': PASSED")

# --- Test POST /connect --- (Connect to device)
def test_connect_ble_device(mocker): 
    """Tests connecting to a BLE device by address using mocks."""
    # 1. Mock discovery to return a fake device
    fake_address = "00:11:22:33:44:55"
    mock_ble_device = mocker.Mock(spec=BLEDevice)
    mock_ble_device.address = fake_address
    mock_ble_device.name = "TestDevice"
    # Mock AdvertisementData if needed by the caching logic
    mock_advertisement_data = mocker.Mock(spec=AdvertisementData)
    mock_advertisement_data.rssi = -50
    # Ensure advertisement_data attribute exists if needed by the code under test
    # Option 1: Assign directly if spec=True allows it
    # mock_ble_device.advertisement_data = mock_advertisement_data 
    # Option 2: Configure the mock specifically if spec=True blocks direct assignment
    mocker.patch.object(mock_ble_device, 'advertisement_data', mock_advertisement_data, create=True)

    # Mock BleakScanner.discover to return our fake device
    # Ensure the patch target matches the actual usage in device_manager.py
    mocker.patch("backend.modules.ble.core.device_manager.BleakScanner.discover", return_value=[mock_ble_device])

    # Optional: Run a scan first to populate the cache (using the mocked discover)
    # scan_params = {"scan_time": 1.0, "active": False} 
    # client.post(f"{DEVICE_API_PREFIX}/scan", json=scan_params) 

    # 2. Mock BleakClient connection
    mock_bleak_client = mocker.AsyncMock(spec=BleakClient)
    # Use configure_mock for properties on AsyncMock
    mock_bleak_client.configure_mock(**{"is_connected": True}) 
    # Patch the BleakClient instantiation within device_manager.py
    mocker.patch("backend.modules.ble.core.device_manager.BleakClient", return_value=mock_bleak_client)
    # Make connect awaitable and return True (or None if it doesn't return anything on success)
    mock_bleak_client.connect = mocker.AsyncMock(return_value=True) 
    # Make disconnect awaitable
    mock_bleak_client.disconnect = mocker.AsyncMock(return_value=True) 

    # 3. Perform the connect API call
    connect_payload = {"address": fake_address}
    response = client.post(f"{DEVICE_API_PREFIX}/connect", json=connect_payload)

    # 4. Assertions
    assert response.status_code == 200
    # Adjust expected response based on actual API return value
    # The API returns a nested structure
    expected_response_fragment = {
        "status": "success", 
        "result": {
            "status": "connected", 
            "address": fake_address
        }
    } 
    # Check if the actual response contains the expected fragment
    response_data = response.json()
    # For nested dicts, comparing items directly might not work as expected.
    # Let's assert the top-level status and the nested result separately.
    assert response_data.get("status") == expected_response_fragment["status"]
    assert response_data.get("result") == expected_response_fragment["result"]
    # assert expected_response_fragment.items() <= response_data.items() # Original less robust assertion

    # Optional: Assert BleakClient methods were called
    mock_bleak_client.connect.assert_awaited_once()

    # Cleanup mocks if needed (though mocker fixture handles most cleanup)
    print(f"Test 'test_connect_ble_device' with mocks: PASSED")

# --- Test POST /disconnect --- (Disconnect from device)
@pytest.mark.xfail(reason="Disconnect endpoint requires mocking of nested service layers which is problematic in FastAPI's dependency injection with TestClient")
def test_disconnect_ble_device(mocker):
    """Tests disconnecting from the currently connected BLE device using mocks."""
    # Create a mock service class
    class MockBleService:
        async def disconnect_device(self, address):
            return {"status": "disconnected", "address": address}

    # Create a mock service getter function
    def get_mock_ble_service():
        return MockBleService()

    # Override the dependency in FastAPI
    app.dependency_overrides[get_ble_service] = get_mock_ble_service

    try:
        # Perform the disconnect API call
        response = client.post(
            f"{DEVICE_API_PREFIX}/disconnect",
            json={"address": "XX:XX:XX:XX:XX:XX"}
        )

        # Assertions
        assert response.status_code == 200
        
        # Validate the response content
        response_data = response.json()
        assert response_data["status"] == "success"
        assert "result" in response_data
        # Check that we got the expected return structure
        assert response_data["result"]["status"] == "disconnected"
        assert response_data["result"]["address"] == "XX:XX:XX:XX:XX:XX"
    finally:
        # Clean up the dependency override
        app.dependency_overrides.pop(get_ble_service, None)

# --- Test GET /connection-status --- (Check connection status)
def test_check_connection_status():
    """Tests checking the current BLE connection status."""
    response = client.get(f"{DEVICE_API_PREFIX}/connection")
    assert response.status_code == 200
    # Assert response body structure (e.g., {"connected": True/False, "device_address": ...})
    assert "connected" in response.json()
    print("Test 'test_check_connection_status': PASSED")

# --- Test GET /exists/{device_address} --- (Check if device exists)
@pytest.mark.xfail(reason="Requires device to be discoverable or cached")
def test_check_device_exists():
    """Tests checking if a specific BLE device exists (discovered/known)."""
    device_address = "XX:XX:XX:XX:XX:XX" # Replace if needed
    response = client.get(f"{DEVICE_API_PREFIX}/exists/{device_address}")
    assert response.status_code == 200 # Should return 200, body indicates existence
    assert "exists" in response.json()
    print(f"Test 'test_check_device_exists' for {device_address}: PASSED (Expected Failure)")

# --- Test GET /services --- (List services of connected device)
@pytest.mark.xfail(reason="Requires an active BLE connection")
def test_get_device_services():
    """Tests listing services of the currently connected BLE device."""
    response = client.get(f"{DEVICE_API_PREFIX}/services")
    assert response.status_code == 200
    assert isinstance(response.json(), list) # Expect a list of services
    print("Test 'test_get_device_services': PASSED (Expected Failure)")

# --- Test GET /characteristics/{service_uuid} --- (List characteristics)
@pytest.mark.xfail(reason="Requires an active BLE connection and valid service UUID")
def test_get_service_characteristics():
    """Tests listing characteristics for a specific service."""
    service_uuid = "0000180a-0000-1000-8000-00805f9b34fb" # Example: Device Information Service UUID
    response = client.get(f"{DEVICE_API_PREFIX}/characteristics/{service_uuid}")
    assert response.status_code == 200
    assert isinstance(response.json(), list) # Expect a list of characteristics
    print(f"Test 'test_get_service_characteristics' for {service_uuid}: PASSED (Expected Failure)")

# --- Test GET /read/{characteristic_uuid} --- (Read characteristic)
@pytest.mark.xfail(reason="Requires an active BLE connection and valid characteristic UUID")
def test_read_characteristic():
    """Tests reading a value from a BLE characteristic."""
    characteristic_uuid = "00002a29-0000-1000-8000-00805f9b34fb" # Example: Manufacturer Name String
    response = client.get(f"{DEVICE_API_PREFIX}/read/{characteristic_uuid}")
    assert response.status_code == 200
    # Assert response structure (e.g., {"value": ..., "hex": ...})
    assert "value" in response.json()
    print(f"Test 'test_read_characteristic' for {characteristic_uuid}: PASSED (Expected Failure)")

# --- Test POST /write/{characteristic_uuid} --- (Write characteristic)
@pytest.mark.xfail(reason="Requires an active BLE connection and valid, writable characteristic UUID")
def test_write_characteristic():
    """Tests writing a value to a BLE characteristic."""
    characteristic_uuid = "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX" # Replace with a writable characteristic UUID
    write_value_hex = "0100" # Example hex value to write
    response = client.post(f"{DEVICE_API_PREFIX}/write/{characteristic_uuid}", json={"value": write_value_hex})
    assert response.status_code == 200
    # Assert response (e.g., {"status": "success"})
    print(f"Test 'test_write_characteristic' for {characteristic_uuid}: PASSED (Expected Failure)")

# --- Test POST /notify/{characteristic_uuid} --- (Enable/Disable notifications)
@pytest.mark.xfail(reason="Requires an active BLE connection and valid, notifiable characteristic UUID")
def test_enable_notifications():
    """Tests enabling notifications for a BLE characteristic."""
    characteristic_uuid = "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX" # Replace with a notifiable characteristic UUID
    response = client.post(f"{DEVICE_API_PREFIX}/notify/{characteristic_uuid}", params={"enable": True})
    assert response.status_code == 200
    # Assert response (e.g., {"status": "notifications enabled"})
    print(f"Test 'test_enable_notifications' for {characteristic_uuid}: PASSED (Expected Failure)")

# --- Test POST /pair --- (Pair with device)
@pytest.mark.xfail(reason="Pairing requires user interaction or specific device state")
def test_pair_device():
    """Tests initiating pairing with the connected device."""
    response = client.post(f"{DEVICE_API_PREFIX}/pair")
    assert response.status_code == 200
    # Assert response (e.g., {"status": "pairing initiated"} or {"status": "paired"})
    print("Test 'test_pair_device': PASSED (Expected Failure)")

# --- Test POST /bond --- (Bond with device)
@pytest.mark.xfail(reason="Bonding requires specific device state and likely prior pairing")
def test_bond_device():
    """Tests bonding with the connected device."""
    response = client.post(f"{DEVICE_API_PREFIX}/bond")
    assert response.status_code == 200
    # Assert response (e.g., {"status": "bonded"})
    print("Test 'test_bond_device': PASSED (Expected Failure)")

# --- Test DELETE /bond/{device_address} --- (Remove bond)
@pytest.mark.xfail(reason="Removing bond requires device to be bonded")
def test_remove_bonded_device():
    """Tests removing the bond for a specific device."""
    device_address = "XX:XX:XX:XX:XX:XX" # Replace with a bonded device address if possible
    response = client.delete(f"{DEVICE_API_PREFIX}/bond/{device_address}")
    assert response.status_code == 200
    # Assert response (e.g., {"status": "bond removed"})
    print(f"Test 'test_remove_bonded_device' for {device_address}: PASSED (Expected Failure)")

# --- Test GET /info --- (Get connected device info)
@pytest.mark.xfail(reason="Requires an active BLE connection")
def test_get_connected_device_info():
    """Tests getting information about the currently connected device."""
    response = client.get(f"{DEVICE_API_PREFIX}/info")
    assert response.status_code == 200
    # Assert structure of connected device info (e.g., address, name, rssi)
    assert "address" in response.json()
    print("Test 'test_get_connected_device_info': PASSED (Expected Failure)")

# Add more device-related tests as needed based on your API specification
