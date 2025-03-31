"""BLE module configuration."""

BLE_CONFIG = {
    # General settings
    "use_mock_devices": False,
    "mock_device_count": 5,
    "debug_mode": False,  # Enable additional debug logging
    
    # Adapter management
    "adapter": {
        "auto_discover_on_startup": True,  # Discover adapters when BLE service starts
        "default_adapter": "auto",  # "auto" or specific adapter address
        "power_on_if_needed": True,  # Try to power on adapter if it's off
        "reset": {
            "auto_reset_on_errors": True,  # Automatically reset adapter on serious errors
            "restart_service": True,       # Restart Bluetooth service on reset
            "disconnect_devices": True,    # Disconnect devices on reset
            "rescan_after_reset": True     # Perform a scan after reset
        }
    },
    
    # Scanning settings
    "scanning": {
        "timeout": 5.0,                 # Default scan timeout in seconds
        "filter_duplicates": True,      # Filter duplicate scan results
        "interval": 0.1,                # Scan interval (platform-specific support)
        "window": 0.1,                  # Scan window (platform-specific support)
        "active": True,                 # Use active scanning
        "max_cached_devices": 100,      # Maximum number of devices to keep in cache
        "default_service_filters": []   # Default service UUIDs to filter by
    },
    
    # Connection settings
    "connection": {
        "timeout": 10.0,                # Connection timeout in seconds
        "retry_count": 3,               # Number of connection retries
        "retry_interval": 2.0,          # Seconds between retries
        "auto_reconnect": True,         # Auto-reconnect on unexpected disconnection
        "max_reconnect_attempts": 5,    # Maximum reconnection attempts
        "use_cached_services": True,    # Use cached services when available
        "remember_devices": True,       # Remember devices for future connections
        "disconnect_timeout": 5.0       # Timeout for disconnect operations
    },
    
    # Service management
    "service": {
        "discover_on_connect": True,    # Automatically discover services on connection
        "read_timeout": 5.0,            # Timeout for characteristic reads
        "write_timeout": 5.0,           # Timeout for characteristic writes
        "max_write_without_response_size": 512,  # Max size for write without response
        "service_descriptions_file": "service_descriptions.json",  # Custom service descriptions
        "characteristic_descriptions_file": "characteristic_descriptions.json"  # Custom char descriptions
    },
    
    # Notification management
    "notifications": {
        "max_history": 1000,            # Maximum notification history per characteristic
        "buffer_size": 100,             # Buffer size for notification processing
        "auto_subscribe_services": [],  # Service UUIDs to auto-subscribe on connection
        "auto_subscribe_characteristics": []  # Characteristic UUIDs to auto-subscribe
    },
    
    # Error handling and recovery
    "error_recovery": {
        "enabled": True,                 # Enable automatic error recovery
        "max_recovery_attempts": 3,      # Maximum recovery attempts per error
        "recovery_delay": 1.0,           # Delay before recovery attempt (seconds)
        "reset_adapter_on_critical": True,  # Reset adapter on critical errors
        "reconnect_on_disconnect": True,    # Try to reconnect on unexpected disconnection
        "aggressive_recovery": False        # Use aggressive recovery strategies
    },
    
    # WebSocket configuration
    "websocket": {
        "path": "/api/ble/ws",
        "enable_legacy_paths": True,     # For backward compatibility
        "max_connections": 10,           # Maximum concurrent WebSocket connections
        "heartbeat_interval": 30,        # Heartbeat interval in seconds
        "notification_buffering": True,  # Buffer notifications for new connections
        "authorization_required": False  # Require authorization for WebSocket connections
    },
    
    # Persistence
    "persistence": {
        "enabled": True,                 # Enable device persistence
        "storage_path": "ble_devices",   # Relative path for device storage
        "max_devices": 50,               # Maximum number of saved devices
        "save_services": True            # Save discovered services for devices
    },
    
    # Metrics and monitoring
    "metrics": {
        "enabled": True,                 # Enable metrics collection
        "log_metrics": True,             # Log metrics periodically
        "log_interval": 300,             # Metrics logging interval in seconds
        "max_entries": 1000,             # Maximum entries in metrics history
        "track_operation_times": True    # Track operation execution times
    },
    
    # Platform-specific settings
    "platform": {
        "windows": {
            "use_bluetooth_le_device": True,  # Use BluetoothLEDevice on Windows
            "prefer_winrt": True              # Prefer WinRT implementation when available
        },
        "linux": {
            "hci_device": "auto",            # HCI device to use ("auto" or e.g., "hci0")
            "bluez_experimental": False       # Use BlueZ experimental features
        },
        "macos": {
            "allow_restore": True,           # Allow restoration of central manager state
            "use_blueutil": True             # Use blueutil for adapter management if available
        }
    },
    
    # Custom behavior overrides (populated by user extensions)
    "custom": {}
}

# Helper function to get a specific configuration value
def get_config(key, default=None):
    """
    Get a specific configuration value using dot notation.
    
    Example:
    get_config("connection.timeout", 5.0)
    
    Args:
        key: Dot-notation key
        default: Default value if key not found
        
    Returns:
        Configuration value or default
    """
    parts = key.split('.')
    config = BLE_CONFIG
    
    for part in parts:
        if part not in config:
            return default
        config = config[part]
    
    return config

# Load environment-specific overrides
def load_env_config():
    """Load environment-specific configuration overrides."""
    import os
    import json
    
    # Environment variable can point to a JSON config file
    env_config = os.environ.get('BLE_CONFIG_FILE')
    if env_config and os.path.isfile(env_config):
        try:
            with open(env_config, 'r') as f:
                overrides = json.load(f)
                
            # Deep merge the overrides
            _merge_config(BLE_CONFIG, overrides)
        except Exception as e:
            print(f"Error loading environment config: {e}")

def _merge_config(base, overrides):
    """Deep merge configuration dictionaries."""
    for key, value in overrides.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _merge_config(base[key], value)
        else:
            base[key] = value

# Load environment configuration on import
load_env_config()