from typing import Dict, Callable, Awaitable, Optional, List
import logging
import asyncio

logger = logging.getLogger("service_registry")

class ServiceRegistry:
    """Registry to track available services and their health."""
    
    def __init__(self):
        self.services = {}
        self.health_checks = {}
        self.service_status = {}
    
    def register_service(self, name: str, service_instance, 
                         health_check: Optional[Callable[[], Awaitable[bool]]] = None):
        """Register a service with optional health check."""
        self.services[name] = service_instance
        if health_check:
            self.health_checks[name] = health_check
        self.service_status[name] = True  # Assume services start healthy
        logger.info(f"Service '{name}' registered")
    
    def is_service_available(self, name: str) -> bool:
        """Check if a service is available and healthy."""
        return name in self.services and self.service_status.get(name, False)
    
    def get_service(self, name: str, default=None):
        """Get a service if it's available, otherwise return default."""
        if self.is_service_available(name):
            return self.services[name]
        logger.warning(f"Attempted to access unavailable service: {name}")
        return default
    
    async def run_health_checks(self):
        """Run health checks for all registered services."""
        for name, check in self.health_checks.items():
            try:
                is_healthy = await check()
                if not is_healthy and self.service_status.get(name, False):
                    logger.warning(f"Service '{name}' is now unhealthy")
                elif is_healthy and not self.service_status.get(name, True):
                    logger.info(f"Service '{name}' is now healthy")
                self.service_status[name] = is_healthy
            except Exception as e:
                logger.error(f"Health check for '{name}' failed: {str(e)}")
                self.service_status[name] = False
    
    def get_unhealthy_services(self) -> List[str]:
        """Get names of all unhealthy services."""
        return [name for name, status in self.service_status.items() if not status]
    
    async def start_health_check_loop(self, interval_seconds=60):
        """Start periodic health checks."""
        while True:
            await self.run_health_checks()
            await asyncio.sleep(interval_seconds)

# Global service registry instance
service_registry = ServiceRegistry()