"""
BLE WebSocket Test Executor

Tests WebSocket endpoints for BLE notifications and events.
"""
import time
import json
import logging
import asyncio
import websockets
import re
from urllib.parse import urlparse
from uuid import uuid4
from typing import Dict, List, Any, Optional, Union

class BLEWebSocketTester:
    """Executes tests on BLE WebSocket endpoints."""
    
    def __init__(self, base_ws_url: str, auth_params: Optional[Dict[str, str]] = None, 
                 timeout: int = 10, retry_count: int = 1, retry_delay: float = 1.0):
        """
        Initialize the WebSocket tester.
        
        Args:
            base_ws_url: Base URL for WebSocket connections
            auth_params: Authentication parameters (dict with 'auth_token', 'auth_type')
            timeout: Connection timeout in seconds
            retry_count: Number of connection retries
            retry_delay: Delay between retries in seconds
        
        Raises:
            ValueError: If parameters are invalid
        """
        # Validate base URL
        if not base_ws_url:
            raise ValueError("Base WebSocket URL cannot be empty")
        
        if not (base_ws_url.startswith('ws://') or base_ws_url.startswith('wss://')):
            raise ValueError(f"Invalid WebSocket URL format: {base_ws_url}. Must start with ws:// or wss://")
            
        # Validate timeout
        if timeout <= 0:
            raise ValueError(f"Timeout must be positive: {timeout}")
            
        # Validate retry parameters
        if retry_count < 0:
            raise ValueError(f"Retry count cannot be negative: {retry_count}")
            
        if retry_delay < 0:
            raise ValueError(f"Retry delay cannot be negative: {retry_delay}")
        
        self.base_ws_url = base_ws_url
        self.auth_params = auth_params or {}
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.logger = logging.getLogger('ble_tester.websocket')
    
    async def test_websocket_endpoint(self, path: str, parameters: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Test a WebSocket endpoint identified by path.
        
        Args:
            path: WebSocket endpoint path or full URL
            parameters: WebSocket parameters (optional)
            
        Returns:
            Dictionary with test results
        """
        # Build endpoint object for compatibility with the test_websocket method
        endpoint = {
            'url': path,
            'type': 'notification',  # Default type
            'parameters': parameters or [],
            'description': f"WebSocket endpoint: {path}"
        }
        
        # Set the WebSocket type based on the path if possible
        if 'notification' in path.lower():
            endpoint['type'] = 'notification'
        elif 'log' in path.lower():
            endpoint['type'] = 'log'
        elif 'metrics' in path.lower():
            endpoint['type'] = 'metrics'
        elif 'ping' in path.lower():
            endpoint['type'] = 'ping'
            
        return await self.test_websocket(endpoint)
    
    async def test_websocket(self, ws_endpoint: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test a single WebSocket endpoint.
        
        Args:
            ws_endpoint: Dictionary with WebSocket endpoint details
            
        Returns:
            Dictionary with test results
        """
        # Extract endpoint details with validation
        url = ws_endpoint.get('url', '')
        if not url:
            self.logger.error("WebSocket endpoint URL is empty")
            return {
                'endpoint': 'unknown',
                'type': 'unknown',
                'status': 'Failed',
                'latency': 0,
                'error': "Empty WebSocket URL"
            }
        
        # If URL doesn't have a protocol, use the base WebSocket URL
        if not url.startswith('ws://') and not url.startswith('wss://'):
            url = f"{self.base_ws_url.rstrip('/')}/{url.lstrip('/')}"
            
        # Validate URL format
        try:
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError(f"Invalid URL format: {url}")
        except Exception as e:
            self.logger.error(f"Invalid WebSocket URL: {url}, error: {str(e)}")
            return {
                'endpoint': url,
                'type': ws_endpoint.get('type', 'unknown'),
                'status': 'Failed',
                'latency': 0,
                'error': f"Invalid WebSocket URL: {str(e)}"
            }
            
        ws_type = ws_endpoint.get('type', 'notification')
        description = ws_endpoint.get('description', '')
        
        # Initialize result
        result = {
            'endpoint': url,
            'type': ws_type,
            'description': description,
            'status': 'Failed',
            'connection_status': 'Disconnected',
            'latency': None,
            'messages': [],
            'error': None,
            'timestamp': time.time()
        }
        
        # Prepare WebSocket connection
        extra_headers = {}
        
        # Handle different authentication types
        if 'auth_token' in self.auth_params:
            auth_type = self.auth_params.get('auth_type', 'Bearer')
            extra_headers['Authorization'] = f"{auth_type} {self.auth_params['auth_token']}"
        
        # Add custom headers if provided
        if 'headers' in self.auth_params and isinstance(self.auth_params['headers'], dict):
            extra_headers.update(self.auth_params['headers'])
        
        # Attempt connection with retries
        for attempt in range(self.retry_count + 1):
            try:
                # Connect to WebSocket with timeout
                self.logger.info(f"Connecting to WebSocket: {url} (attempt {attempt+1}/{self.retry_count+1})")
                start_time = time.time()
                
                connect_timeout = self.timeout
                connection_task = websockets.connect(
                    url, 
                    extra_headers=extra_headers, 
                    ping_interval=None, 
                    ping_timeout=None,
                    close_timeout=self.timeout
                )
                
                # Use asyncio.wait_for to enforce a timeout on connection
                websocket = await asyncio.wait_for(connection_task, timeout=connect_timeout)
                
                async with websocket:
                    # Calculate connection latency
                    connection_latency = (time.time() - start_time) * 1000  # Convert to milliseconds
                    result['latency'] = round(connection_latency, 2)
                    result['connection_status'] = 'Connected'
                    
                    self.logger.info(f"Successfully connected to {url} ({result['latency']} ms)")
                    
                    # Prepare a test message based on WebSocket type with parameter customization
                    test_message = self._generate_test_message(ws_type, ws_endpoint.get('parameters', []))
                    
                    if test_message:
                        # Send test message
                        self.logger.info(f"Sending test message to {url}: {json.dumps(test_message)}")
                        await websocket.send(json.dumps(test_message))
                    
                    # Listen for messages with timeout
                    response_received = False
                    listen_start = time.time()
                    max_listen_time = 5  # Listen for up to 5 seconds
                    
                    while time.time() - listen_start < max_listen_time:
                        try:
                            # Set a timeout for receiving messages
                            response = await asyncio.wait_for(websocket.recv(), timeout=2)
                            response_received = True
                            
                            try:
                                # Try to parse as JSON
                                message = json.loads(response)
                                self.logger.debug(f"Received JSON message: {json.dumps(message)}")
                            except json.JSONDecodeError:
                                message = response
                                self.logger.debug(f"Received non-JSON message: {response}")
                                
                            result['messages'].append(message)
                            self.logger.info(f"Received message from {url}")
                            
                            # For simple ping test, we can stop after first message
                            if ws_type == 'ping':
                                break
                        except asyncio.TimeoutError:
                            # No message received within timeout
                            self.logger.debug(f"No message received within timeout")
                            break
                        except websockets.exceptions.ConnectionClosedOK:
                            self.logger.info(f"WebSocket connection closed normally")
                            break
                        except websockets.exceptions.ConnectionClosedError as e:
                            self.logger.warning(f"WebSocket connection closed with error: {str(e)}")
                            result['error'] = f"Connection closed: {str(e)}"
                            break
                    
                    if response_received or ws_type == 'ping' or not test_message:
                        result['status'] = 'Success'
                    else:
                        result['error'] = "No response received within timeout"
                
                # If we reach here without exception, connection was successful
                break
            
            except asyncio.TimeoutError:
                error_msg = f"Connection timeout after {self.timeout} seconds"
                result['error'] = error_msg
                self.logger.error(f"{error_msg} for {url}")
                
                # If not the last attempt, wait before retrying
                if attempt < self.retry_count:
                    await asyncio.sleep(self.retry_delay)
            
            except websockets.exceptions.WebSocketException as e:
                error_msg = f"WebSocket connection error: {str(e)}"
                result['error'] = error_msg
                self.logger.error(f"Failed to connect to {url}: {str(e)}")
                
                # If not the last attempt, wait before retrying
                if attempt < self.retry_count:
                    await asyncio.sleep(self.retry_delay)
                
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                result['error'] = error_msg
                self.logger.error(f"Error testing WebSocket {url}: {str(e)}", exc_info=True)
                
                # Don't retry on unexpected errors
                break
        
        # Record end timestamp
        result['test_duration'] = round((time.time() - result['timestamp']) * 1000, 2)
        result['timestamp'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(result['timestamp']))
        
        return result
    
    def _generate_test_message(self, ws_type: str, parameters: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a test message based on WebSocket type and parameters.
        
        Args:
            ws_type: WebSocket type (notification, ping, log, etc.)
            parameters: List of parameter dictionaries with name, value, etc.
            
        Returns:
            Dictionary with test message payload
        """
        # Extract parameter values if provided
        param_values = {}
        if parameters:
            for param in parameters:
                if 'name' in param and 'value' in param:
                    param_values[param['name']] = param['value']
        
        # Base message with defaults that can be overridden
        base_message = {
            'id': str(uuid4())
        }
        
        if ws_type == 'notification':
            message = {
                'type': 'subscribe',
                'deviceId': param_values.get('deviceId', '00000000-0000-0000-0000-000000000000'),
                'characteristicUuid': param_values.get('characteristicUuid', '00002a37-0000-1000-8000-00805f9b34fb'),
                'serviceUuid': param_values.get('serviceUuid', '0000180d-0000-1000-8000-00805f9b34fb')
            }
        elif ws_type == 'ping':
            message = {
                'type': 'ping'
            }
        elif ws_type == 'log':
            message = {
                'type': 'subscribe',
                'level': param_values.get('level', 'info')
            }
        elif ws_type == 'metrics':
            message = {
                'type': 'subscribe',
                'metrics': param_values.get('metrics', ['cpu', 'memory', 'connections'])
            }
        elif ws_type == 'custom' and 'message' in param_values:
            # Allow fully custom messages
            try:
                if isinstance(param_values['message'], str):
                    message = json.loads(param_values['message'])
                else:
                    message = param_values['message']
            except (json.JSONDecodeError, TypeError):
                self.logger.error(f"Invalid custom message format: {param_values['message']}")
                message = {'type': 'custom', 'error': 'Invalid message format'}
        else:
            message = {
                'type': 'hello'
            }
            
        # Merge with base message
        return {**base_message, **message}
    
    async def run_all_tests(self, websocket_endpoints: List[Dict[str, Any]], 
                          concurrent: bool = False, max_concurrency: int = 5) -> List[Dict[str, Any]]:
        """
        Run tests for all WebSocket endpoints.
        
        Args:
            websocket_endpoints: List of WebSocket endpoint dictionaries
            concurrent: Whether to run tests concurrently
            max_concurrency: Maximum number of concurrent tests
            
        Returns:
            List of test result dictionaries
        """
        if not websocket_endpoints:
            self.logger.warning("No WebSocket endpoints provided for testing")
            return []
            
        self.logger.info(f"Running tests for {len(websocket_endpoints)} WebSocket endpoints")
        
        results = []
        
        if concurrent:
            # Run tests concurrently with limited concurrency
            self.logger.info(f"Running WebSocket tests concurrently (max {max_concurrency} simultaneous)")
            tasks = []
            
            for endpoint in websocket_endpoints:
                tasks.append(self.test_websocket(endpoint))
                
                # If we've reached max concurrency, wait for tasks to complete
                if len(tasks) >= max_concurrency:
                    completed_results = await asyncio.gather(*tasks)
                    results.extend(completed_results)
                    tasks = []
            
            # Wait for any remaining tasks
            if tasks:
                completed_results = await asyncio.gather(*tasks)
                results.extend(completed_results)
        else:
            # Run tests sequentially
            self.logger.info("Running WebSocket tests sequentially")
            for endpoint in websocket_endpoints:
                self.logger.info(f"Testing WebSocket endpoint: {endpoint.get('url', 'unknown')}")
                result = await self.test_websocket(endpoint)
                results.append(result)
                
                # Wait a bit between tests to avoid overwhelming the server
                await asyncio.sleep(self.retry_delay)
        
        # Log summary
        successful = sum(1 for r in results if r['status'] == 'Success')
        self.logger.info(f"WebSocket tests completed: {successful}/{len(results)} successful")
        
        return results