#!/usr/bin/env python3
"""
Ensure a system-wide super admin user exists.
This is used in the demo environment to guarantee access to admin features
(like native backups) regardless of the seed data used.

Usage:
    python3 scripts/ensure_sysadmin.py
"""

import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import SessionLocal
from app.core.auth import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ensure_sysadmin():
    db = SessionLocal()
    try:
        username = os.getenv("SYSADMIN_USERNAME", "sysadmin")
        password = os.getenv("SYSADMIN_PASSWORD", "changeme-in-production")
        email = os.getenv("SYSADMIN_EMAIL", "sysadmin@example.com")
        
        # Check if user exists
        user = db.execute(text("SELECT id FROM users WHERE username = :username"), {"username": username}).fetchone()
        
        if user:
            logger.info(f"User '{username}' already exists (ID: {user[0]}). ensuring super_admin privileges...")
            # Ensure privileges are set correctly
            db.execute(text("""
                UPDATE users 
                SET is_super_admin = true, 
                    role = 'super_admin',
                    is_active = true
                WHERE id = :id
            """), {"id": user[0]})
            db.commit()
            logger.info(f"✅ User '{username}' updated to super_admin.")
        else:
            logger.info(f"Creating new super_admin user '{username}'...")
            hashed_pw = get_password_hash(password)
            
            # Insert new user as super admin
            # Note: tenant_id is required (NOT NULL constraint), but super_admin can access all tenants
            # Use tenant_id=1 (demo tenant) as a default, but super_admin privileges allow system-wide access
            db.execute(text("""
                INSERT INTO users (
                    username, 
                    email, 
                    hashed_password, 
                    is_active, 
                    is_super_admin, 
                    role, 
                    tenant_id,
                    created_at,
                    updated_at
                ) VALUES (
                    :username,
                    :email,
                    :hashed_pw,
                    true,
                    true,
                    'super_admin',
                    COALESCE((SELECT id FROM tenants WHERE id = 1 LIMIT 1), 1),
                    NOW(),
                    NOW()
                )
            """), {
                "username": username,
                "email": email,
                "hashed_pw": hashed_pw
            })
            db.commit()
            logger.info(f"✅ Created user '{username}' (set SYSADMIN_PASSWORD env var for custom password)")
            
    except Exception as e:
        logger.error(f"❌ Failed to ensure sysadmin: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    ensure_sysadmin()
