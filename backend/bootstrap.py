#!/usr/bin/env python3
"""
Database Bootstrap Script for Datacenter Inventory Management System
Initializes database, creates tables, sets up foreign keys, and populates default data
"""

import sys
import os
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db_url
from app.models.asset import Asset
from app.models.asset_type import AssetTypeModel
from app.models.storage_container import StorageContainer
from app.models.location import Datacenter, Room, Rack
from app.models.user import User
from app.models.tenant import Tenant
from passlib.context import CryptContext
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def check_database_connection(engine):
    """Check if database is accessible"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✓ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        return False


def create_all_tables(engine):
    """Create all tables defined in models"""
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✓ All tables created successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to create tables: {e}")
        return False


def verify_tables(engine):
    """Verify all required tables exist"""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    required_tables = [
        'tenants',
        'users',
        'asset_types',
        'datacenters',
        'rooms',
        'racks',
        'storage_containers',
        'assets',
    ]

    logger.info("Verifying tables...")
    all_exist = True
    for table in required_tables:
        if table in existing_tables:
            logger.info(f"  ✓ {table}")
        else:
            logger.error(f"  ✗ {table} - MISSING")
            all_exist = False

    return all_exist


def create_admin_tenant(session):
    """Create admin tenant (tenant ID 1) if none exist"""
    try:
        # Check if tenant ID 1 exists (admin tenant)
        admin_tenant = session.query(Tenant).filter(Tenant.id == 1).first()
        if admin_tenant:
            logger.info("✓ Admin tenant already exists")
            # Ensure it has the correct slug
            if admin_tenant.slug != "admin":
                admin_tenant.slug = "admin"
                admin_tenant.name = "Admin Tenant"
                session.commit()
                logger.info("✓ Updated admin tenant slug to 'admin'")
            
            # CRITICAL: Always reset the sequence even if tenant exists
            # This handles cases where data persists (volumes) but sequences got desynced
            # or if the tenant was manually inserted with ID=1
            try:
                session.execute(text("SELECT setval('tenants_id_seq', (SELECT MAX(id) FROM tenants))"))
                session.commit()
                logger.info("✓ Synced tenants_id_seq")
            except Exception as e:
                logger.warning(f"⚠ Failed to sync sequence: {e}")

            return admin_tenant

        tenant_count = session.query(Tenant).count()
        if tenant_count > 0:
            logger.warning("⚠ Tenants exist but admin tenant (ID 1) is missing. Creating admin tenant...")
        else:
            logger.info("Creating admin tenant...")
        
        admin_tenant = Tenant(
            id=1,  # Explicitly set ID 1 for admin tenant
            name="Admin Tenant",
            slug="admin",
            subscription_tier="standard",
            is_active=True
        )
        session.add(admin_tenant)
        session.commit()
        session.refresh(admin_tenant)
        # Reset sequence to ensure next tenant gets ID 2
        session.execute(text("SELECT setval('tenants_id_seq', (SELECT MAX(id) FROM tenants))"))
        session.commit()
        logger.info("✓ Admin tenant created")
        return admin_tenant
    except Exception as e:
        logger.error(f"✗ Failed to create default tenant: {e}")
        session.rollback()
        return None


def create_default_admin_user(session):
    """Create default admin user if no users exist"""
    try:
        user_count = session.query(User).count()
        if user_count > 0:
            logger.info("✓ Users already exist, skipping default user creation")
            # Ensure admin user is super admin
            from app.models.user_role import UserRole
            admin_user = session.query(User).filter(User.username == "admin").first()
            if admin_user:
                # Update role and is_super_admin for backward compatibility
                if not hasattr(admin_user, 'role') or admin_user.role != UserRole.SUPER_ADMIN:
                    logger.info("  Updating admin to super admin role...")
                    admin_user.role = UserRole.SUPER_ADMIN
                    admin_user.is_super_admin = True
                    admin_user.sync_is_super_admin()
                    session.commit()
                    logger.info("  ✓ admin is now a super admin")
                elif not admin_user.is_super_admin:
                    # Sync is_super_admin flag
                    admin_user.sync_is_super_admin()
                    session.commit()
            return True

        # Get or create admin tenant
        admin_tenant = create_admin_tenant(session)
        if not admin_tenant:
            logger.error("Cannot create admin user without admin tenant")
            return False

        logger.info("Creating default admin user...")
        from app.models.user_role import UserRole
        admin_user = User(
            username="admin",
            hashed_password=pwd_context.hash("ChangeMe123!"),
            is_active=True,
            tenant_id=admin_tenant.id,
            role=UserRole.SUPER_ADMIN,  # Set role to super admin
            is_super_admin=True  # Legacy flag for backward compatibility
        )
        admin_user.sync_is_super_admin()  # Ensure flags are in sync
        session.add(admin_user)
        session.commit()
        logger.info("✓ Default admin user created: admin / ChangeMe123! (Super Admin)")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to create admin user: {e}")
        session.rollback()
        return False


def create_default_asset_types(session):
    """Create default asset types for admin tenant if none exist"""
    try:
        # Get admin tenant (ID 1)
        admin_tenant = session.query(Tenant).filter(Tenant.id == 1).first()
        if not admin_tenant:
            logger.warning("⚠ No admin tenant found, cannot create asset types")
            return False

        # Check if asset types exist for admin tenant
        type_count = session.query(AssetTypeModel).filter(
            AssetTypeModel.tenant_id == admin_tenant.id
        ).count()
        if type_count > 0:
            logger.info("✓ Asset types already exist for admin tenant, skipping defaults")
            return True

        logger.info("Creating default asset types for admin tenant...")
        # Use the same default types as seed_asset_types.py
        default_types = [
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
        ]

        for type_data in default_types:
            asset_type = AssetTypeModel(**type_data, tenant_id=admin_tenant.id)
            session.add(asset_type)

        session.commit()
        logger.info(f"✓ Created {len(default_types)} default asset types for admin tenant")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to create default asset types: {e}")
        session.rollback()
        return False


def create_default_datacenter(session):
    """Create default datacenter if none exist"""
    try:
        # Get admin tenant (ID 1) (required for tenant_id)
        admin_tenant = session.query(Tenant).filter(Tenant.id == 1).first()
        if not admin_tenant:
            logger.warning("⚠ No admin tenant found, cannot create datacenter")
            return False

        dc_count = session.query(Datacenter).count()
        if dc_count > 0:
            logger.info("✓ Datacenters already exist, skipping default")
            return True

        logger.info("Creating default datacenter...")
        datacenter = Datacenter(
            name="Main Datacenter",
            code="MAIN-DC",
            city="Default City",
            address="Configure location in Locations page",
            facility_manager="System Administrator",
            contact_phone="",
            contact_email="",
            tenant_id=admin_tenant.id
        )
        session.add(datacenter)
        session.commit()
        logger.info("✓ Default datacenter created")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to create default datacenter: {e}")
        session.rollback()
        return False


def verify_foreign_keys(engine):
    """Verify foreign key constraints exist"""
    inspector = inspect(engine)

    logger.info("Verifying foreign key constraints...")

    tables_with_fks = {
        'assets': ['datacenter_id', 'rack_id', 'storage_container_id'],
        'rooms': ['datacenter_id'],
        'racks': ['datacenter_id', 'room_id'],
        'storage_containers': ['datacenter_id', 'room_id'],
    }

    all_valid = True
    for table_name, expected_fk_columns in tables_with_fks.items():
        try:
            fks = inspector.get_foreign_keys(table_name)
            fk_columns = [fk['constrained_columns'][0] for fk in fks if fk['constrained_columns']]

            for expected_col in expected_fk_columns:
                if expected_col in fk_columns:
                    logger.info(f"  ✓ {table_name}.{expected_col}")
                else:
                    logger.warning(f"  ⚠ {table_name}.{expected_col} - not found (may be optional)")
        except Exception as e:
            logger.warning(f"  ⚠ Could not verify FKs for {table_name}: {e}")

    return all_valid


def check_indexes(engine):
    """Check for important indexes"""
    inspector = inspect(engine)

    logger.info("Checking database indexes...")

    important_indexes = {
        'assets': ['asset_tag', 'serial_number', 'status'],
        'users': ['username'],
        'asset_types': ['name'],
    }

    for table_name, columns in important_indexes.items():
        try:
            indexes = inspector.get_indexes(table_name)
            indexed_columns = set()
            for idx in indexes:
                indexed_columns.update(idx['column_names'])

            for col in columns:
                if col in indexed_columns:
                    logger.info(f"  ✓ {table_name}.{col} indexed")
                else:
                    logger.info(f"  ℹ {table_name}.{col} not indexed (may impact performance)")
        except Exception as e:
            logger.warning(f"  ⚠ Could not check indexes for {table_name}: {e}")


def display_summary(session):
    """Display summary of database contents"""
    logger.info("\n" + "="*60)
    logger.info("DATABASE SUMMARY")
    logger.info("="*60)

    try:
        tenant_count = session.query(Tenant).count()
        user_count = session.query(User).count()
        super_admin_count = session.query(User).filter(User.is_super_admin == True).count()
        asset_type_count = session.query(AssetTypeModel).count()
        datacenter_count = session.query(Datacenter).count()
        room_count = session.query(Room).count()
        rack_count = session.query(Rack).count()
        container_count = session.query(StorageContainer).count()
        asset_count = session.query(Asset).count()

        logger.info(f"Tenants:            {tenant_count}")
        logger.info(f"Users:              {user_count} ({super_admin_count} super admin)")
        logger.info(f"Asset Types:        {asset_type_count}")
        logger.info(f"Datacenters:        {datacenter_count}")
        logger.info(f"Rooms:              {room_count}")
        logger.info(f"Racks:              {rack_count}")
        logger.info(f"Storage Containers: {container_count}")
        logger.info(f"Assets:             {asset_count}")
        logger.info("="*60)

        if user_count > 0:
            admin_user = session.query(User).filter(User.username == "admin").first()
            if admin_user:
                logger.info("\nDefault login credentials:")
                logger.info("  Username: admin")
                logger.info("  Password: ChangeMe123!")
                logger.info(f"  Role: {'Super Admin' if admin_user.is_super_admin else 'Regular User'}")
                logger.info(f"  Tenant: {admin_user.tenant_id}")
                logger.info("\n⚠ Change these credentials after first login!")
                logger.info("⚠ As Super Admin, you can manage tenants and users")

    except Exception as e:
        logger.error(f"Could not generate summary: {e}")


def main():
    """Main bootstrap function"""
    logger.info("="*60)
    logger.info("DATACENTER Inventory Management System - Database Bootstrap")
    logger.info("="*60)

    # Get database URL
    db_url = get_db_url()
    logger.info(f"Database URL: {db_url.split('@')[1] if '@' in db_url else 'configured'}")

    # Create engine
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)

    # Step 1: Check connection
    if not check_database_connection(engine):
        logger.error("Cannot proceed without database connection")
        sys.exit(1)

    # Step 2: Create tables
    if not create_all_tables(engine):
        logger.error("Failed to create tables")
        sys.exit(1)

    # Step 3: Verify tables
    if not verify_tables(engine):
        logger.error("Some required tables are missing")
        sys.exit(1)

    # Step 4: Verify foreign keys
    verify_foreign_keys(engine)

    # Step 5: Check indexes
    check_indexes(engine)

    # Step 6: Create default data
    session = SessionLocal()
    try:
        # Create admin tenant first (required for users and asset types)
        if not create_admin_tenant(session):
            logger.warning("Admin tenant creation failed")

        if not create_default_admin_user(session):
            logger.warning("Admin user creation failed")

        if not create_default_asset_types(session):
            logger.warning("Default asset types creation failed")

        if not create_default_datacenter(session):
            logger.warning("Default datacenter creation failed")

    finally:
        session.close()

    # Step 7: Display summary
    session = SessionLocal()
    try:
        display_summary(session)
    finally:
        session.close()

    logger.info("\n" + "="*60)
    logger.info("✓ BOOTSTRAP COMPLETE")
    logger.info("="*60)
    logger.info("\nNext steps:")
    logger.info("1. Start the application: docker compose up -d")
    logger.info("2. Access frontend: http://localhost:3000")
    logger.info("3. Access mobile: http://localhost:3000/mobile")
    logger.info("4. Login with: admin / ChangeMe123!")
    logger.info("5. Change default password immediately!")
    logger.info("\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\nBootstrap cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nBootstrap failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
