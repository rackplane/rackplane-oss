# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Plugin Management API

Endpoints for managing plugins:
- List available plugins
- Get plugin configuration
- Enable/disable plugins for tenants
- Test plugin connections
- Trigger plugin syncs
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user, get_current_tenant_admin
from app.models.user import User
from app.plugins.registry import PluginRegistry, TenantPluginConfig, discover_plugins
from app.plugins.base import PluginType

router = APIRouter(prefix="/plugins", tags=["plugins"])


# Schemas
class PluginInfo(BaseModel):
    """Plugin metadata"""
    name: str
    type: str
    version: str
    display_name: str
    description: str
    vertical_packs: List[str]
    
    class Config:
        from_attributes = True


class PluginConfigSchema(BaseModel):
    """Plugin configuration schema"""
    name: str
    config_schema: dict
    current_config: Optional[dict] = None
    is_enabled: bool = False
    status: Optional[str] = None


class EnablePluginRequest(BaseModel):
    """Request to enable a plugin"""
    plugin_name: str
    config: dict = Field(default_factory=dict)


class PluginSyncRequest(BaseModel):
    """Request to trigger a plugin sync"""
    plugin_name: str
    direction: str = Field(default="inbound", pattern="^(inbound|outbound|bidirectional)$")
    options: dict = Field(default_factory=dict)


class PluginTestResult(BaseModel):
    """Result of plugin connection test"""
    success: bool
    message: str
    external_version: Optional[str] = None
    latency_ms: Optional[int] = None


class PluginSyncResult(BaseModel):
    """Result of plugin sync operation"""
    success: bool
    items_synced: int = 0
    items_created: int = 0
    items_updated: int = 0
    items_failed: int = 0
    errors: List[str] = []
    duration_seconds: float = 0


# Endpoints

