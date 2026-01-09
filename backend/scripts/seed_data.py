
import sys
import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def seed_data():
    print("Seeding demo data...")
    engine = create_engine(str(settings.DATABASE_URL))
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. Create Default Tenant
        print("Checking Tenant...")
        result = session.execute(text("SELECT id FROM public.tenants WHERE slug = 'default'"))
        tenant = result.fetchone()
        
        tenant_id = 0
        if not tenant:
            print("Creating Default Tenant...")
            result = session.execute(
                text("INSERT INTO public.tenants (name, slug, is_active, created_at, updated_at) VALUES (:name, :slug, true, now(), now()) RETURNING id"),
                {"name": "Default Tenant", "slug": "default"}
            )
            tenant_id = result.fetchone()[0]
            session.commit()
            print(f"Created Tenant ID: {tenant_id}")
        else:
            tenant_id = tenant[0]
            print(f"Tenant exists: {tenant_id}")

        # 2. Create Admin User
        print("Checking Admin User...")
        result = session.execute(text("SELECT id FROM public.users WHERE username = 'admin'"))
        user = result.fetchone()
        
        if not user:
            print("Creating Admin User...")
            hashed_pw = get_password_hash("admin")
            session.execute(
                text("""
                    INSERT INTO public.users 
                    (username, email, hashed_password, role, is_active, is_super_admin, tenant_id, created_at, updated_at)
                    VALUES (:username, :email, :password, 'admin', true, true, :tenant_id, now(), now())
                """),
                {
                    "username": "admin", 
                    "email": "admin@example.com", 
                    "password": hashed_pw,
                    "tenant_id": tenant_id
                }
            )
            session.commit()
            print("Created Admin User (admin/admin)")
        else:
            print("Admin User exists")

        # 2b. Create Velocity Admin (Requested by user)
        print("Checking Velocity Admin...")
        result = session.execute(text("SELECT id FROM public.users WHERE username = 'velocity-admin'"))
        v_user = result.fetchone()

        if not v_user:
            print("Creating Velocity Admin...")
            # Use 'velocity' as default password, or 'admin' if preferred. Let's start with 'velocity'
            hashed_pw_velocity = get_password_hash("velocity") 
            session.execute(
                text("""
                    INSERT INTO public.users 
                    (username, email, hashed_password, role, is_active, is_super_admin, tenant_id, created_at, updated_at)
                    VALUES (:username, :email, :password, 'admin', true, true, :tenant_id, now(), now())
                """),
                {
                    "username": "velocity-admin", 
                    "email": "velocity-admin@rackplane.com", 
                    "password": hashed_pw_velocity,
                    "tenant_id": tenant_id
                }
            )
            session.commit()
            print("Created Velocity Admin (velocity-admin/velocity)")
        else:
            # Optional: Reset password if it exists but is broken? 
            # For safety in a seed script, we usually don't overwrite existing users unless asked.
            # But the user specifically said they can't log in. 
            # Let's print a helpful message about how to reset it.
            print("Velocity Admin exists. (To reset password, delete this user and re-run seed)")

        # 3. Seed Vendor SKUs (to test visibility)
        print("Seeding Vendor SKUs...")
        # Check if we have any skus
        result = session.execute(text("SELECT count(*) FROM vendor_skus"))
        count = result.fetchone()[0]
        
        if count == 0:
            skus = [
                ("Cisco", "QSFP-100G-SR4-S", "100GBASE-SR4", "100GBASE-SR4 QSFP Transceiver"),
                ("Juniper", "QFX-SFP-10GE-SR", "SFP+ SR", "SFP+ 10GBASE-SR 850nm"),
                ("Arista", "SFP-10G-LR", "10GBASE-LR", "10GBASE-LR SFP+ Transceiver"),
                ("Dell", "407-BBOU", "SFP+ SR", "SFP+ Transceiver, 10GbE SR"),
            ]
            
            for vendor, part_number, name, desc in skus:
                session.execute(
                    text("""
                        INSERT INTO vendor_skus 
                        (vendor, sku, name, description, tenant_id, created_at, updated_at)
                        VALUES (:vendor, :sku, :name, :desc, :tenant_id, now(), now())
                    """),
                    {
                        "vendor": vendor,
                        "sku": part_number,
                        "name": name,
                        "desc": desc,
                        "tenant_id": tenant_id
                    }
                )
            session.commit()
            print(f"Seeded {len(skus)} Vendor SKUs")
        else:
            print(f"Vendor SKUs exist ({count})")

        print("Seeding Complete. You can now login with admin/admin.")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    seed_data()
