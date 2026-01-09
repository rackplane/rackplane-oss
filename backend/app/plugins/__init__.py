# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
RackPlane Plugin Architecture

This module provides the plugin system for extending RackPlane with:
- Integration plugins (NetBox, Epic EHR, SAP, etc.)
- Feature plugins (expiration tracking, par levels, etc.)
- Vertical-specific functionality

Usage:
    from app.plugins import PluginRegistry
    
    # Get all plugins for a vertical
    plugins = PluginRegistry.list_for_vertical('healthcare')
    
    # Get a specific plugin
    netbox = PluginRegistry.get('netbox')
"""

from app.plugins.registry import PluginRegistry
from app.plugins.base import IntegrationPlugin, FeaturePlugin

__all__ = ['PluginRegistry', 'IntegrationPlugin', 'FeaturePlugin']
