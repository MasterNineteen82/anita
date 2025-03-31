"""
OpenAPI Specification Parser for BLE Module Testing

Extracts API endpoints and WebSocket connections from an OpenAPI specification.
"""
import json
import yaml
import logging
from pathlib import Path
import re
from typing import Dict, List, Any, Optional, Union

class BLESpecParser:
    """Parser for OpenAPI specifications focused on BLE functionality."""
    
    def __init__(self, spec_file_path: str):
        """
        Initialize the parser with the path to the OpenAPI spec file.
        
        Args:
            spec_file_path: Path to the OpenAPI specification file (YAML or JSON)
        
        Raises:
            ValueError: If the spec_file_path is None or empty
        """
        if not spec_file_path:
            raise ValueError("OpenAPI specification file path cannot be empty")
        
        self.spec_file_path = spec_file_path
        self.logger = logging.getLogger('ble_tester.parser')
        self.spec = None
    
    def parse_openapi_spec(self) -> Dict[str, Any]:
        """
        Load and parse the OpenAPI specification file.
        
        Returns:
            The parsed OpenAPI specification as a dictionary
            
        Raises:
            FileNotFoundError: If the spec file doesn't exist
            ValueError: If the file format is not supported or the spec is invalid
            yaml.YAMLError: If there's an error parsing the YAML file
            json.JSONDecodeError: If there's an error parsing the JSON file
        """
        file_path = Path(self.spec_file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"OpenAPI specification file not found: {self.spec_file_path}")
        
        try:
            if file_path.suffix.lower() in ['.yaml', '.yml']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.spec = yaml.safe_load(f)
            elif file_path.suffix.lower() == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.spec = json.load(f)
            else:
                raise ValueError(f"Unsupported file format: {file_path.suffix}. Use YAML or JSON.")
            
            # Validate basic OpenAPI structure
            if not isinstance(self.spec, dict):
                raise ValueError("OpenAPI specification must be a JSON object/YAML map")
            
            # Check for required OpenAPI fields
            if 'openapi' not in self.spec:
                self.logger.warning("Specification might not be OpenAPI - missing 'openapi' version field")
            
            if 'paths' not in self.spec or not isinstance(self.spec['paths'], dict):
                self.logger.warning("OpenAPI specification has no valid 'paths' section")
                self.spec['paths'] = {}
            
            self.logger.info(f"Successfully parsed OpenAPI spec: {file_path.name}")
            return self.spec
            
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing YAML file: {str(e)}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing JSON file: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error parsing OpenAPI specification: {str(e)}")
            raise ValueError(f"Failed to parse OpenAPI specification: {str(e)}")
    
    def _extract_endpoint_common(self, keyword_list: List[str]) -> List[Dict[str, Any]]:
        """
        Common method for extracting endpoints based on keywords.
        
        Args:
            keyword_list: List of keywords to search for in paths
            
        Returns:
            List of matching endpoint dictionaries
            
        Raises:
            ValueError: If the OpenAPI spec is not loaded
        """
        if not self.spec:
            raise ValueError("OpenAPI spec not loaded. Call parse_openapi_spec() first.")
            
        endpoints = []
        
        try:
            # Look for paths matching the keywords
            for path, path_item in self.spec.get('paths', {}).items():
                # Skip if path_item is not a dict (malformed OpenAPI)
                if not isinstance(path_item, dict):
                    self.logger.warning(f"Skipping malformed path item at {path} - not a dict")
                    continue
                    
                # Check if path contains related keywords
                if any(keyword in path.lower() for keyword in keyword_list):
                    for method, operation in path_item.items():
                        if method.lower() in ['get', 'post', 'put', 'delete', 'patch']:
                            # Skip if operation is not a dict (malformed OpenAPI)
                            if not isinstance(operation, dict):
                                self.logger.warning(f"Skipping malformed operation at {path}/{method} - not a dict")
                                continue
                                
                            endpoint = {
                                'path': path,
                                'method': method.upper(),
                                'operation_id': operation.get('operationId', ''),
                                'summary': operation.get('summary', ''),
                                'description': operation.get('description', ''),
                                'parameters': operation.get('parameters', []),
                                'request_body': operation.get('requestBody', {}),
                                'responses': operation.get('responses', {})
                            }
                            endpoints.append(endpoint)
            
            return endpoints
        except Exception as e:
            self.logger.error(f"Error extracting endpoints with keywords {keyword_list}: {str(e)}")
            raise
    
    def extract_adapter_endpoints(self) -> List[Dict[str, Any]]:
        """
        Extract BLE adapter-related endpoints.
        
        Returns:
            List of adapter-related endpoint dictionaries
            
        Raises:
            ValueError: If the OpenAPI spec is not loaded
        """
        try:
            adapter_endpoints = self._extract_endpoint_common(['adapter', 'bluetooth', 'ble'])
            self.logger.info(f"Extracted {len(adapter_endpoints)} adapter-related endpoints")
            return adapter_endpoints
        except Exception as e:
            self.logger.error(f"Failed to extract adapter endpoints: {str(e)}")
            return []
    
    def extract_scanner_endpoints(self) -> List[Dict[str, Any]]:
        """
        Extract device scanning related endpoints.
        
        Returns:
            List of scanner-related endpoint dictionaries
            
        Raises:
            ValueError: If the OpenAPI spec is not loaded
        """
        try:
            scanner_endpoints = self._extract_endpoint_common(['scan', 'discover'])
            self.logger.info(f"Extracted {len(scanner_endpoints)} scanner-related endpoints")
            return scanner_endpoints
        except Exception as e:
            self.logger.error(f"Failed to extract scanner endpoints: {str(e)}")
            return []
    
    def extract_device_endpoints(self) -> List[Dict[str, Any]]:
        """
        Extract device connection and management endpoints.
        
        Returns:
            List of device-related endpoint dictionaries
            
        Raises:
            ValueError: If the OpenAPI spec is not loaded
        """
        try:
            device_endpoints = self._extract_endpoint_common(['device', 'connect', 'disconnect'])
            self.logger.info(f"Extracted {len(device_endpoints)} device-related endpoints")
            return device_endpoints
        except Exception as e:
            self.logger.error(f"Failed to extract device endpoints: {str(e)}")
            return []
    
    def extract_service_endpoints(self) -> List[Dict[str, Any]]:
        """
        Extract GATT service related endpoints.
        
        Returns:
            List of service-related endpoint dictionaries
            
        Raises:
            ValueError: If the OpenAPI spec is not loaded
        """
        try:
            service_endpoints = self._extract_endpoint_common(['service', 'gatt'])
            self.logger.info(f"Extracted {len(service_endpoints)} service-related endpoints")
            return service_endpoints
        except Exception as e:
            self.logger.error(f"Failed to extract service endpoints: {str(e)}")
            return []
    
    def extract_characteristic_endpoints(self) -> List[Dict[str, Any]]:
        """
        Extract characteristic related endpoints (read/write/notify).
        
        Returns:
            List of characteristic-related endpoint dictionaries
            
        Raises:
            ValueError: If the OpenAPI spec is not loaded
        """
        try:
            characteristic_endpoints = self._extract_endpoint_common(['characteristic', 'char', 'property'])
            self.logger.info(f"Extracted {len(characteristic_endpoints)} characteristic-related endpoints")
            return characteristic_endpoints
        except Exception as e:
            self.logger.error(f"Failed to extract characteristic endpoints: {str(e)}")
            return []
    
    def extract_websocket_endpoints(self) -> List[Dict[str, Any]]:
        """
        Extract WebSocket endpoints for BLE notifications and events.
        
        Returns:
            List of WebSocket-related endpoint dictionaries
            
        Raises:
            ValueError: If the OpenAPI spec is not loaded
        """
        if not self.spec:
            raise ValueError("OpenAPI spec not loaded. Call parse_openapi_spec() first.")
            
        websocket_endpoints = []
        
        try:
            # Check for standard WebSocket definitions in OpenAPI 3.1 (callbacks or webhooks)
            callbacks = {}
            
            # Extract from paths
            for path, path_item in self.spec.get('paths', {}).items():
                if not isinstance(path_item, dict):
                    continue
                    
                for method, operation in path_item.items():
                    if method.lower() in ['get', 'post'] and isinstance(operation, dict):
                        # Check if operation has callbacks (WebSocket)
                        if 'callbacks' in operation and isinstance(operation['callbacks'], dict):
                            callbacks.update(operation['callbacks'])
                        
                        # Look for WebSocket URLs in description
                        description = operation.get('description', '')
                        if description and ('websocket' in description.lower() or 'ws://' in description or 'wss://' in description):
                            # Try to extract WebSocket URL from description using regex
                            # This regex matches ws:// or wss:// followed by anything up to whitespace, quotes, or commas
                            ws_urls = re.findall(r'(wss?://[^\s",\'<>]+)', description)
                            
                            for url in ws_urls:
                                websocket_endpoints.append({
                                    'path': url,  # Use 'path' for consistency with the test runner
                                    'url': url,
                                    'type': 'notification',
                                    'related_path': path,
                                    'description': f"WebSocket URL found in description of {path}",
                                    'parameters': []  # Empty parameters for consistency
                                })
            
            # Check for WebSocket in components section (custom extension)
            components = self.spec.get('components', {})
            if 'x-websockets' in components and isinstance(components['x-websockets'], dict):
                for ws_name, ws_info in components['x-websockets'].items():
                    if isinstance(ws_info, dict):
                        url = ws_info.get('url', '')
                        if url:
                            websocket_endpoints.append({
                                'path': url,  # Use 'path' for consistency
                                'url': url,
                                'type': ws_info.get('type', 'unknown'),
                                'description': ws_info.get('description', ''),
                                'parameters': ws_info.get('parameters', [])
                            })
            
            # Check for WebSocket in custom top-level extension
            if 'x-websockets' in self.spec and isinstance(self.spec['x-websockets'], dict):
                for ws_name, ws_info in self.spec['x-websockets'].items():
                    if isinstance(ws_info, dict):
                        url = ws_info.get('url', '')
                        if url:
                            websocket_endpoints.append({
                                'path': url,  # Use 'path' for consistency
                                'url': url,
                                'type': ws_info.get('type', 'unknown'),
                                'description': ws_info.get('description', ''),
                                'parameters': ws_info.get('parameters', [])
                            })
            
            self.logger.info(f"Extracted {len(websocket_endpoints)} WebSocket endpoints")
            return websocket_endpoints
        except Exception as e:
            self.logger.error(f"Failed to extract WebSocket endpoints: {str(e)}")
            return []
    
    def get_security_requirements(self) -> Dict[str, Any]:
        """
        Extract security requirements from the OpenAPI spec.
        
        Returns:
            Dictionary containing security schemes and global security requirements
            
        Raises:
            ValueError: If the OpenAPI spec is not loaded
        """
        if not self.spec:
            raise ValueError("OpenAPI spec not loaded. Call parse_openapi_spec() first.")
        
        try:
            security_schemes = self.spec.get('components', {}).get('securitySchemes', {})
            global_security = self.spec.get('security', [])
            
            result = {
                'security_schemes': security_schemes,
                'global_security': global_security
            }
            
            self.logger.info(f"Extracted {len(security_schemes)} security schemes")
            return result
        except Exception as e:
            self.logger.error(f"Failed to extract security requirements: {str(e)}")
            return {'security_schemes': {}, 'global_security': []}
    
    def extract_all_endpoints(self) -> Dict[str, Any]:
        """
        Extract all BLE-related endpoints in a structured format.
        
        Returns:
            Dictionary containing all endpoint types
        
        Note:
            This is an alias for get_all_endpoints for compatibility
        """
        return self.get_all_endpoints()
    
    def get_all_endpoints(self) -> Dict[str, Any]:
        """
        Get all BLE-related endpoints in a structured format.
        
        Returns:
            Dictionary containing all endpoint types organized by category
        """
        try:
            if not self.spec:
                self.parse_openapi_spec()
                
            return {
                'adapter_endpoints': self.extract_adapter_endpoints(),
                'scanner_endpoints': self.extract_scanner_endpoints(),
                'device_endpoints': self.extract_device_endpoints(),
                'service_endpoints': self.extract_service_endpoints(),
                'characteristic_endpoints': self.extract_characteristic_endpoints(),
                'websocket_endpoints': self.extract_websocket_endpoints(),
                'security': self.get_security_requirements()
            }
        except Exception as e:
            self.logger.error(f"Failed to extract all endpoints: {str(e)}")
            return {
                'adapter_endpoints': [],
                'scanner_endpoints': [],
                'device_endpoints': [],
                'service_endpoints': [],
                'characteristic_endpoints': [],
                'websocket_endpoints': [],
                'security': {'security_schemes': {}, 'global_security': []}
            }