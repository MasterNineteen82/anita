from typing import Dict, Set
import logging

logger = logging.getLogger("feature_flags")

class FeatureFlags:
    """Simple feature flag system to enable/disable features."""
    
    def __init__(self):
        self.disabled_features = set()
        self.feature_dependencies = {}
    
    def disable_feature(self, feature_name: str):
        """Disable a specific feature."""
        self.disabled_features.add(feature_name)
        logger.info(f"Feature '{feature_name}' has been disabled")
        
        # Disable dependent features
        if feature_name in self.feature_dependencies:
            for dependent in self.feature_dependencies[feature_name]:
                self.disable_feature(dependent)
    
    def enable_feature(self, feature_name: str):
        """Enable a specific feature."""
        if feature_name in self.disabled_features:
            self.disabled_features.remove(feature_name)
            logger.info(f"Feature '{feature_name}' has been enabled")
    
    def is_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled."""
        return feature_name not in self.disabled_features
    
    def register_dependency(self, feature_name: str, depends_on: str):
        """Register that one feature depends on another."""
        if depends_on not in self.feature_dependencies:
            self.feature_dependencies[depends_on] = set()
        self.feature_dependencies[depends_on].add(feature_name)
        logger.info(f"Registered dependency: '{feature_name}' depends on '{depends_on}'")

# Global feature flags instance
feature_flags = FeatureFlags()

# Register BLE features
feature_flags.register_dependency("ble_connect", "ble_scan")
feature_flags.register_dependency("ble_services", "ble_connect")
feature_flags.register_dependency("ble_characteristics", "ble_services")
feature_flags.register_dependency("ble_notify", "ble_characteristics")