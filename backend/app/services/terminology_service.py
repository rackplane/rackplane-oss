# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Terminology Service
Manages configurable terminology for white-label platform

This service provides terminology management and substitution capabilities
for the white-label platform. It includes presets for different verticals
(datacenter, healthcare, warehouse) and allows custom terminology per tenant.

Usage:
    from app.services.terminology_service import TerminologyService
    
    service = TerminologyService()
    terminology = service.get_terminology(tenant_id, db)
    label = service.substitute("Assets", terminology)  # Returns "Supplies" for healthcare
"""

from typing import Dict, Optional, Any
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class TerminologyService:
    """Service to manage and substitute terminology based on tenant config."""
    
    # Default datacenter terminology (baseline)
    DATACENTER_PRESET = {
        "item": "Asset",
        "items": "Assets",
        "location": "Datacenter",
        "locations": "Datacenters",
        "bin": "Rack",
        "bins": "Racks",
        "check_out": "Deploy",
        "check_in": "Return",
        "category": "Asset Type",
        "categories": "Asset Types",
        "lifecycle": "Status",
        "storage": "Storage",
        "stock": "Inventory",
        "container": "Storage Container",
        "containers": "Storage Containers",
        "unit": "U-Space",
        "units": "U-Spaces"
    }
    
    # Healthcare vertical preset
    HEALTHCARE_PRESET = {
        "item": "Supply",
        "items": "Supplies",
        "location": "Facility",
        "locations": "Facilities",
        "bin": "Cabinet",
        "bins": "Cabinets",
        "check_out": "Dispense",
        "check_in": "Restock",
        "category": "Supply Category",
        "categories": "Supply Categories",
        "lifecycle": "Supply Status",
        "storage": "Supply Room",
        "stock": "Inventory",
        "container": "Storage Location",
        "containers": "Storage Locations",
        "unit": "Shelf",
        "units": "Shelves"
    }
    
    # Warehouse vertical preset
    WAREHOUSE_PRESET = {
        "item": "Item",
        "items": "Items",
        "location": "Warehouse",
        "locations": "Warehouses",
        "bin": "Shelf",
        "bins": "Shelves",
        "check_out": "Pick",
        "check_in": "Receive",
        "category": "SKU Category",
        "categories": "SKU Categories",
        "lifecycle": "Item Status",
        "storage": "Zone",
        "stock": "Stock",
        "container": "Bin Location",
        "containers": "Bin Locations",
        "unit": "Slot",
        "units": "Slots"
    }
    
    # Map vertical pack names to presets
    VERTICAL_PRESETS = {
        "datacenter": DATACENTER_PRESET,
        "healthcare": HEALTHCARE_PRESET,
        "warehouse": WAREHOUSE_PRESET
    }
    
    def get_preset(self, vertical: str) -> Dict[str, str]:
        """
        Get terminology preset for a vertical pack.
        
        Args:
            vertical: Vertical pack name (datacenter, healthcare, warehouse)
            
        Returns:
            Dictionary of terminology key-value pairs
        """
        return self.VERTICAL_PRESETS.get(vertical, self.DATACENTER_PRESET).copy()
    
    def get_terminology(self, tenant_id: int, db: Session) -> Dict[str, str]:
        """
        Get merged terminology for a tenant.
        
        Merges default preset with tenant-specific overrides.
        
        Args:
            tenant_id: Tenant ID
            db: Database session
            
        Returns:
            Complete terminology dictionary
        """
        from app.models.tenant import Tenant
        
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            logger.warning(f"Tenant {tenant_id} not found, using datacenter defaults")
            return self.DATACENTER_PRESET.copy()
        
        # Start with vertical preset
        vertical = tenant.vertical_pack or "datacenter"
        terminology = self.get_preset(vertical)
        
        # Merge tenant-specific overrides
        tenant_terms = tenant.terminology or {}
        terminology.update(tenant_terms)
        
        return terminology
    
    def get_term(self, tenant_id: int, key: str, db: Session) -> str:
        """
        Get a single terminology value for a tenant.
        
        Args:
            tenant_id: Tenant ID
            key: Terminology key (e.g., "item", "bin")
            db: Database session
            
        Returns:
            Terminology value or key if not found
        """
        terminology = self.get_terminology(tenant_id, db)
        return terminology.get(key, key)
    
    def substitute(self, text: str, terminology: Dict[str, str]) -> str:
        """
        Substitute default terms with tenant-specific terms in text.
        
        This performs case-insensitive substitution while preserving
        the original case pattern.
        
        Args:
            text: Text containing default terminology
            terminology: Terminology dictionary to apply
            
        Returns:
            Text with substituted terminology
        """
        if not text:
            return text
            
        result = text
        
        # Create substitution map from datacenter defaults to custom terms
        for key, default_value in self.DATACENTER_PRESET.items():
            custom_value = terminology.get(key, default_value)
            if default_value != custom_value:
                # Replace exact matches (case-sensitive)
                result = result.replace(default_value, custom_value)
                # Replace lowercase matches
                result = result.replace(default_value.lower(), custom_value.lower())
                # Replace uppercase matches
                result = result.replace(default_value.upper(), custom_value.upper())
        
        return result
    
    def update_tenant_terminology(
        self, 
        tenant_id: int, 
        updates: Dict[str, str], 
        db: Session
    ) -> Dict[str, str]:
        """
        Update tenant terminology with custom values.
        
        Args:
            tenant_id: Tenant ID
            updates: Dictionary of terminology key-value pairs to update
            db: Database session
            
        Returns:
            Updated terminology dictionary
        """
        from app.models.tenant import Tenant
        
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        # Get current terminology or initialize empty
        current = tenant.terminology or {}
        
        # Merge updates
        current.update(updates)
        
        # Save to tenant
        tenant.terminology = current
        db.commit()
        db.refresh(tenant)
        
        logger.info(f"Updated terminology for tenant {tenant_id}: {list(updates.keys())}")
        
        return self.get_terminology(tenant_id, db)
    
    def apply_vertical_preset(
        self, 
        tenant_id: int, 
        vertical: str, 
        db: Session,
        override_custom: bool = False
    ) -> Dict[str, str]:
        """
        Apply a vertical preset to a tenant.
        
        Args:
            tenant_id: Tenant ID
            vertical: Vertical pack name
            db: Database session
            override_custom: If True, replace all custom terminology
            
        Returns:
            Updated terminology dictionary
        """
        from app.models.tenant import Tenant
        
        if vertical not in self.VERTICAL_PRESETS:
            raise ValueError(f"Unknown vertical: {vertical}. "
                           f"Options: {list(self.VERTICAL_PRESETS.keys())}")
        
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        # Update vertical pack
        tenant.vertical_pack = vertical
        
        if override_custom:
            # Replace terminology with preset
            tenant.terminology = self.get_preset(vertical)
        
        db.commit()
        db.refresh(tenant)
        
        logger.info(f"Applied vertical preset '{vertical}' to tenant {tenant_id}")
        
        return self.get_terminology(tenant_id, db)
    
    def get_all_presets(self) -> Dict[str, Dict[str, str]]:
        """
        Get all available vertical presets.
        
        Returns:
            Dictionary of vertical -> terminology presets
        """
        return {
            vertical: preset.copy()
            for vertical, preset in self.VERTICAL_PRESETS.items()
        }
    
    def get_supported_keys(self) -> list:
        """
        Get list of all supported terminology keys.
        
        Returns:
            List of terminology key names
        """
        return list(self.DATACENTER_PRESET.keys())


# Singleton instance
terminology_service = TerminologyService()
