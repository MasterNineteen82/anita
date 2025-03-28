#!/usr/bin/env python
# BLE Diagnostic Script - Tests all BLE routes and WebSocket functionality

import asyncio
import json
import time
import sys
import aiohttp
import websockets
import logging
import argparse
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('ble_diagnostic.log')
    ]
)
logger = logging.getLogger("ble_diagnostics")

# Configuration (will be overridable via command line)
BASE_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/ws/ble"
TEST_DEVICE_ADDRESS = "D8:D6:68:6B:03:F4"  # Update with your test device address
TIMEOUT = 10  # seconds

# Test results
results = {
    "http_routes": {},
    "websocket": {"connection": False, "messages_received": 0},
    "device_scan": {"success": False, "devices_found": 0},
    "device_connection": {"success": False},
    "characteristics": {"read": {}, "write": {}, "notify": {}},
    "disconnection": {"success": False}
}

def log_result(component, test, success, message):
    """Log test result and store in results dict"""
    status = "[PASS]" if success else "[FAIL]"
    logger.info(f"{status} - {component}.{test}: {message}")
    
    if component not in results:
        results[component] = {}
    results[component][test] = {"success": success, "message": message}

async def test_http_route(session, route, method="get", data=None):
    """Test a specific HTTP route and return result"""
    url = f"{BASE_URL}{route}"
    try:
        start_time = time.time()
        if method.lower() == "get":
            response = await session.get(url, timeout=TIMEOUT)
        elif method.lower() == "post":
            response = await session.post(url, json=data or {}, timeout=TIMEOUT)
        elif method.lower() == "delete":
            response = await session.delete(url, timeout=TIMEOUT)
        elapsed = time.time() - start_time
        
        success = response.status < 400
        log_result("http_routes", route, success, 
                  f"Status {response.status}, time {elapsed:.2f}s")
        
        if success:
            try:
                return {"success": True, "data": await response.json(), "status": response.status}
            except aiohttp.ContentTypeError:
                return {"success": True, "data": await response.text(), "status": response.status}
        else:
            return {"success": False, "error": await response.text(), "status": response.status}
    except Exception as e:
        log_result("http_routes", route, False, f"Exception: {str(e)}")
        return {"success": False, "error": str(e)}

async def test_websocket():
    """Test WebSocket connection and functionality"""
    try:
        logger.info("Connecting to WebSocket...")
        async with websockets.connect(WS_URL, ping_interval=None, close_timeout=TIMEOUT) as websocket:
            results["websocket"]["connection"] = True
            log_result("websocket", "connection", True, "Connected successfully")
            
            # Send ping message
            await websocket.send(json.dumps({"type": "ping"}))
            logger.info("Sent ping message, waiting for response...")
            
            try:
                # Wait for response with timeout
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                results["websocket"]["messages_received"] += 1
                logger.info(f"Received WebSocket message: {response}")
                
                try:
                    data = json.loads(response)
                    if data.get("type") == "pong":
                        log_result("websocket", "ping_pong", True, "Received pong response")
                except json.JSONDecodeError:
                    log_result("websocket", "message_parse", False, "Could not parse WebSocket message")
            except asyncio.TimeoutError:
                log_result("websocket", "response", False, "Timeout waiting for WebSocket response")
    except Exception as e:
        log_result("websocket", "connection", False, f"Connection failed: {str(e)}")

async def test_device_scan(session):
    """Test BLE device scanning"""
    try:
        logger.info("Testing device scanning...")
        scan_result = await test_http_route(session, "/api/ble/scan", "post", 
                                        {"duration": 5, "active": True})
        
        if scan_result["success"]:
            devices = scan_result["data"].get("devices", [])
            results["device_scan"]["devices_found"] = len(devices)
            results["device_scan"]["success"] = True
            
            test_device_found = any(device.get("address") == TEST_DEVICE_ADDRESS.lower() for device in devices)
            log_result("device_scan", "test_device_found", test_device_found, 
                      f"Test device {'found' if test_device_found else 'not found'} in scan results")
            
            return {"success": True, "devices": devices}
        else:
            log_result("device_scan", "api_call", False, f"Scan API call failed: {scan_result.get('error')}")
            return {"success": False}
    except Exception as e:
        log_result("device_scan", "exception", False, f"Error during scan: {str(e)}")
        return {"success": False, "error": str(e)}

