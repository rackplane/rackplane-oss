# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Plugin Registry

Central registry for all RackPlane plugins. Handles:
- Plugin registration and discovery
- Plugin lookup by name or vertical
- Tenant-specific plugin enablement state
- Plugin configuration storage and retrieval
"""

from typing import Dict, Type, List, Optional, Any
import logging
from typing import Dict, Type, List, Optional, Any, Union
import logging
import json
import base64
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session
from app.core.config import settings

from app.plugins.base import (
    BasePlugin, 
    IntegrationPlugin, 
    FeaturePlugin, 
    PluginType,
    PluginStatus
)

logger = logging.getLogger(__name__)


class PluginRegistry:
    """
    Central registry for all RackPlane plugins.
    
    This is a singleton that maintains the global plugin registry.
    Plugins are registered at application startup and can be queried
    by name, type, or vertical pack.
    
    Usage:
        # Register a plugin (usually done in plugin's __init__.py)
        PluginRegistry.register(NetBoxPlugin)
        
        # Get all plugins for a vertical
        plugins = PluginRegistry.list_for_vertical('healthcare')
        
        # Get a specific plugin
        plugin = PluginRegistry.get('netbox')
        if plugin:
            instance = plugin()  # Create instance
            result = instance.test_connection(config)
    """
    
    # Registry storage (class-level singletons)
    _plugins: Dict[str, Type[BasePlugin]] = {}
    _instances: Dict[str, BasePlugin] = {}
    
    @classmethod
    def register(cls, plugin_class: Type[BasePlugin]) -> None:
        """
        Register a plugin class with the registry.
        
        Args:
            plugin_class: Plugin class to register
            
        Raises:
            ValueError: If plugin_name is missing or already registered
        """
        if not hasattr(plugin_class, 'plugin_name') or not plugin_class.plugin_name:
            raise ValueError(f"Plugin class {plugin_class} missing plugin_name")
        
        name = plugin_class.plugin_name
        
        if name in cls._plugins:
            logger.warning(f"Plugin '{name}' already registered, overwriting")
        
        cls._plugins[name] = plugin_class
        logger.info(
            f"Registered plugin: {name} v{plugin_class.plugin_version} "
            f"({plugin_class.plugin_type.value})"
        )
    
    @classmethod
    def unregister(cls, plugin_name: str) -> bool:
        """
        Remove a plugin from the registry.
        
        Args:
            plugin_name: Name of plugin to remove
            
        Returns:
            True if plugin was removed, False if not found
        """
        if plugin_name in cls._plugins:
            del cls._plugins[plugin_name]
            if plugin_name in cls._instances:
                del cls._instances[plugin_name]
            logger.info(f"Unregistered plugin: {plugin_name}")
            return True
        return False
    
    @classmethod
    def get(cls, plugin_name: str) -> Optional[Type[BasePlugin]]:
        """
        Get a plugin class by name.
        
        Args:
            plugin_name: Unique plugin identifier
            
        Returns:
            Plugin class or None if not found
        """
        return cls._plugins.get(plugin_name)
    
    @classmethod
    def get_instance(cls, plugin_name: str) -> Optional[BasePlugin]:
        """
        Get or create a singleton plugin instance.
        
        Args:
            plugin_name: Unique plugin identifier
            
        Returns:
            Plugin instance or None if not found
        """
        if plugin_name not in cls._instances:
            plugin_class = cls._plugins.get(plugin_name)
            if plugin_class:
                cls._instances[plugin_name] = plugin_class()
        
        return cls._instances.get(plugin_name)
    
    @classmethod
    def list_all(cls) -> List[Dict[str, Any]]:
        """
        List all registered plugins.
        
        Returns:
            List of plugin metadata dicts
        """
        return [
            {
                'name': p.plugin_name,
                'type': p.plugin_type.value,
                'version': p.plugin_version,
                'display_name': getattr(p, 'display_name', p.plugin_name),
                'description': getattr(p, 'description', ''),
                'vertical_packs': p.vertical_packs,
            }
            for p in cls._plugins.values()
        ]
    
    @classmethod
    def list_by_type(cls, plugin_type: PluginType) -> List[Type[BasePlugin]]:
        """
        List plugins by type.
        
        Args:
            plugin_type: Type of plugins to list
            
        Returns:
            List of plugin classes matching type
        """
        return [
            p for p in cls._plugins.values()
            if p.plugin_type == plugin_type
        ]
    
    @classmethod
    def list_integrations(cls) -> List[Type[IntegrationPlugin]]:
        """List all integration plugins"""
        return cls.list_by_type(PluginType.INTEGRATION)
    
    @classmethod
    def list_features(cls) -> List[Type[FeaturePlugin]]:
        """List all feature plugins"""
        return cls.list_by_type(PluginType.FEATURE)
    
    @classmethod
    def list_for_vertical(cls, vertical: str) -> List[Type[BasePlugin]]:
        """
        List plugins applicable to a specific vertical.
        
        Args:
            vertical: Vertical pack name (e.g., 'healthcare', 'datacenter')
            
        Returns:
            List of plugin classes that support this vertical
        """
        return [
            p for p in cls._plugins.values()
            if not p.vertical_packs or vertical in p.vertical_packs
        ]
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered plugins. Mainly for testing."""
        cls._plugins.clear()
        cls._instances.clear()
        logger.info("Cleared plugin registry")


