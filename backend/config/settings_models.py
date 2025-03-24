from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class SecuritySettings(BaseModel):
    """Security-related settings"""
    encryption_enabled: bool = True
    key_derivation_method: str = "PBKDF2"
    default_key_timeout: int = 3600
    
class DeviceSettings(BaseModel):
    """Device-related settings"""
    simulation_mode: bool = False
    device_discovery_interval: int = 60
    cache_device_info: bool = True
    
class LoggingSettings(BaseModel):
    """Logging-related settings"""
    log_level: str = "INFO"
    log_to_file: bool = True
    log_rotation: bool = True
    log_max_size: int = 10485760  # 10MB