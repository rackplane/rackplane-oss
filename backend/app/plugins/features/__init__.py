# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""Feature plugins for vertical-specific functionality"""

from app.plugins.features.expiration_tracking import ExpirationTrackingPlugin
from app.plugins.features.par_levels import ParLevelPlugin
from app.plugins.registry import PluginRegistry

# Auto-register feature plugins
PluginRegistry.register(ExpirationTrackingPlugin)
PluginRegistry.register(ParLevelPlugin)

__all__ = ['ExpirationTrackingPlugin', 'ParLevelPlugin']