async def test_device_connection(session):
    """Test BLE device connection"""
    try:
        logger.info(f"Testing connection to device {TEST_DEVICE_ADDRESS}...")
        # Use the correct route format with device address in the path
        connect_result = await test_http_route(session, f"/api/ble/connect/{TEST_DEVICE_ADDRESS}", "post", {})
        
        if connect_result["success"] and connect_result["status"] < 400:
            results["device_connection"]["success"] = True
            log_result("device_connection", "connect", True, "Connected successfully")
            return True
        else:
            log_result("device_connection", "connect", False, 
                      f"Connection failed: {connect_result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        log_result("device_connection", "exception", False, f"Exception during connection: {str(e)}")
        return False

async def test_characteristics(session):
    """Test reading/writing BLE characteristics"""
    # Test reading characteristics
    try:
        logger.info("Testing characteristic operations...")
        # Get device info to view services
        device_info_result = await test_http_route(session, f"/api/ble/device/{TEST_DEVICE_ADDRESS}")
        
        if not device_info_result["success"]:
            log_result("characteristics", "services", False, "Failed to get device info")
            return
        
        services = device_info_result["data"].get("services", [])
        if not services:
            log_result("characteristics", "services", False, "No services found")
            return
        
        # Find a characteristic to read and write
        for service in services:
            characteristics = service.get("characteristics", [])
            for characteristic in characteristics:
                char_uuid = characteristic.get("uuid")
                logger.info(f"Testing characteristic {char_uuid}")
                
                # Test reading if readable
                if characteristic.get("properties", {}).get("read"):
                    logger.info(f"Testing read for characteristic {char_uuid}")
                    read_result = await test_http_route(
                        session, 
                        f"/api/ble/characteristics/{char_uuid}/read"
                    )
                    success = read_result["success"]
                    log_result("characteristics", f"read_{char_uuid}", success, 
                              f"Read {'successful' if success else 'failed'}")
                    results["characteristics"]["read"][char_uuid] = success
                
                # Test writing if writable
                if characteristic.get("properties", {}).get("write"):
                    logger.info(f"Testing write for characteristic {char_uuid}")
                    write_result = await test_http_route(
                        session, 
                        f"/api/ble/characteristics/{char_uuid}/write", 
                        "post",
                        {"value": "AABBCC"}
                    )
                    success = write_result["success"]
                    log_result("characteristics", f"write_{char_uuid}", success, 
                              f"Write {'successful' if success else 'failed'}")
                    results["characteristics"]["write"][char_uuid] = success
                
                # Test notifications if notifiable
                if characteristic.get("properties", {}).get("notify"):
                    logger.info(f"Testing notify for characteristic {char_uuid}")
                    notify_result = await test_http_route(
                        session, 
                        f"/api/ble/characteristics/{char_uuid}/subscribe", 
                        "post",
                        {}
                    )
                    success = notify_result["success"]
                    log_result("characteristics", f"notify_{char_uuid}", success, 
                              f"Subscribe {'successful' if success else 'failed'}")
                    results["characteristics"]["notify"][char_uuid] = success
                    
                    # Unsubscribe after testing
                    if success:
                        await test_http_route(
                            session, 
                            f"/api/ble/characteristics/{char_uuid}/unsubscribe", 
                            "post",
                            {}
                        )
    except Exception as e:
        log_result("characteristics", "exception", False, f"Exception during characteristic tests: {str(e)}")

async def test_device_disconnection(session):
    """Test BLE device disconnection"""
    try:
        logger.info(f"Testing disconnection from device {TEST_DEVICE_ADDRESS}...")
        disconnect_result = await test_http_route(
            session, 
            f"/api/ble/disconnect/{TEST_DEVICE_ADDRESS}", 
            "post", 
            {}
        )
        
        success = disconnect_result["success"] and disconnect_result["status"] < 400
        results["disconnection"]["success"] = success
        log_result("disconnection", "disconnect", success, 
                  "Disconnected successfully" if success else "Disconnection failed")
        return success
    except Exception as e:
        log_result("disconnection", "exception", False, f"Exception during disconnection: {str(e)}")
        return False

def print_summary():
    """Print a summary of all test results"""
    print("\n" + "="*80)
    print("BLE DIAGNOSTICS SUMMARY")
    print("="*80)
    
    total_tests = 0
    passed_tests = 0
    
    for component, tests in results.items():
        if isinstance(tests, dict) and not any(k in ["connection", "success", "devices_found", "messages_received"] for k in tests.keys()):
            component_total = len(tests)
            component_passed = sum(1 for t in tests.values() if t.get("success", False))
            print(f"{component}: {component_passed}/{component_total} tests passed")
            total_tests += component_total
            passed_tests += component_passed
    
    print("-"*80)
    if total_tests > 0:
        print(f"OVERALL: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.1f}%)")
    else:
        print("OVERALL: No tests were run")
    print("="*80)

async def run_diagnostics():
    """Run all diagnostic tests in sequence"""
    logger.info("Starting BLE diagnostics...")
    
    async with aiohttp.ClientSession() as session:
        # Test HTTP health check
        await test_http_route(session, "/api/health")
        
        # Test BLE adapter info
        await test_http_route(session, "/api/ble/adapter-info")
        
        # Test device-exists endpoint
        await test_http_route(session, f"/api/ble/device-exists/{TEST_DEVICE_ADDRESS}")
        
        # Test cached devices endpoint 
        await test_http_route(session, "/api/ble/devices/cached")
        
        # Test WebSocket
        await test_websocket()
        
        # Test device scanning
        scan_result = await test_device_scan(session)
        if scan_result["success"] and any(d.get("address") == TEST_DEVICE_ADDRESS.lower() for d in scan_result.get("devices", [])):
            connected = await test_device_connection(session)
            
            if connected:
                # Test characteristics
                await test_characteristics(session)
                
                # Test disconnection
                await test_device_disconnection(session)
        else:
            logger.warning(f"Test device {TEST_DEVICE_ADDRESS} not found, skipping connection tests")
            
    logger.info("BLE diagnostics completed.")
    print_summary()

def parse_arguments():
    """Parse command line arguments"""
    # Fix the global declaration - it must come before using the variables
    global BASE_URL, WS_URL, TEST_DEVICE_ADDRESS, TIMEOUT
    
    parser = argparse.ArgumentParser(description="BLE Diagnostic Tool")
    parser.add_argument("--url", default=BASE_URL, help=f"Base URL for the BLE API (default: {BASE_URL})")
    parser.add_argument("--ws", default=WS_URL, help=f"WebSocket URL (default: {WS_URL})")
    parser.add_argument("--device", default=TEST_DEVICE_ADDRESS, help=f"Test device address (default: {TEST_DEVICE_ADDRESS})")
    parser.add_argument("--timeout", type=int, default=TIMEOUT, help=f"Timeout in seconds (default: {TIMEOUT})")
    
    args = parser.parse_args()
    
    BASE_URL = args.url
    WS_URL = args.ws
    TEST_DEVICE_ADDRESS = args.device
    TIMEOUT = args.timeout
    
    return args

if __name__ == "__main__":
    parse_arguments()
    logger.info(f"Using BASE_URL: {BASE_URL}")
    logger.info(f"Using WebSocket URL: {WS_URL}")
    logger.info(f"Test device: {TEST_DEVICE_ADDRESS}")
    
    try:
        asyncio.run(run_diagnostics())
    except KeyboardInterrupt:
        logger.info("Diagnostics interrupted by user")
    except Exception as e:
        logger.error(f"Error during diagnostics: {str(e)}", exc_info=True)
        sys.exit(1)