@router.get("/", response_model=List[PluginInfo])
def list_plugins(
    vertical: Optional[str] = None,
    plugin_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    List all available plugins.
    
    Optionally filter by:
    - vertical: Only show plugins for a specific vertical pack
    - plugin_type: Only show 'integration' or 'feature' plugins
    """
    # Ensure plugins are discovered
    if not PluginRegistry._plugins:
        discover_plugins()
    
    plugins = PluginRegistry.list_all()
    
    # Filter by vertical if specified
    if vertical:
        plugins = [p for p in plugins if not p['vertical_packs'] or vertical in p['vertical_packs']]
    
    # Filter by type if specified
    if plugin_type:
        plugins = [p for p in plugins if p['type'] == plugin_type]
    
    return plugins


@router.get("/for-tenant", response_model=List[PluginInfo])
def list_plugins_for_tenant(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List plugins available for the current tenant's vertical pack.
    
    This filters plugins to only show ones relevant to the tenant's
    configured vertical (datacenter, healthcare, warehouse).
    """
    from app.models.tenant import Tenant
    
    if not PluginRegistry._plugins:
        discover_plugins()
    
    # Get tenant's vertical pack
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    vertical = tenant.vertical_pack if tenant else "datacenter"
    
    plugins = PluginRegistry.list_for_vertical(vertical)
    
    return [
        {
            'name': p.plugin_name,
            'type': p.plugin_type.value,
            'version': p.plugin_version,
            'display_name': getattr(p, 'display_name', p.plugin_name),
            'description': getattr(p, 'description', ''),
            'vertical_packs': p.vertical_packs,
        }
        for p in plugins
    ]


@router.get("/{plugin_name}", response_model=PluginConfigSchema)
def get_plugin_config(
    plugin_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get configuration schema and current config for a plugin.
    """
    if not PluginRegistry._plugins:
        discover_plugins()
    
    plugin_class = PluginRegistry.get(plugin_name)
    if not plugin_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{plugin_name}' not found"
        )
    
    plugin = plugin_class()
    
    # Get current config for tenant
    current_config = TenantPluginConfig.get_plugin_config(
        db, current_user.tenant_id, plugin_name
    )
    is_enabled = TenantPluginConfig.is_plugin_enabled(
        db, current_user.tenant_id, plugin_name
    )
    
    return PluginConfigSchema(
        name=plugin_name,
        config_schema=plugin.get_config_schema(),
        current_config=current_config,
        is_enabled=is_enabled
    )


@router.post("/{plugin_name}/enable")
def enable_plugin(
    plugin_name: str,
    request: EnablePluginRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_tenant_admin)
):
    """
    Enable a plugin for the current tenant.
    
    Requires tenant admin permissions.
    """
    if not PluginRegistry._plugins:
        discover_plugins()
    
    result = TenantPluginConfig.enable_plugin(
        db=db,
        tenant_id=current_user.tenant_id,
        plugin_name=plugin_name,
        config=request.config
    )
    
    if not result['success']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get('error', 'Failed to enable plugin')
        )
    
    return result


@router.post("/{plugin_name}/disable")
def disable_plugin(
    plugin_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_tenant_admin)
):
    """
    Disable a plugin for the current tenant.
    
    Requires tenant admin permissions.
    """
    result = TenantPluginConfig.disable_plugin(
        db=db,
        tenant_id=current_user.tenant_id,
        plugin_name=plugin_name
    )
    
    if not result['success']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get('error', 'Failed to disable plugin')
        )
    
    return result


@router.post("/{plugin_name}/test", response_model=PluginTestResult)
def test_plugin_connection(
    plugin_name: str,
    config: dict,
    current_user: User = Depends(get_current_tenant_admin)
):
    """
    Test plugin connection with provided configuration.
    
    This allows testing before enabling the plugin.
    """
    if not PluginRegistry._plugins:
        discover_plugins()
    
    plugin_class = PluginRegistry.get(plugin_name)
    if not plugin_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{plugin_name}' not found"
        )
    
    # Check it's an integration plugin
    if plugin_class.plugin_type != PluginType.INTEGRATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only integration plugins support connection testing"
        )
    
    plugin = plugin_class()
    
    # Validate config first
    is_valid, error = plugin.validate_config(config)
    if not is_valid:
        return PluginTestResult(
            success=False,
            message=f"Configuration invalid: {error}"
        )
    
    # Test connection
    result = plugin.test_connection(config)
    
    return PluginTestResult(**result)


@router.post("/{plugin_name}/sync", response_model=PluginSyncResult)
def trigger_plugin_sync(
    plugin_name: str,
    request: PluginSyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_tenant_admin)
):
    """
    Trigger a sync operation for an enabled plugin.
    
    Direction can be:
    - inbound: Pull from external system
    - outbound: Push to external system
    - bidirectional: Both directions
    """
    if not PluginRegistry._plugins:
        discover_plugins()
    
    plugin_class = PluginRegistry.get(plugin_name)
    if not plugin_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{plugin_name}' not found"
        )
    
    # Check plugin is enabled for tenant
    if not TenantPluginConfig.is_plugin_enabled(db, current_user.tenant_id, plugin_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plugin '{plugin_name}' is not enabled for your organization"
        )
    
    # Get config
    config = TenantPluginConfig.get_plugin_config(db, current_user.tenant_id, plugin_name)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plugin configuration not found"
        )
    
    plugin = plugin_class()
    
    results = {
        'success': True,
        'items_synced': 0,
        'items_created': 0,
        'items_updated': 0,
        'items_failed': 0,
        'errors': [],
        'duration_seconds': 0
    }
    
    # Run sync based on direction
    if request.direction in ['inbound', 'bidirectional']:
        inbound_result = plugin.sync_inbound(
            tenant_id=current_user.tenant_id,
            config=config,
            options=request.options
        )
        results['items_synced'] += inbound_result.get('items_synced', 0)
        results['items_created'] += inbound_result.get('items_created', 0)
        results['items_updated'] += inbound_result.get('items_updated', 0)
        results['items_failed'] += inbound_result.get('items_failed', 0)
        results['errors'].extend(inbound_result.get('errors', []))
        results['duration_seconds'] += inbound_result.get('duration_seconds', 0)
        if not inbound_result.get('success'):
            results['success'] = False
    
    if request.direction in ['outbound', 'bidirectional']:
        if not plugin.supports_bidirectional:
            results['errors'].append(f"Plugin {plugin_name} does not support outbound sync")
        else:
            outbound_result = plugin.sync_outbound(
                tenant_id=current_user.tenant_id,
                config=config,
                data=None,
                options=request.options
            )
            results['items_synced'] += outbound_result.get('items_synced', 0)
            results['items_created'] += outbound_result.get('items_created', 0)
            results['items_updated'] += outbound_result.get('items_updated', 0)
            results['items_failed'] += outbound_result.get('items_failed', 0)
            results['errors'].extend(outbound_result.get('errors', []))
            results['duration_seconds'] += outbound_result.get('duration_seconds', 0)
            if not outbound_result.get('success'):
                results['success'] = False
    
    return PluginSyncResult(**results)


@router.get("/enabled", response_model=List[PluginConfigSchema])
def list_enabled_plugins(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all enabled plugins for the current tenant.
    """
    if not PluginRegistry._plugins:
        discover_plugins()
    
    enabled_plugins = TenantPluginConfig.get_enabled_plugins(db, current_user.tenant_id)
    
    result = []
    for plugin_data in enabled_plugins:
        plugin_name = plugin_data.get('name')
        plugin_class = PluginRegistry.get(plugin_name)
        
        if plugin_class:
            plugin = plugin_class()
            result.append(PluginConfigSchema(
                name=plugin_name,
                config_schema=plugin.get_config_schema(),
                current_config=plugin_data.get('config'),
                is_enabled=plugin_data.get('enabled', False),
                status=plugin_data.get('status')
            ))
    
    return result
