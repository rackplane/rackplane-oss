# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""NetBox Integration Plugin"""

from app.plugins.integrations.netbox.plugin import NetBoxPlugin
from app.plugins.registry import PluginRegistry

# Auto-register plugin when module is imported
PluginRegistry.register(NetBoxPlugin)

__all__ = ['NetBoxPlugin']
