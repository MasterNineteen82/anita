"""
BLE API Tester

Handles testing of API endpoints extracted from the OpenAPI specification.
"""

import requests
import logging
import time
import urllib.parse
import json
from typing import Dict, List, Any, Optional, Union

class BLEAPITester:
    """Tester for BLE API endpoints."""

    def __init__(self, base_url: str, timeout: int = 10, retry_count: int = 1, 
                 headers: Optional[Dict[str, str]] = None, retry_delay: int = 1):
        """
        Initialize the API tester.
        
        :param base_url: Base URL for the API endpoints.
        :param timeout: Timeout for API requests in seconds.
        :param retry_count: Number of retries for failed requests.
        :param headers: Default headers for API requests.
        :param retry_delay: Delay between retries in seconds.
        :raises ValueError: If parameters are invalid.
        """
        # Validate parameters
        if not base_url:
            raise ValueError("Base URL cannot be empty")
        if not base_url.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid base URL format: {base_url}")
        if timeout <= 0:
            raise ValueError(f"Timeout must be positive: {timeout}")
        if retry_count < 0:
            raise ValueError(f"Retry count cannot be negative: {retry_count}")
        if retry_delay < 0:
            raise ValueError(f"Retry delay cannot be negative: {retry_delay}")
            
        # Remove trailing slash from base_url for consistency
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.headers = headers or {}
        self.logger = logging.getLogger('ble_tester.api')

    def test_endpoint(self, path, method, parameters, request_body, responses):
        url = f"{self.base_url}{path}"
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=request_body,
                timeout=self.timeout
            )
            return {
                'endpoint': path,
                'method': method,
                'status': 'Success' if response.status_code in responses else 'Failed',
                'status_code': response.status_code,
                'latency': response.elapsed.total_seconds() * 1000,
                'error': None if response.status_code in responses else response.text
            }
        except Exception as e:
            return {
                'endpoint': path,
                'method': method,
                'status': 'Failed',
                'status_code': None,
                'latency': 0,
                'error': str(e)
            }
    
    def _resolve_path_params(self, path: str, parameters: List[Dict[str, Any]]) -> str:
        """
        Replace path parameters with test values.
        
        :param path: The endpoint path with parameter placeholders.
        :param parameters: List of parameter definitions.
        :return: Path with parameters resolved.
        """
        resolved_path = path
        for param in parameters:
            if param.get('in') == 'path':
                param_name = param['name']
                param_placeholder = f"{{{param_name}}}"
                
                # Generate appropriate test value based on parameter type
                if param.get('schema', {}).get('type') == 'integer':
                    test_value = "1"
                elif param.get('schema', {}).get('type') == 'boolean':
                    test_value = "true"
                else:
                    test_value = "test"
                
                resolved_path = resolved_path.replace(param_placeholder, test_value)
        
        return resolved_path

    def _generate_test_payload(self, request_body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate a test payload based on the request body schema.
        
        :param request_body: The request body schema from the OpenAPI spec.
        :return: A dictionary representing the test payload.
        """
        if not request_body:
            return None

        try:
            # Use example values if provided in the schema
            content = request_body.get('content', {})
            for media_type, schema_info in content.items():
                # Check for direct example
                example = schema_info.get('example')
                if example:
                    return example

                # Get schema properties
                schema = schema_info.get('schema', {})
                
                # Check for examples at schema level
                if 'example' in schema:
                    return schema['example']
                
                # Generate based on schema properties
                properties = schema.get('properties', {})
                payload = {}
                
                for prop, details in properties.items():
                    # Handle required fields first
                    is_required = prop in schema.get('required', [])
                    
                    if 'example' in details:
                        payload[prop] = details['example']
                    elif details.get('type') == 'string':
                        if details.get('format') == 'date-time':
                            payload[prop] = "2023-01-01T00:00:00Z"
                        elif details.get('format') == 'uuid':
                            payload[prop] = "00000000-0000-0000-0000-000000000000"
                        elif details.get('enum'):
                            payload[prop] = details['enum'][0]
                        else:
                            payload[prop] = f"test_{prop}"
                    elif details.get('type') == 'integer':
                        payload[prop] = 1
                    elif details.get('type') == 'number':
                        payload[prop] = 1.0
                    elif details.get('type') == 'boolean':
                        payload[prop] = True
                    elif details.get('type') == 'array':
                        if is_required:
                            # Create a small array with sample item
                            items_schema = details.get('items', {})
                            if items_schema.get('type') == 'string':
                                payload[prop] = ["test"]
                            elif items_schema.get('type') == 'integer':
                                payload[prop] = [1]
                            elif items_schema.get('type') == 'boolean':
                                payload[prop] = [True]
                            else:
                                payload[prop] = []
                        else:
                            payload[prop] = []
                    elif details.get('type') == 'object':
                        if is_required:
                            # Recursively generate nested objects
                            nested_properties = details.get('properties', {})
                            nested_obj = {}
                            for nested_prop, nested_details in nested_properties.items():
                                if nested_details.get('type') == 'string':
                                    nested_obj[nested_prop] = f"test_{nested_prop}"
                                elif nested_details.get('type') == 'integer':
                                    nested_obj[nested_prop] = 1
                                elif nested_details.get('type') == 'boolean':
                                    nested_obj[nested_prop] = True
                            payload[prop] = nested_obj
                        else:
                            payload[prop] = {}
                
                return payload
            
            return None
        except Exception as e:
            self.logger.warning(f"Error generating test payload: {str(e)}")
            return {}

    def _prepare_query_params(self, parameters: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Prepare query parameters for the request.
        
        :param parameters: List of parameter definitions.
        :return: Dictionary of query parameters.
        """
        query_params = {}
        for param in parameters:
            if param.get('in') == 'query':
                param_name = param['name']
                schema = param.get('schema', {})
                
                # Skip if not required and not providing default values for all params
                if not param.get('required', False):
                    continue
                    
                # Generate appropriate test value based on parameter type
                if schema.get('type') == 'integer':
                    query_params[param_name] = "1"
                elif schema.get('type') == 'boolean':
                    query_params[param_name] = "true"
                elif schema.get('type') == 'array':
                    # Handle array parameters
                    query_params[param_name] = "test1,test2"
                else:
                    query_params[param_name] = "test"
        
        return query_params

    def execute_test(self, endpoint: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single API test.
        
        :param endpoint: The endpoint details extracted from the OpenAPI spec.
        :return: A dictionary containing the test result.
        """
        # Extract endpoint information
        path = endpoint.get('path', '')
        method = endpoint.get('method', 'GET')
        parameters = endpoint.get('parameters', [])
        request_body = endpoint.get('request_body', {})
        expected_responses = endpoint.get('responses', {})
        
        # Create a default result for error cases
        default_result = {
            'endpoint': path,
            'method': method,
            'status': "Failed",
            'status_code': None,
            'latency': None,
            'error': None,
            'response_data': None
        }
        
        try:
            # Resolve path parameters
            resolved_path = self._resolve_path_params(path, parameters)
            url = f"{self.base_url}{resolved_path}"
            
            # Prepare request components
            query_params = self._prepare_query_params(parameters)
            payload = self._generate_test_payload(request_body)
            headers = dict(self.headers)
            
            # Determine content type from request body if needed
            content_types = list(request_body.get('content', {}).keys()) if request_body else []
            if content_types and 'Content-Type' not in headers:
                headers['Content-Type'] = content_types[0]
            
            self.logger.debug(f"Testing {method} {url}")
            if payload:
                self.logger.debug(f"Payload: {json.dumps(payload)[:1000]}")
            
            # Execute the request with retries and exponential backoff
            for attempt in range(self.retry_count + 1):
                try:
                    start_time = time.time()
                    
                    # Execute request based on content type
                    if headers.get('Content-Type') == 'application/x-www-form-urlencoded':
                        response = requests.request(
                            method=method,
                            url=url,
                            headers=headers,
                            params=query_params,
                            data=payload,
                            timeout=self.timeout,
                            allow_redirects=True
                        )
                    elif headers.get('Content-Type') == 'multipart/form-data':
                        # Remove the Content-Type header as requests will set it with boundary
                        content_type = headers.pop('Content-Type')
                        response = requests.request(
                            method=method,
                            url=url,
                            headers=headers,
                            params=query_params,
                            files=payload,
                            timeout=self.timeout,
                            allow_redirects=True
                        )
                        # Restore the header for logging purposes
                        headers['Content-Type'] = content_type
                    else:
                        # Default to JSON
                        response = requests.request(
                            method=method,
                            url=url,
                            headers=headers,
                            params=query_params,
                            json=payload,
                            timeout=self.timeout,
                            allow_redirects=True
                        )
                    
                    latency = int((time.time() - start_time) * 1000)  # Convert to milliseconds
                    self.logger.debug(f"Response status: {response.status_code}, latency: {latency}ms")
                    
                    # Check for rate limiting
                    if response.status_code == 429:
                        retry_after = int(response.headers.get('Retry-After', self.retry_delay))
                        self.logger.warning(f"Rate limited. Retrying after {retry_after} seconds.")
                        time.sleep(retry_after)
                        continue
                    
                    # Validate the response
                    expected_status_codes = [int(code) for code in expected_responses.keys()]
                    # If no valid status codes are specified, consider 2xx as success
                    if not expected_status_codes:
                        status = "Success" if 200 <= response.status_code < 300 else "Failed"
                    else:
                        status = "Success" if response.status_code in expected_status_codes else "Failed"
                    
                    # Try to extract response data
                    response_data = None
                    try:
                        if response.headers.get('Content-Type', '').startswith('application/json'):
                            response_data = response.json()
                        else:
                            # Limit text response to prevent huge logs
                            response_data = response.text[:1000]
                    except Exception as e:
                        self.logger.debug(f"Could not parse response content: {str(e)}")
                    
                    error = None if status == "Success" else f"Unexpected status code: {response.status_code}"
                    
                    return {
                        'endpoint': path,
                        'method': method,
                        'status': status,
                        'status_code': response.status_code,
                        'latency': latency,
                        'error': error,
                        'response_data': response_data
                    }
                
                except requests.exceptions.Timeout as e:
                    self.logger.warning(f"Request timeout for {method} {url}: {str(e)}")
                    error_msg = f"Request timed out after {self.timeout} seconds"
                    # Only retry on timeouts
                    if attempt < self.retry_count:
                        wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                        self.logger.info(f"Retrying in {wait_time} seconds (attempt {attempt+1}/{self.retry_count})")
                        time.sleep(wait_time)
                    else:
                        default_result['error'] = error_msg
                        return default_result
                
                except requests.exceptions.ConnectionError as e:
                    self.logger.error(f"Connection error for {method} {url}: {str(e)}")
                    default_result['error'] = f"Connection error: {str(e)}"
                    return default_result
                
                except requests.exceptions.RequestException as e:
                    self.logger.error(f"Request failed for {method} {url}: {str(e)}")
                    default_result['error'] = f"Request failed: {str(e)}"
                    return default_result
        
        except Exception as e:
            self.logger.error(f"Unexpected error testing {method} {path}: {str(e)}", exc_info=True)
            default_result['error'] = f"Unexpected error: {str(e)}"
            return default_result
    
    def test_adapter_endpoints(self, endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Test BLE adapter-related endpoints.
        
        :param endpoints: List of adapter endpoints to test.
        :return: List of test results.
        """
        self.logger.info(f"Testing {len(endpoints)} adapter endpoints")
        return self.run_all_tests(endpoints)
    
    def test_scanner_endpoints(self, endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Test BLE scanner-related endpoints.
        
        :param endpoints: List of scanner endpoints to test.
        :return: List of test results.
        """
        self.logger.info(f"Testing {len(endpoints)} scanner endpoints")
        return self.run_all_tests(endpoints)
        
    def test_device_endpoints(self, endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Test BLE device-related endpoints.
        
        :param endpoints: List of device endpoints to test.
        :return: List of test results.
        """
        self.logger.info(f"Testing {len(endpoints)} device endpoints")
        return self.run_all_tests(endpoints)
    
    def test_service_endpoints(self, endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Test BLE service-related endpoints.
        
        :param endpoints: List of service endpoints to test.
        :return: List of test results.
        """
        self.logger.info(f"Testing {len(endpoints)} service endpoints")
        return self.run_all_tests(endpoints)
    
    def test_characteristic_endpoints(self, endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Test BLE characteristic-related endpoints.
        
        :param endpoints: List of characteristic endpoints to test.
        :return: List of test results.
        """
        self.logger.info(f"Testing {len(endpoints)} characteristic endpoints")
        return self.run_all_tests(endpoints)

    def run_all_tests(self, endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Run tests for all provided API endpoints.
        
        :param endpoints: A list of API endpoints to test.
        :return: A list of test results.
        """
        if not endpoints:
            self.logger.warning("No endpoints provided for testing")
            return []
            
        results = []
        for endpoint in endpoints:
            if not isinstance(endpoint, dict) or 'path' not in endpoint or 'method' not in endpoint:
                self.logger.warning(f"Invalid endpoint format, skipping: {endpoint}")
                continue
                
            self.logger.info(f"Testing {endpoint['method']} {endpoint['path']}...")
            try:
                result = self.execute_test(endpoint)
                results.append(result)
                
                # Log with appropriate level based on result status
                if result['status'] == 'Success':
                    self.logger.info(f"✓ {result['method']} {result['endpoint']}: {result['status']} ({result['latency']} ms)")
                else:
                    self.logger.error(f"✗ {result['method']} {result['endpoint']}: {result['status']} - {result['error']}")
                    
            except Exception as e:
                self.logger.error(f"Unexpected error in test execution for {endpoint['method']} {endpoint['path']}: {str(e)}", 
                                 exc_info=True)
                results.append({
                    'endpoint': endpoint['path'],
                    'method': endpoint['method'],
                    'status': 'Failed',
                    'status_code': None,
                    'latency': None,
                    'error': f"Test execution error: {str(e)}",
                    'response_data': None
                })
                
        return results