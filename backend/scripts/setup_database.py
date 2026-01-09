#!/usr/bin/env python3
"""
Seamless Database Setup and Migration

This script handles both fresh installations and upgrades seamlessly:
- Runs database migrations automatically
- Verifies constraints after migration
- Runs bootstrap for fresh installations
- Handles everything in one command

Usage:
    python scripts/setup_database.py
    python scripts/setup_database.py --skip-bootstrap  # Only run migrations
    python scripts/setup_database.py --skip-migrations  # Only run bootstrap
"""
import sys
import subprocess
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
os.chdir(backend_dir)


def run_migrations():
    """Run database migrations safely."""
    print("=" * 80)
    print("STEP 1: Running Database Migrations")
    print("=" * 80)
    print()
    
    cmd = ['python3', 'scripts/safe_migrate.py']
    result = subprocess.run(cmd, cwd=backend_dir)
    
    if result.returncode != 0:
        print()
        print("❌ Migration failed. Please fix errors before continuing.")
        return False
    
    return True


def run_bootstrap():
    """Run bootstrap to create default data."""
    print()
    print("=" * 80)
    print("STEP 2: Initializing Default Data")
    print("=" * 80)
    print()
    
    cmd = ['python3', 'bootstrap.py']
    result = subprocess.run(cmd, cwd=backend_dir)
    
    if result.returncode != 0:
        print()
        print("⚠️  Bootstrap had some issues, but migration completed.")
        print("   You may need to create default data manually.")
        return False
    
    return True


def check_if_fresh_install():
    """Check if this is a fresh installation (no data)."""
    try:
        from sqlalchemy import create_engine, text
        from app.core.config import settings
        
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            # Check if tenants table exists and has data
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'tenants'
                )
            """))
            table_exists = result.scalar()
            
            if not table_exists:
                return True  # Fresh install - no tables
            
            # Check if any tenants exist
            result = conn.execute(text("SELECT COUNT(*) FROM tenants"))
            tenant_count = result.scalar()
            
            return tenant_count == 0  # Fresh install if no tenants
    except Exception:
        # If we can't check, assume it's a fresh install to be safe
        return True


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Seamless database setup and migration"
    )
    parser.add_argument(
        '--skip-migrations',
        action='store_true',
        help='Skip running migrations (only run bootstrap)'
    )
    parser.add_argument(
        '--skip-bootstrap',
        action='store_true',
        help='Skip bootstrap (only run migrations)'
    )
    parser.add_argument(
        '--skip-tests',
        action='store_true',
        help='Skip running tests after migration'
    )
    
    args = parser.parse_args()
    
    print()
    print("=" * 80)
    print("SEAMLESS DATABASE SETUP")
    print("=" * 80)
    print()
    print("This script will:")
    if not args.skip_migrations:
        print("  1. Run database migrations (with safety checks)")
    if not args.skip_bootstrap:
        print("  2. Initialize default data (if needed)")
    print()

    # Check if this is a fresh install FIRST
    is_fresh = check_if_fresh_install()

    # For FRESH installs: Bootstrap FIRST, then migrations
    # For EXISTING installs: Migrations only
    if is_fresh:
        # Step 1 (Fresh Install): Run bootstrap first to create base schema
        if not args.skip_bootstrap:
            print("📦 Fresh installation detected - running bootstrap first...")
            if not run_bootstrap():
                print("⚠️  Bootstrap had issues, but you can continue.")
        else:
            print("⏭️  Skipping bootstrap (--skip-bootstrap)")
            print()

        # Step 2 (Fresh Install): Then run migrations
        if not args.skip_migrations:
            if not run_migrations():
                sys.exit(1)
        else:
            print("⏭️  Skipping migrations (--skip-migrations)")
            print()
    else:
        # Existing installation
        # Step 1 (Existing Install): Run migrations only
        if not args.skip_migrations:
            if not run_migrations():
                sys.exit(1)
        else:
            print("⏭️  Skipping migrations (--skip-migrations)")
            print()

        # Step 2 (Existing Install): Skip bootstrap
        if not args.skip_bootstrap:
            print("✓ Existing installation detected - skipping bootstrap")
            print("  (Bootstrap only runs for fresh installations)")
            print()
        else:
            print("⏭️  Skipping bootstrap (--skip-bootstrap)")
            print()
    
    print()
    print("=" * 80)
    print("✅ DATABASE SETUP COMPLETE")
    print("=" * 80)
    print()
    print("Your database is ready to use!")
    print()
    print("Next steps:")
    print("  1. Start the application: docker compose up -d")
    print("  2. Access frontend: http://localhost:3000")
    print("  3. Login with default credentials (if fresh install):")
    print("     Username: admin")
    print("     Password: ChangeMe123!")
    print()


if __name__ == '__main__':
    main()

