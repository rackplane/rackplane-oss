# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Base Plugin Classes

Defines the abstract base classes for all plugin types:
- IntegrationPlugin: For external system integrations (NetBox, Epic, SAP)
- FeaturePlugin: For vertical-specific features (expiration tracking, par levels)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum


class PluginType(str, Enum):
    """Types of plugins supported by RackPlane"""
    INTEGRATION = "integration"  # External system integrations
    FEATURE = "feature"          # Vertical-specific feature modules


class PluginStatus(str, Enum):
    """Plugin activation status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    CONFIGURING = "configuring"


class BasePlugin(ABC):
    """
    Abstract base class for all RackPlane plugins.
    
    Attributes:
        plugin_name: Unique identifier for the plugin (e.g., 'netbox', 'epic')
        plugin_type: Type of plugin (integration or feature)
        plugin_version: Semver version string
        display_name: Human-readable name for UI
        description: Description of what the plugin does
        vertical_packs: List of verticals this plugin applies to
        required_features: List of feature flags required to use this plugin
    """
    
    plugin_name: str
    plugin_type: PluginType
    plugin_version: str
    display_name: str
    description: str
    vertical_packs: List[str] = []
    required_features: List[str] = []
    
    @abstractmethod
    def get_config_schema(self) -> Dict[str, Any]:
        """
        Return JSON Schema for plugin configuration.
        
        This schema is used to validate configuration and generate
        configuration UI in the admin panel.
        
        Returns:
            JSON Schema dict defining configuration options
        """
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate plugin configuration.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass
    
    def on_enable(self, tenant_id: int, config: Dict[str, Any]) -> None:
        """Called when plugin is enabled for a tenant"""
        pass
    
    def on_disable(self, tenant_id: int) -> None:
        """Called when plugin is disabled for a tenant"""
        pass


class IntegrationPlugin(BasePlugin):
    """
    Base class for external system integration plugins.
    
    Integration plugins connect RackPlane to external systems like:
    - NetBox (datacenter infrastructure management)
    - Epic (healthcare EHR)
    - SAP (enterprise ERP)
    - Workday (HR/asset management)
    
    Each integration plugin must implement:
    - test_connection: Verify external system is reachable
    - sync_inbound: Pull data from external system
    - sync_outbound: Push data to external system (optional)
    """
    
    plugin_type = PluginType.INTEGRATION
    
    # Whether this integration supports bidirectional sync
    supports_bidirectional: bool = False
    
    # Rate limiting settings
    rate_limit_requests_per_minute: int = 60
    rate_limit_requests_per_day: int = 10000
    
    @abstractmethod
    def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test the integration connection.
        
        Args:
            config: Integration configuration with credentials
            
        Returns:
            Dict with keys:
                - success (bool): Whether connection succeeded
                - message (str): Status message
                - external_version (str): Version of external system (optional)
                - latency_ms (int): Response time in milliseconds (optional)
        """
        pass
    
    @abstractmethod
    def sync_inbound(
        self, 
        tenant_id: int, 
        config: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Pull data from external system into RackPlane.
        
        Args:
            tenant_id: Tenant to sync data for
            config: Integration configuration
            options: Sync options (e.g., full vs incremental, filters)
            
        Returns:
            Dict with keys:
                - success (bool): Whether sync succeeded
                - items_synced (int): Number of items synchronized
                - items_created (int): New items created
                - items_updated (int): Existing items updated
                - items_failed (int): Items that failed to sync
                - errors (list): List of error messages
                - duration_seconds (float): How long sync took
        """
        pass
    
    def sync_outbound(
        self, 
        tenant_id: int, 
        config: Dict[str, Any], 
        data: Any,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Push data from RackPlane to external system.
        
        Default implementation raises NotImplementedError if 
        supports_bidirectional is False.
        
        Args:
            tenant_id: Tenant to sync data for
            config: Integration configuration
            data: Data to push to external system
            options: Push options
            
        Returns:
            Dict with sync results (same format as sync_inbound)
        """
        if not self.supports_bidirectional:
            raise NotImplementedError(
                f"Plugin {self.plugin_name} does not support outbound sync"
            )
        raise NotImplementedError("Subclass must implement sync_outbound")
    
    def get_external_status(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get status information from external system.
        
        Returns:
            Dict with external system status
        """
        return self.test_connection(config)


class FeaturePlugin(BasePlugin):
    """
    Base class for vertical-specific feature plugins.
    
    Feature plugins add functionality specific to certain verticals:
    - Expiration tracking (healthcare, food service)
    - Par level alerts (healthcare, warehouse)
    - Lot/batch tracking (healthcare, manufacturing)
    - Department attribution (healthcare, enterprise)
    
    Each feature plugin must implement:
    - is_enabled_for_tenant: Check if feature is enabled
    - get_dashboard_widgets: Return widgets for dashboard
    - get_api_routes: Return additional API routes
    """
    
    plugin_type = PluginType.FEATURE
    
    # Feature flag key that controls this feature
    feature_flag_key: str = ""
    
    @abstractmethod
    def is_enabled_for_tenant(self, tenant_id: int) -> bool:
        """Check if this feature is enabled for a tenant"""
        pass
    
    def get_dashboard_widgets(self, tenant_id: int) -> List[Dict[str, Any]]:
        """
        Return dashboard widgets for this feature.
        
        Returns:
            List of widget definitions with:
                - id (str): Widget identifier
                - title (str): Widget title
                - component (str): Frontend component name
                - size (str): 'small', 'medium', 'large'
                - refresh_interval (int): Auto-refresh in seconds (0 for none)
        """
        return []
    
    def get_report_types(self, tenant_id: int) -> List[Dict[str, Any]]:
        """
        Return available report types for this feature.
        
        Returns:
            List of report definitions
        """
        return []
    
    def get_celery_tasks(self) -> List[Dict[str, Any]]:
        """
        Return Celery task definitions for this feature.
        
        Returns:
            List of task definitions with:
                - name (str): Task name
                - schedule (dict): Celery beat schedule
                - function (callable): Task function
        """
        return []
    
    def extend_asset_model(self) -> List[Dict[str, Any]]:
        """
        Return additional fields to add to Asset model.
        
        These are stored in custom_fields JSON column.
        
        Returns:
            List of field definitions
        """
        return []
