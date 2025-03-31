"""
Configuration Manager for BLE API Testing

Processes command-line arguments, environment variables, and config files to configure the test script.
"""
import os
import json
import yaml
import argparse
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv

class BLETestConfig:
    """Manages configuration for BLE API testing."""
    
    def __init__(self, args=None, config_file=None):
        """
        Initialize the configuration manager.
        
        Args:
            args: Optional parsed args or dict with configuration values
            config_file: Optional path to a configuration file (JSON/YAML)
        """
        self.logger = logging.getLogger('ble_tester.config')
        self.config = {}
        
        # Default configuration
        self.defaults = {
            'timeout': 10,
            'retries': 1,
            'concurrency': 5,
            'format': 'text',
            'log_level': 'info'
        }
        
        # Load configuration in order of priority: defaults -> env -> file -> args
        self._load_defaults()
        
        # Load environment variables
        try:
            load_dotenv()
            self.load_from_env()
        except Exception as e:
            self.logger.warning(f"Error loading environment variables: {str(e)}")
        
        # Load from config file if provided
        if config_file:
            try:
                self.load_from_file(config_file)
            except Exception as e:
                self.logger.error(f"Error loading config file: {str(e)}")
        
        # Load from args if provided
        if args:
            if isinstance(args, argparse.Namespace):
                self.config.update({k: v for k, v in vars(args).items() if v is not None})
            elif isinstance(args, dict):
                self.config.update({k: v for k, v in args.items() if v is not None})
            else:
                self.logger.warning(f"Invalid args type: {type(args)}, expected Namespace or dict")
        
        # Validate the configuration
        self.validate_config()
    
    def _load_defaults(self):
        """Load default configuration values."""
        self.config.update(self.defaults)
        self.logger.debug("Default configuration loaded")
    
    def load_from_args(self) -> Dict[str, Any]:
        """
        Process command-line arguments.
        
        Returns:
            Updated configuration dictionary
        """
        parser = argparse.ArgumentParser(description='BLE API Testing Tool')
        
        # OpenAPI specification
        parser.add_argument('--spec-file', required=True, help='Path to OpenAPI specification file')
        
        # Base URLs
        parser.add_argument('--base-url', required=True, help='Base URL for API requests')
        parser.add_argument('--websocket-url', help='Base URL for WebSocket connections')
        
        # Authentication
        parser.add_argument('--api-key', help='API key for authentication')
        parser.add_argument('--auth-token', help='Authentication token')
        parser.add_argument('--auth-type', default='Bearer', help='Authentication type (Bearer, Basic, etc.)')
        
        # Test settings
        parser.add_argument('--timeout', type=int, default=self.defaults['timeout'], 
                          help=f"Request timeout in seconds (default: {self.defaults['timeout']})")
        parser.add_argument('--retries', type=int, default=self.defaults['retries'], 
                          help=f"Number of retries for failed requests (default: {self.defaults['retries']})")
        parser.add_argument('--retry-delay', type=float, default=1.0,
                          help="Delay between retries in seconds (default: 1.0)")
        parser.add_argument('--concurrency', type=int, default=self.defaults['concurrency'], 
                          help=f"Number of concurrent API requests (default: {self.defaults['concurrency']})")
        
        # Output settings
        parser.add_argument('--format', choices=['json', 'csv', 'text', 'html'], 
                          default=self.defaults['format'], 
                          help=f"Output format for test results (default: {self.defaults['format']})")
        parser.add_argument('--output', help='Path to output file')
        parser.add_argument('--log-level', choices=['debug', 'info', 'warning', 'error'], 
                          default=self.defaults['log_level'], 
                          help=f"Logging level (default: {self.defaults['log_level']})")
        parser.add_argument('--log-file', help='Path to log file')
        
        # Config file
        parser.add_argument('--config-file', help='Path to configuration file (JSON or YAML)')
        
        # Parse the arguments
        try:
            args = parser.parse_args()
            
            # If config file specified in args, load it first
            if args.config_file:
                try:
                    self.load_from_file(args.config_file)
                except Exception as e:
                    self.logger.error(f"Failed to load config file: {str(e)}")
            
            # Update the configuration with args (overriding other sources)
            self.config.update({k: v for k, v in vars(args).items() if v is not None})
            self.logger.info("Command-line arguments processed")
            
            # Validate after update
            self.validate_config()
            
            return self.config
        except Exception as e:
            self.logger.error(f"Error processing command-line arguments: {str(e)}")
            raise
    
    def load_from_env(self) -> Dict[str, Any]:
        """
        Load configuration from environment variables.
        
        Returns:
            Updated configuration dictionary
        """
        env_mappings = {
            'BLE_SPEC_FILE': 'spec_file',
            'BLE_BASE_URL': 'base_url',
            'BLE_WEBSOCKET_URL': 'websocket_url',
            'BLE_API_KEY': 'api_key',
            'BLE_AUTH_TOKEN': 'auth_token',
            'BLE_AUTH_TYPE': 'auth_type',
            'BLE_TIMEOUT': 'timeout',
            'BLE_RETRIES': 'retries',
            'BLE_RETRY_DELAY': 'retry_delay',
            'BLE_CONCURRENCY': 'concurrency',
            'BLE_FORMAT': 'format',
            'BLE_OUTPUT': 'output',
            'BLE_LOG_LEVEL': 'log_level',
            'BLE_LOG_FILE': 'log_file'
        }
        
        try:
            for env_var, config_key in env_mappings.items():
                if env_var in os.environ:
                    value = os.environ[env_var]
                    
                    # Convert numeric values
                    if config_key in ['timeout', 'retries', 'concurrency']:
                        try:
                            value = int(value)
                            if value < 0:
                                self.logger.warning(f"Invalid negative value for {env_var}: {value}, using default")
                                value = self.defaults.get(config_key, 0)
                        except ValueError:
                            self.logger.warning(f"Failed to convert {env_var} to integer, using default")
                            value = self.defaults.get(config_key, 0)
                    elif config_key == 'retry_delay':
                        try:
                            value = float(value)
                            if value < 0:
                                self.logger.warning(f"Invalid negative value for {env_var}: {value}, using default")
                                value = 1.0
                        except ValueError:
                            self.logger.warning(f"Failed to convert {env_var} to float, using default")
                            value = 1.0
                    
                    self.config[config_key] = value
            
            self.logger.info("Environment variables processed")
            return self.config
        except Exception as e:
            self.logger.error(f"Error processing environment variables: {str(e)}")
            raise
    
    def load_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Load configuration from a JSON or YAML file.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            Updated configuration dictionary
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file format is invalid
        """
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"Configuration file not found: {file_path}")
            
            self.logger.info(f"Loading configuration from {file_path}")
            
            if path.suffix.lower() in ['.yaml', '.yml']:
                with open(path, 'r') as f:
                    file_config = yaml.safe_load(f)
            elif path.suffix.lower() == '.json':
                with open(path, 'r') as f:
                    file_config = json.load(f)
            else:
                raise ValueError(f"Unsupported configuration file format: {path.suffix}")
            
            if not isinstance(file_config, dict):
                raise ValueError(f"Invalid configuration format: expected dict, got {type(file_config)}")
            
            # Update configuration
            self.config.update(file_config)
            self.logger.info(f"Configuration loaded from {file_path}")
            return self.config
            
        except Exception as e:
            self.logger.error(f"Error loading configuration from file: {str(e)}")
            raise
    
    def validate_config(self) -> bool:
        """
        Validate the current configuration.
        
        Returns:
            True if valid, False otherwise
            
        Raises:
            ValueError: If configuration is invalid
        """
        errors = []
        
        # Check required fields
        if self.config.get('spec_file') is None:
            errors.append("Missing required configuration: spec_file")
        elif not Path(self.config['spec_file']).exists():
            errors.append(f"Specification file not found: {self.config['spec_file']}")
            
        if self.config.get('base_url') is None:
            errors.append("Missing required configuration: base_url")
        else:
            # Validate base URL format
            try:
                parsed = urlparse(self.config['base_url'])
                if not parsed.scheme or not parsed.netloc:
                    errors.append(f"Invalid base URL format: {self.config['base_url']}")
                if parsed.scheme not in ['http', 'https']:
                    errors.append(f"Unsupported protocol in base URL: {parsed.scheme}")
            except Exception as e:
                errors.append(f"Invalid base URL: {str(e)}")
        
        # Validate WebSocket URL if provided
        if self.config.get('websocket_url'):
            try:
                parsed = urlparse(self.config['websocket_url'])
                if not parsed.scheme or not parsed.netloc:
                    errors.append(f"Invalid WebSocket URL format: {self.config['websocket_url']}")
                if parsed.scheme not in ['ws', 'wss']:
                    errors.append(f"Unsupported protocol in WebSocket URL: {parsed.scheme}")
            except Exception as e:
                errors.append(f"Invalid WebSocket URL: {str(e)}")
        
        # Validate numeric values
        for key, min_val in [('timeout', 1), ('retries', 0), ('concurrency', 1)]:
            if key in self.config:
                try:
                    val = int(self.config[key])
                    if val < min_val:
                        errors.append(f"{key} must be at least {min_val}, got {val}")
                except (ValueError, TypeError):
                    errors.append(f"{key} must be an integer, got {self.config[key]}")
        
        # Validate retry_delay
        if 'retry_delay' in self.config:
            try:
                val = float(self.config['retry_delay'])
                if val < 0:
                    errors.append(f"retry_delay must be non-negative, got {val}")
            except (ValueError, TypeError):
                errors.append(f"retry_delay must be a number, got {self.config['retry_delay']}")
        
        # Validate format
        if self.config.get('format') not in ['json', 'csv', 'text', 'html']:
            errors.append(f"Unsupported output format: {self.config.get('format')}")
        
        # Validate log level
        if self.config.get('log_level') not in ['debug', 'info', 'warning', 'error']:
            errors.append(f"Unsupported log level: {self.config.get('log_level')}")
        
        # If output file is specified, check if the directory exists
        if self.config.get('output'):
            output_path = Path(self.config['output'])
            if not output_path.parent.exists():
                errors.append(f"Output directory does not exist: {output_path.parent}")
        
        # If log file is specified, check if the directory exists
        if self.config.get('log_file'):
            log_path = Path(self.config['log_file'])
            if not log_path.parent.exists():
                errors.append(f"Log directory does not exist: {log_path.parent}")
        
        if errors:
            for error in errors:
                self.logger.error(error)
            raise ValueError("Configuration validation failed:\n" + "\n".join(errors))
        
        self.logger.debug("Configuration validation successful")
        return True
    
    def get_base_url(self) -> str:
        """
        Return the base URL for API requests.
        
        Returns:
            Base URL string
            
        Raises:
            ValueError: If base URL is not configured
        """
        base_url = self.config.get('base_url')
        if not base_url:
            self.logger.error("Base URL not configured")
            raise ValueError("Base URL not configured")
        return base_url
    
    def get_websocket_url(self) -> str:
        """
        Return the WebSocket URL, fallback to base URL if not specified.
        
        Returns:
            WebSocket URL string
            
        Raises:
            ValueError: If neither WebSocket URL nor base URL is configured
        """
        ws_url = self.config.get('websocket_url')
        if not ws_url:
            base_url = self.get_base_url()
            if not base_url:
                self.logger.error("Neither WebSocket URL nor base URL is configured")
                raise ValueError("WebSocket URL not configured and cannot be derived")
            
            # Convert http(s) to ws(s) while preserving path and query
            try:
                parsed = urlparse(base_url)
                # Determine the new scheme
                new_scheme = 'wss' if parsed.scheme == 'https' else 'ws'
                # Reconstruct the URL with the new scheme
                ws_url = parsed._replace(scheme=new_scheme).geturl()
                self.logger.debug(f"Converted {base_url} to WebSocket URL: {ws_url}")
            except Exception as e:
                self.logger.error(f"Failed to convert base URL to WebSocket URL: {str(e)}")
                raise ValueError(f"Failed to convert base URL to WebSocket URL: {str(e)}")
                
        return ws_url
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Return authentication headers based on configured auth params.
        
        Returns:
            Dictionary of headers
        """
        headers = {}
        
        # Handle API key
        if 'api_key' in self.config and self.config['api_key']:
            headers['X-API-Key'] = self.config['api_key']
            
        # Handle auth token
        if 'auth_token' in self.config and self.config['auth_token']:
            auth_type = self.config.get('auth_type', 'Bearer')
            headers['Authorization'] = f"{auth_type} {self.config['auth_token']}"
            
        return headers
    
    def get_auth_params(self) -> Dict[str, Any]:
        """
        Return authentication parameters.
        
        Returns:
            Dictionary of auth parameters
        """
        auth = {}
        
        if 'api_key' in self.config and self.config['api_key']:
            auth['api_key'] = self.config['api_key']
            
        if 'auth_token' in self.config and self.config['auth_token']:
            auth['auth_token'] = self.config['auth_token']
            auth['auth_type'] = self.config.get('auth_type', 'Bearer')
            
        return auth
    
    def get_test_timeout(self) -> int:
        """
        Return request timeout setting.
        
        Returns:
            Timeout in seconds
        """
        try:
            timeout = int(self.config.get('timeout', self.defaults['timeout']))
            return max(1, timeout)  # Ensure minimum timeout of 1 second
        except (ValueError, TypeError):
            self.logger.warning(f"Invalid timeout value: {self.config.get('timeout')}, using default")
            return self.defaults['timeout']
    
    def get_retry_count(self) -> int:
        """
        Return the number of retries for failed requests.
        
        Returns:
            Retry count
        """
        try:
            retries = int(self.config.get('retries', self.defaults['retries']))
            return max(0, retries)  # Ensure non-negative
        except (ValueError, TypeError):
            self.logger.warning(f"Invalid retries value: {self.config.get('retries')}, using default")
            return self.defaults['retries']
    
    def get_retry_delay(self) -> float:
        """
        Return the delay between retries.
        
        Returns:
            Retry delay in seconds
        """
        try:
            delay = float(self.config.get('retry_delay', 1.0))
            return max(0, delay)  # Ensure non-negative
        except (ValueError, TypeError):
            self.logger.warning(f"Invalid retry_delay value: {self.config.get('retry_delay')}, using default")
            return 1.0
    
    def get_test_concurrency(self) -> int:
        """
        Return concurrency level for API testing.
        
        Returns:
            Concurrency level
        """
        try:
            concurrency = int(self.config.get('concurrency', self.defaults['concurrency']))
            return max(1, concurrency)  # Ensure minimum of 1
        except (ValueError, TypeError):
            self.logger.warning(f"Invalid concurrency value: {self.config.get('concurrency')}, using default")
            return self.defaults['concurrency']
    
    def get_output_format(self) -> str:
        """
        Return the output format for test results.
        
        Returns:
            Output format string
        """
        format_val = self.config.get('format', self.defaults['format'])
        if format_val not in ['json', 'csv', 'text', 'html']:
            self.logger.warning(f"Invalid output format: {format_val}, using default")
            return self.defaults['format']
        return format_val
    
    def get_output_file(self) -> Optional[str]:
        """
        Return the output file path.
        
        Returns:
            Output file path or None
        """
        return self.config.get('output')
    
    def set_config_value(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self.config[key] = value
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key is not found
            
        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)
    
    def get_config(self) -> Dict[str, Any]:
        """
        Return the complete configuration dictionary.
        
        Returns:
            Configuration dictionary
        """
        return self.config.copy()