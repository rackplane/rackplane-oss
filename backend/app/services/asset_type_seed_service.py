# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Asset Type Seed Service
Service for seeding vertical-specific asset types for tenants

This service provides functions to seed asset types based on tenant vertical packs.
Can be used by API endpoints and scripts.
"""

from typing import Dict
from sqlalchemy.orm import Session
from app.models.tenant import Tenant
from app.models.asset_type import AssetTypeModel
import logging

logger = logging.getLogger(__name__)

# Vertical-specific asset types
VERTICAL_ASSET_TYPES = {
    "datacenter": [
        {"name": "server_device", "display_name": "Server", "description": "Physical or virtual servers", "icon": "server", "color": "#3B82F6", "is_system": True},
        {"name": "switch_device", "display_name": "Network Switch", "description": "Network switches and Layer 2/3 devices", "icon": "network", "color": "#10B981", "is_system": True},
        {"name": "router_device", "display_name": "Router", "description": "Network routers and Layer 3 devices", "icon": "router", "color": "#8B5CF6", "is_system": True},
        {"name": "storage_device", "display_name": "Storage", "description": "Storage arrays, NAS, SAN devices", "icon": "database", "color": "#F59E0B", "is_system": True},
        {"name": "firewall_device", "display_name": "Firewall", "description": "Network firewalls and security appliances", "icon": "shield", "color": "#EF4444", "is_system": True},
        {"name": "load_balancer", "display_name": "Load Balancer", "description": "Application and network load balancers", "icon": "balance", "color": "#06B6D4", "is_system": True},
        {"name": "pdu_device", "display_name": "PDU", "description": "Power Distribution Units", "icon": "plug", "color": "#6366F1", "is_system": True},
        {"name": "ups_device", "display_name": "UPS", "description": "Uninterruptible Power Supply", "icon": "battery", "color": "#14B8A6", "is_system": True},
        {"name": "patch_panel", "display_name": "Patch Panel", "description": "Network patch panels and fiber enclosures", "icon": "grid", "color": "#84CC16", "is_system": True},
        {"name": "kvm_switch", "display_name": "KVM Switch", "description": "Keyboard, Video, Mouse switches", "icon": "monitor", "color": "#78716C", "is_system": True},
        {"name": "console_server", "display_name": "Console Server", "description": "Serial console servers", "icon": "terminal", "color": "#64748B", "is_system": True},
        {"name": "generic_cable", "display_name": "Cable", "description": "Generic cables", "icon": "cable", "color": "#9CA3AF", "is_system": True},
        {"name": "dac_cable", "display_name": "DAC Cable", "description": "Direct Attach Copper cables", "icon": "cable", "color": "#A855F7", "is_system": True},
        {"name": "ethernet_cable", "display_name": "Ethernet Cable", "description": "Copper Ethernet cables (Cat5e, Cat6, etc.)", "icon": "cable", "color": "#22D3EE", "is_system": True},
        {"name": "electrical_cable", "display_name": "Electrical Cable", "description": "Power and electrical cables", "icon": "cable", "color": "#FB923C", "is_system": True},
        {"name": "fiber_cable", "display_name": "Fiber Cable", "description": "Fiber optic cables and modules", "icon": "cable", "color": "#EC4899", "is_system": True},
        {"name": "copper_transceiver", "display_name": "Copper Transceiver", "description": "Copper network transceivers (SFP, QSFP, etc.)", "icon": "chip", "color": "#F97316", "is_system": True},
        {"name": "optical_transceiver", "display_name": "Optical Transceiver", "description": "Optical network transceivers (SFP+, QSFP+, etc.)", "icon": "chip", "color": "#06B6D4", "is_system": True},
        {"name": "nic_card", "display_name": "NIC Card", "description": "Network Interface Cards", "icon": "chip", "color": "#10B981", "is_system": True},
        {"name": "dpu_card", "display_name": "DPU Card", "description": "Data Processing Unit Cards", "icon": "chip", "color": "#8B5CF6", "is_system": True},
        {"name": "other_device", "display_name": "Other", "description": "Other datacenter equipment", "icon": "box", "color": "#6B7280", "is_system": True}
    ],
    "healthcare": [
        {"name": "medication", "display_name": "Medication", "description": "Pharmaceuticals and medications", "icon": "pill", "color": "#8b5cf6", "is_system": True},
        {"name": "ppe", "display_name": "PPE", "description": "Personal Protective Equipment", "icon": "shield", "color": "#10b981", "is_system": True},
        {"name": "syringes", "display_name": "Syringes", "description": "Medical syringes and needles", "icon": "syringe", "color": "#22c55e", "is_system": True},
        {"name": "medical_supply", "display_name": "Medical Supply", "description": "General medical supplies and equipment", "icon": "box", "color": "#3b82f6", "is_system": True},
        {"name": "bandages", "display_name": "Bandages", "description": "Bandages and wound care supplies", "icon": "bandage", "color": "#ef4444", "is_system": True},
        {"name": "gloves", "display_name": "Gloves", "description": "Medical gloves", "icon": "glove", "color": "#f59e0b", "is_system": True},
        {"name": "masks", "display_name": "Masks", "description": "Medical masks and respirators", "icon": "mask", "color": "#06b6d4", "is_system": True},
        {"name": "medical_device", "display_name": "Medical Device", "description": "Medical devices and equipment", "icon": "device", "color": "#6366f1", "is_system": True}
    ],
    "warehouse": [
        {"name": "electronics", "display_name": "Electronics", "description": "Electronic products and components", "icon": "cpu", "color": "#3b82f6", "is_system": True},
        {"name": "apparel", "display_name": "Apparel", "description": "Clothing and apparel items", "icon": "shirt", "color": "#ef4444", "is_system": True},
        {"name": "shipping_supply", "display_name": "Shipping Supply", "description": "Shipping and packaging supplies", "icon": "box", "color": "#f59e0b", "is_system": True},
        {"name": "inventory_item", "display_name": "Inventory Item", "description": "General warehouse inventory items", "icon": "package", "color": "#10b981", "is_system": True},
        {"name": "raw_material", "display_name": "Raw Material", "description": "Raw materials and components", "icon": "cube", "color": "#8b5cf6", "is_system": True},
        {"name": "finished_good", "display_name": "Finished Good", "description": "Finished products ready for shipment", "icon": "check", "color": "#22c55e", "is_system": True}
    ]
}


def seed_vertical_asset_types(tenant_id: int, db: Session) -> Dict:
    """
    Seed vertical-specific asset types for a tenant based on their vertical_pack.
    
    Args:
        tenant_id: Tenant ID to seed asset types for
        db: Database session
        
    Returns:
        Dictionary with created and skipped counts
    """
    # Get tenant (skip tenant filter for admin operations)
    tenant = db.query(Tenant).execution_options(skip_tenant_filter=True).filter(
        Tenant.id == tenant_id
    ).first()
    
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")
    
    vertical = tenant.vertical_pack or "datacenter"
    
    if vertical not in VERTICAL_ASSET_TYPES:
        logger.warning(f"Unknown vertical '{vertical}' for tenant {tenant_id}, using datacenter defaults")
        vertical = "datacenter"
    
    asset_types = VERTICAL_ASSET_TYPES[vertical]
    
    logger.info(f"Seeding {len(asset_types)} asset types for tenant {tenant_id} ({tenant.name}) - vertical: {vertical}")
    
    # Batch query all existing asset types for this tenant
    asset_type_names = [type_data["name"] for type_data in asset_types]
    existing_asset_types = db.query(AssetTypeModel).execution_options(skip_tenant_filter=True).filter(
        AssetTypeModel.tenant_id == tenant_id,
        AssetTypeModel.name.in_(asset_type_names)
    ).all()
    existing_by_name = {at.name: at for at in existing_asset_types}
    
    created_count = 0
    skipped_count = 0
    updated_count = 0
    
    for type_data in asset_types:
        if type_data["name"] not in existing_by_name:
            # Create new asset type
            asset_type = AssetTypeModel(
                **type_data,
                tenant_id=tenant_id
            )
            db.add(asset_type)
            created_count += 1
            logger.debug(f"  Creating: {type_data['display_name']}")
        else:
            # Update existing asset type to ensure is_system is set correctly
            existing = existing_by_name[type_data["name"]]
            if not existing.is_system and type_data.get("is_system", False):
                existing.is_system = True
                updated_count += 1
                logger.debug(f"  Updating: {type_data['display_name']} - marked as system type")
            else:
                skipped_count += 1
                logger.debug(f"  Skipping (exists): {type_data['display_name']}")
    
    db.commit()
    
    logger.info(f"✅ Seeded asset types for tenant {tenant_id}: {created_count} created, {updated_count} updated, {skipped_count} skipped")
    
    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant.name,
        "vertical": vertical,
        "created": created_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "total": len(asset_types)
    }