class TenantPluginConfig:
    """
    Manages plugin configuration and enablement for tenants.
    
    This class handles:
    - Storing plugin configurations per tenant
    - Enabling/disabling plugins for tenants
    - Retrieving plugin status for tenants
    """
    
    
    @staticmethod
    def _get_cipher_suite():
        """Get encryption cipher suite."""
        # Derive key from SECRET_KEY (must be 32 base64-encoded bytes)
        key = settings.SECRET_KEY
        # Ensure we have a valid key for Fernet
        if len(key) < 32:
            key = key.ljust(32, '0')
        elif len(key) > 32:
            key = key[:32]
        
        encoded_key = base64.urlsafe_b64encode(key.encode())
        return Fernet(encoded_key)

    @staticmethod
    def _encrypt_config(config: Dict[str, Any]) -> str:
        """Encrypt configuration dictionary."""
        try:
            cipher = TenantPluginConfig._get_cipher_suite()
            json_data = json.dumps(config)
            return cipher.encrypt(json_data.encode()).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    @staticmethod
    def _decrypt_config(encrypted_config: Union[str, Dict]) -> Dict[str, Any]:
        """Decrypt configuration string."""
        if isinstance(encrypted_config, dict):
            return encrypted_config
            
        try:
            cipher = TenantPluginConfig._get_cipher_suite()
            decrypted_data = cipher.decrypt(encrypted_config.encode()).decode()
            return json.loads(decrypted_data)
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return {}

    @staticmethod
    def get_enabled_plugins(db: Session, tenant_id: int) -> List[Dict[str, Any]]:
        """
        Get list of enabled plugins for a tenant.
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            
        Returns:
            List of enabled plugin configurations
        """
        from app.models.tenant import Tenant
        
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            return []
        
        # Plugin configs stored in tenant.plugin_config
        # Fallback to branding_config for backward compatibility during migration
        if hasattr(tenant, 'plugin_config') and tenant.plugin_config:
            config = tenant.plugin_config
            plugins = config.get('plugins', [])
            # Decrypt configs on the fly
            for p in plugins:
                if 'config' in p:
                    p['config'] = TenantPluginConfig._decrypt_config(p['config'])
            return plugins
            
        # Fallback check (deprecated)
        branding = tenant.branding_config or {}
        plugins = branding.get('plugins', [])
        # Decrypt configs if present in fallback (unlikely but safe)
        for p in plugins:
            if 'config' in p:
                p['config'] = TenantPluginConfig._decrypt_config(p['config'])
        return plugins
    
    @staticmethod
    def is_plugin_enabled(
        db: Session, 
        tenant_id: int, 
        plugin_name: str
    ) -> bool:
        """Check if a specific plugin is enabled for a tenant"""
        plugins = TenantPluginConfig.get_enabled_plugins(db, tenant_id)
        return any(p.get('name') == plugin_name and p.get('enabled', False) 
                   for p in plugins)
    
    @staticmethod
    def get_plugin_config(
        db: Session, 
        tenant_id: int, 
        plugin_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific plugin for a tenant"""
        plugins = TenantPluginConfig.get_enabled_plugins(db, tenant_id)
        for p in plugins:
            if p.get('name') == plugin_name:
                return p.get('config', {})
        return None
    
    @staticmethod
    def enable_plugin(
        db: Session,
        tenant_id: int,
        plugin_name: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enable a plugin for a tenant.
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            plugin_name: Plugin to enable
            config: Plugin configuration
            
        Returns:
            Result dict with success status
        """
        from app.models.tenant import Tenant
        
        # Validate plugin exists
        plugin_class = PluginRegistry.get(plugin_name)
        if not plugin_class:
            return {'success': False, 'error': f'Plugin {plugin_name} not found'}
        
        # Validate configuration
        plugin = plugin_class()
        is_valid, error = plugin.validate_config(config)
        if not is_valid:
            return {'success': False, 'error': error}
        
        # Update tenant configuration
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            return {'success': False, 'error': 'Tenant not found'}
        
        # Use plugin_config, initialize if needed
        if not tenant.plugin_config:
            tenant.plugin_config = {'plugins': []}
            
        # Deep copy to ensure SQLAlchemy detects change
        plugin_config = dict(tenant.plugin_config)
        plugins = plugin_config.get('plugins', [])
        
        # Remove existing config for this plugin
        plugins = [p for p in plugins if p.get('name') != plugin_name]
        
        # Add new config
        # Encrypt the config before storing
        try:
            encrypted_config = TenantPluginConfig._encrypt_config(config)
        except Exception:
            return {'success': False, 'error': 'Failed to secure configuration'}
        
        plugins.append({
            'name': plugin_name,
            'enabled': True,
            'config': encrypted_config,
            'status': PluginStatus.ACTIVE.value
        })
        
        plugin_config['plugins'] = plugins
        tenant.plugin_config = plugin_config
        
        # Also clean up from branding_config if present (migration)
        if tenant.branding_config and 'plugins' in tenant.branding_config:
            branding = dict(tenant.branding_config)
            if 'plugins' in branding:
                del branding['plugins']
                tenant.branding_config = branding
        
        # Call plugin's on_enable hook
        try:
            plugin.on_enable(tenant_id, config)
        except Exception as e:
            logger.error(f"Error in plugin on_enable hook for {plugin_name}: {str(e)}")
            # Still save config but mark as error
            plugins[-1]['status'] = PluginStatus.ERROR.value
            # Generic error for DB to prevent secret leakage
            plugins[-1]['error'] = "Plugin initialization failed. Check server logs for details."
            # Re-save with error status
            plugin_config['plugins'] = plugins
            tenant.plugin_config = plugin_config
        
        db.commit()
        
        return {'success': True, 'plugin': plugin_name, 'status': 'enabled'}
    
    @staticmethod
    def disable_plugin(
        db: Session,
        tenant_id: int,
        plugin_name: str
    ) -> Dict[str, Any]:
        """
        Disable a plugin for a tenant.
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            plugin_name: Plugin to disable
            
        Returns:
            Result dict with success status
        """
        from app.models.tenant import Tenant
        
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            return {'success': False, 'error': 'Tenant not found'}
        
        if not tenant.plugin_config:
            return {'success': False, 'error': f'Plugin {plugin_name} not configured'}
            
        plugin_config = dict(tenant.plugin_config)
        plugins = plugin_config.get('plugins', [])
        
        # Find and disable plugin
        found = False
        for p in plugins:
            if p.get('name') == plugin_name:
                p['enabled'] = False
                p['status'] = PluginStatus.INACTIVE.value
                found = True
                
                # Call plugin's on_disable hook
                plugin_class = PluginRegistry.get(plugin_name)
                if plugin_class:
                    try:
                        plugin_class().on_disable(tenant_id)
                    except Exception as e:
                        logger.error(f"Error in plugin on_disable hook: {e}")
                
                break
        
        if found:
            plugin_config['plugins'] = plugins
            tenant.plugin_config = plugin_config
            db.commit()
            return {'success': True, 'plugin': plugin_name, 'status': 'disabled'}
        
        return {'success': False, 'error': f'Plugin {plugin_name} not configured'}


def discover_plugins() -> None:
    """
    Discover and register all available plugins.
    
    This function is called at application startup to auto-discover
    plugins from the plugins/integrations and plugins/features directories.
    """
    # Import and register integration plugins
    try:
        from app.plugins.integrations.netbox.plugin import NetBoxPlugin
        if 'netbox' not in PluginRegistry._plugins:
            PluginRegistry.register(NetBoxPlugin)
        logger.info("Loaded NetBox integration plugin")
    except ImportError as e:
        logger.warning(f"Could not load NetBox plugin: {e}")
    
    # Import and register feature plugins
    try:
        from app.plugins.features.expiration_tracking import ExpirationTrackingPlugin
        if 'expiration_tracking' not in PluginRegistry._plugins:
            PluginRegistry.register(ExpirationTrackingPlugin)
        logger.info("Loaded expiration tracking feature plugin")
    except ImportError as e:
        logger.warning(f"Could not load expiration tracking plugin: {e}")
    
    try:
        from app.plugins.features.par_levels import ParLevelPlugin
        if 'par_levels' not in PluginRegistry._plugins:
            PluginRegistry.register(ParLevelPlugin)
        logger.info("Loaded par levels feature plugin")
    except ImportError as e:
        logger.warning(f"Could not load par levels plugin: {e}")
    
    # Future: Add dynamic plugin discovery from a plugins directory
    # for path in Path('app/plugins/integrations').glob('*/plugin.py'):
    #     module = importlib.import_module(str(path))
    
    logger.info(f"Plugin discovery complete. {len(PluginRegistry._plugins)} plugins loaded.")


