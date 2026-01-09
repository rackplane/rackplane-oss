#!/usr/bin/env python3
"""
Seed vertical-specific asset types for tenants based on their vertical_pack.

This script ensures that each tenant has the appropriate asset types for their vertical:
- Datacenter: IT infrastructure types (servers, switches, cables, etc.)
- Healthcare: Medical supply types (medications, PPE, syringes, etc.)
- Warehouse: Inventory types (electronics, apparel, shipping supplies, etc.)

Usage:
    python3 scripts/seed_vertical_asset_types.py [--tenant-id TENANT_ID]
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.tenant import Tenant
from app.services.asset_type_seed_service import seed_vertical_asset_types
import argparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Function imported from service module


def main():
    parser = argparse.ArgumentParser(description="Seed vertical-specific asset types for tenants")
    parser.add_argument("--tenant-id", type=int, help="Specific tenant ID to seed (if not provided, seeds all tenants)")
    parser.add_argument("--all", action="store_true", help="Seed all tenants")
    args = parser.parse_args()
    
    db: Session = SessionLocal()
    try:
        if args.tenant_id:
            # Seed specific tenant
            result = seed_vertical_asset_types(args.tenant_id, db)
            print(f"✅ Seeded tenant {result['tenant_id']} ({result['tenant_name']}): {result['created']} created, {result['skipped']} skipped")
        elif args.all:
            # Seed all tenants
            # SECURITY NOTE: skip_tenant_filter is required for admin script to query all tenants.
            # This script should only be run by system administrators during deployment/setup.
            tenants = db.query(Tenant).execution_options(skip_tenant_filter=True).filter(
                Tenant.is_active == True
            ).all()
            
            print(f"Seeding asset types for {len(tenants)} tenants...")
            for tenant in tenants:
                try:
                    result = seed_vertical_asset_types(tenant.id, db)
                    print(f"  ✅ Tenant {result['tenant_id']} ({result['tenant_name']}): {result['created']} created, {result['skipped']} skipped")
                except Exception as e:
                    print(f"  ❌ Failed to seed tenant {tenant.id}: {e}")
        else:
            parser.print_help()
            sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
